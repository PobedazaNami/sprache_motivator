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
    ) -> Tuple[bool, str, str]:
        """
        Check if user's translation is correct
        Returns: (is_correct, correct_translation, explanation)
        """
        prompt = f"""Compare these two translations and determine if they are semantically equivalent:

Original sentence: {original}
User's translation: {user_translation}
Target language: {expected_lang}

Respond in {interface_lang} with:
1. "CORRECT" or "INCORRECT"
2. The correct translation
3. Brief grammatical explanation if incorrect

Format your response as:
STATUS: [CORRECT/INCORRECT]
TRANSLATION: [correct translation]
EXPLANATION: [explanation in {interface_lang}]"""
        
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a language teacher checking translations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=300
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse response
        is_correct = "CORRECT" in result.split("\n")[0].upper() and "INCORRECT" not in result.split("\n")[0].upper()
        
        translation_line = [line for line in result.split("\n") if "TRANSLATION:" in line]
        correct_translation = translation_line[0].replace("TRANSLATION:", "").strip() if translation_line else user_translation
        
        explanation_line = [line for line in result.split("\n") if "EXPLANATION:" in line]
        explanation = explanation_line[0].replace("EXPLANATION:", "").strip() if explanation_line else ""
        
        return is_correct, correct_translation, explanation


translation_service = TranslationService()
