from openai import AsyncOpenAI
from typing import Optional, Tuple
import re
from bot.config import settings
from bot.services.redis_service import redis_service


class TranslationService:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.german_articles = {
            "der": "masculine",
            "die": "feminine", 
            "das": "neuter",
            "plural": "plural"
        }
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str,
        user_id: Optional[int] = None
    ) -> Tuple[str, int]:
        """
        Translate text using OpenAI API with caching
        Returns: (translation, tokens_used)
        """
        # Check cache first
        cached = await redis_service.get_cached_translation(text, source_lang, target_lang)
        if cached:
            return cached, 0
        
        # Check token limit
        if user_id:
            tokens_used_today = await redis_service.get_user_tokens_today(user_id)
            if tokens_used_today >= settings.MAX_TOKENS_PER_USER_DAILY:
                raise Exception("Daily token limit reached")
        
        # Prepare prompt based on target language
        if target_lang == "de":
            prompt = f"Translate the following text to German. If it's a noun, include the appropriate article (der/die/das). Provide only the translation without explanations.\n\nText: {text}"
        else:
            prompt = f"Translate the following text from {source_lang} to {target_lang}. Provide only the translation without explanations.\n\nText: {text}"
        
        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional translator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=500
        )
        
        translation = response.choices[0].message.content.strip()
        tokens_used = response.usage.total_tokens
        
        # Cache the translation
        await redis_service.cache_translation(text, source_lang, target_lang, translation)
        
        # Update user token count
        if user_id:
            await redis_service.increment_user_tokens(user_id, tokens_used)
        
        return translation, tokens_used
    
    async def generate_sentence(self, difficulty: str, target_lang: str, interface_lang: str) -> str:
        """Generate a sentence for daily trainer"""
        difficulty_descriptions = {
            "A2": "elementary level (A2)",
            "B1": "intermediate level (B1)",
            "B2": "upper-intermediate level (B2)",
            "A2-B2": "mixed difficulty between A2 and B2"
        }
        
        prompt = f"Generate a simple sentence in {interface_lang} at {difficulty_descriptions.get(difficulty, 'A2')} difficulty level. The sentence should be suitable for language learning. Provide only the sentence without any explanations."
        
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a language teacher creating practice sentences."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        return response.choices[0].message.content.strip()
    
    async def check_translation(
        self, 
        original: str, 
        user_translation: str, 
        expected_lang: str,
        interface_lang: str
    ) -> Tuple[bool, str, str, int]:
        """
        Check if user's translation is correct
        Returns: (is_correct, correct_translation, explanation, quality_percentage)
        """
        prompt = f"""Evaluate a learner's translation. You receive the original sentence and the learner's translation.

Original sentence (source language): {original}
Learner translation (target={expected_lang}): {user_translation}

TASK:
1. Produce the best correct translation in target language.
2. Identify ALL mistakes (articles, verb endings, tense, word order, capitalization, noun gender, case, choice of verb (e.g. 'frühstücken' vs 'essen Frühstück'), spelling).
3. Decide correctness: ONLY 'CORRECT' if there are ZERO grammar or morphology errors.
4. Score quality 0-100 following rubric:
   100: Perfect
   85-99: Minor style only
   60-84: Some grammar errors, meaning OK
   30-59: Multiple grammar errors but understandable
   1-29: Severe errors, meaning partly lost
   0: Meaning wrong or unintelligible
5. Provide short structured explanation listing each error category.

Return STRICT JSON ONLY (no prose) with keys:
{"status": "CORRECT|INCORRECT", "correct": "<correct translation>", "quality": <int>, "errors": ["error 1", "error 2", ...]}"""
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",  # More accurate for grammar checking than gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "You are a strict language teacher. Check grammar precisely and mark INCORRECT if there are ANY errors in verb forms, articles, cases, declensions, or word order."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Very low temperature for consistent, strict evaluation
            max_tokens=400
        )
        
        raw = response.choices[0].message.content.strip()

        # Try JSON parse
        import json
        is_correct = False
        correct_translation = user_translation
        explanation = ""
        quality_percentage = 0
        try:
            data = json.loads(raw)
            status_val = str(data.get("status", "")).upper()
            is_correct = status_val == "CORRECT"
            correct_translation = data.get("correct", user_translation).strip() or user_translation
            quality_percentage = int(data.get("quality", 0))
            quality_percentage = max(0, min(100, quality_percentage))
            errors_list = data.get("errors", []) or []
            explanation = "\n".join(errors_list)
        except Exception:
            # Fallback simple heuristic if JSON failed
            explanation = "Parser fallback: модель вернула не-JSON."
            # Penalize if clearly wrong patterns present
            quality_percentage = 30

        # Apply rule-based German heuristics for stricter penalties
        if expected_lang.lower() == "de":
            penalties = 0
            lower_user = user_translation.lower()
            def penalize(reason, amount):
                nonlocal penalties, explanation
                penalties += amount
                if reason not in explanation:
                    explanation += ("\n" if explanation else "") + reason
            if "maine " in lower_user:
                penalize("Ошибка: 'Meine' написано как 'Maine'", 15)
            if "familie essen" in lower_user:
                penalize("Спряжение: должно 'Familie isst' или 'Familie frühstückt'", 25)
            if any(x in lower_user for x in ["den frühstück","der frühstück","einen frühstück"]):
                penalize("Артикль: нужно 'das Frühstück'", 20)
            if "essen frühstück" in lower_user:
                penalize("Лексика: предпочтительно глагол 'frühstücken'", 10)
            if penalties:
                quality_percentage = max(0, quality_percentage - penalties)
                if penalties > 0:
                    is_correct = False  # Force incorrect if any penalty
        
        # Final adjustment: if marked correct but quality < 90, downgrade correctness
        if is_correct and quality_percentage < 90:
            is_correct = False
            explanation += ("\nАвто-правка: качество <90 => не идеально по правилам.")
        
        return is_correct, correct_translation, explanation, quality_percentage


translation_service = TranslationService()
