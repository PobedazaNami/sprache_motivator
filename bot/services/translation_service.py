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
            temperature=0.3,
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
            temperature=0.7,
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
        prompt = f"""You are a strict language teacher. Check if the user's translation is GRAMMATICALLY CORRECT and semantically accurate.

Original sentence: {original}
User's translation: {user_translation}
Target language: {expected_lang}

IMPORTANT:
- Mark as CORRECT only if there are NO grammatical errors (verb forms, articles, cases, word order, spelling)
- Even small grammar mistakes = INCORRECT
- Evaluate quality strictly: grammar errors significantly reduce percentage

Respond in {interface_lang} with:
1. "CORRECT" (only if perfect grammar) or "INCORRECT" (if any errors)
2. The grammatically correct translation
3. Quality percentage (0-100%):
   - 100%: Perfect grammar and meaning
   - 80-99%: Minor stylistic issues only
   - 50-79%: Some grammar errors but meaning clear
   - 0-49%: Major grammar errors or wrong meaning
4. Detailed explanation of ALL errors found

Format your response as:
STATUS: [CORRECT/INCORRECT]
TRANSLATION: [correct translation]
QUALITY: [0-100]
EXPLANATION: [detailed explanation of errors in {interface_lang}]"""
        
        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",  # More accurate for grammar checking than gpt-3.5-turbo
            messages=[
                {"role": "system", "content": "You are a strict language teacher. Check grammar precisely and mark INCORRECT if there are ANY errors in verb forms, articles, cases, declensions, or word order."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Very low temperature for consistent, strict evaluation
            max_tokens=400
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse response with robust status checking
        lines = result.split("\n")
        status_line = lines[0].strip().upper() if lines else ""
        
        # Check for exact status patterns - must be exactly "STATUS: CORRECT", not "STATUS: INCORRECT"
        is_correct = False
        if status_line.startswith("STATUS:"):
            status_value = status_line.replace("STATUS:", "").strip()
            # Only accept if it's exactly "CORRECT", reject if contains "INCORRECT"
            is_correct = status_value == "CORRECT"
        
        translation_line = [line for line in lines if "TRANSLATION:" in line]
        correct_translation = translation_line[0].replace("TRANSLATION:", "").strip() if translation_line else user_translation
        
        quality_line = [line for line in lines if "QUALITY:" in line]
        quality_percentage = 100 if is_correct else 0
        if quality_line:
            try:
                quality_str = quality_line[0].replace("QUALITY:", "").strip()
                # Extract just the number from strings like "85%" or "85"
                quality_percentage = int(''.join(filter(str.isdigit, quality_str)))
                quality_percentage = max(0, min(100, quality_percentage))  # Clamp to 0-100
            except (ValueError, IndexError):
                quality_percentage = 100 if is_correct else 50
        
        explanation_line = [line for line in lines if "EXPLANATION:" in line]
        explanation = explanation_line[0].replace("EXPLANATION:", "").strip() if explanation_line else ""
        
        return is_correct, correct_translation, explanation, quality_percentage


translation_service = TranslationService()
