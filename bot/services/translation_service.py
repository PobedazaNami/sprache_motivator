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
    
    async def generate_sentence(self, difficulty: str, target_lang: str, interface_lang: str, topic=None) -> str:
        """Generate a sentence for daily trainer"""
        from bot.models.database import TrainerTopic, TOPIC_METADATA
        import random
        
        # Map language codes to full names for clarity
        lang_names = {
            "uk": "Ukrainian",
            "ru": "Russian", 
            "en": "English",
            "de": "German"
        }
        
        difficulty_descriptions = {
            "A2": "elementary level (A2)",
            "B1": "intermediate level (B1)",
            "B2": "upper-intermediate level (B2)",
            "A2-B2": "mixed difficulty between A2 and B2"
        }
        
        # Topic descriptions for prompts
        topic_descriptions = {
            TrainerTopic.PERSONAL_INFO: "personal information and introduction (name, age, origin, profession)",
            TrainerTopic.FAMILY_FRIENDS: "family and friends (relationships, character, connections)",
            TrainerTopic.HOME_DAILY: "home and daily life (housing, neighbors, household chores, daily habits)",
            TrainerTopic.LEISURE_HOBBIES: "leisure and hobbies (sports, hobbies, free time, meetings)",
            TrainerTopic.SHOPPING_MONEY: "shopping and money (purchases, stores, prices, goods)",
            TrainerTopic.FOOD_DRINK: "food and drink (eating, restaurants, favorite dishes)",
            TrainerTopic.HEALTH_DOCTOR: "health and doctor visits (illness, doctor appointments, medicine)",
            TrainerTopic.TRANSPORT: "traffic and transport (bus, train, road, tickets)",
            TrainerTopic.TRAVEL_VACATION: "travel and vacation (trips, holidays, hotels, excursions)",
            TrainerTopic.WEATHER_SEASONS: "weather and seasons (weather, seasons, clothing)",
            TrainerTopic.SCHOOL_LEARNING: "school and learning (studying, language courses, exams)",
            TrainerTopic.CELEBRATIONS: "celebrations and holidays (holidays, traditions, congratulations)",
            TrainerTopic.WORK_CAREER: "work and career (job, profession, working conditions)",
            TrainerTopic.JOB_APPLICATION: "job application and CV (interview, resume, job search)",
            TrainerTopic.RESIDENCE_NEIGHBORHOOD: "residence and neighborhood (life in city/village, neighbors)",
            TrainerTopic.LEISURE_MEDIA: "leisure and media (cinema, television, internet, social media)",
            TrainerTopic.FOOD_NUTRITION: "food, drink and nutrition (eating habits, diet, health)",
            TrainerTopic.TRAVEL_TRAFFIC: "travel and traffic (journeys, transport, impressions)",
            TrainerTopic.ENVIRONMENT_NATURE: "environment and nature (ecology, waste, recycling)",
            TrainerTopic.SOCIETY_COEXISTENCE: "society and coexistence (helping others, respect, rules)",
            TrainerTopic.HEALTH_LIFESTYLE: "health and lifestyle (sports, stress, healthy living)",
            TrainerTopic.FASHION_CLOTHING: "fashion and clothing (style, shopping, appearance)",
            TrainerTopic.TECHNOLOGY_DIGITALIZATION: "technology and digitalization (impact of technology, internet, online work)",
            TrainerTopic.MEDIA_ADVERTISING: "media, advertising and consumption (advertising, manipulation, social media)",
            TrainerTopic.FUTURE_DREAMS: "future and dreams (goals, career, self-development)",
            TrainerTopic.SOCIAL_PROBLEMS: "social problems (poverty, unemployment, housing, discrimination)",
            TrainerTopic.CULTURE_IDENTITY: "culture and identity (cultural differences, traditions, integration)",
            TrainerTopic.SCIENCE_INNOVATION: "science and innovation (inventions, artificial intelligence, medicine)",
            TrainerTopic.ENVIRONMENT_CLIMATE: "environment and climate change (climate, global warming, solutions)",
            TrainerTopic.FUTURE_WORK: "work of the future (automation, remote work, work-life balance)",
        }
        
        interface_lang_name = lang_names.get(interface_lang, interface_lang)
        
        # Handle topic selection
        topic_instruction = ""
        if topic and topic != TrainerTopic.RANDOM:
            topic_desc = topic_descriptions.get(topic, "general topic")
            topic_instruction = f" about the topic: {topic_desc}"
        elif not topic or topic == TrainerTopic.RANDOM:
            # Select random topic
            available_topics = [t for t in TrainerTopic if t != TrainerTopic.RANDOM]
            random_topic = random.choice(available_topics)
            topic_desc = topic_descriptions.get(random_topic, "general topic")
            topic_instruction = f" about the topic: {topic_desc}"
        
        prompt = f"Generate a simple sentence in {interface_lang_name} at {difficulty_descriptions.get(difficulty, 'A2')} difficulty level{topic_instruction}. The sentence should be suitable for language learning. Provide only the sentence without any explanations."
        
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
        # Map language codes to full names for clarity
        lang_names = {
            "uk": "Ukrainian",
            "ru": "Russian", 
            "en": "English",
            "de": "German"
        }
        
        interface_lang_name = lang_names.get(interface_lang, interface_lang)
        expected_lang_name = lang_names.get(expected_lang, expected_lang)
        
        prompt = f"""You are a language teacher checking a translation exercise.

Original sentence (to be translated): {original}
User's translation attempt: {user_translation}
Expected target language: {expected_lang_name}

Your task:
1. First check if the user's answer is even attempting to translate the original sentence or if it's completely off-topic/irrelevant
2. If off-topic (e.g., single random word, unrelated sentence), mark as INCORRECT with quality 0-20%
3. If on-topic, evaluate the translation quality based on these specific criteria:
   - **Punctuation correctness**: Are commas, periods, and other punctuation marks placed correctly according to {expected_lang_name} grammar rules? (20% weight)
   - **Word endings and grammar**: Are word endings correct (declensions, conjugations)? Are articles, prepositions, and cases used correctly? (30% weight)
   - **Semantic accuracy**: Does the translation accurately convey the same meaning as the original sentence? (30% weight)
   - **Vocabulary appropriateness**: Are the words natural and appropriate for the context? (10% weight)
   - **Natural phrasing**: Does it sound natural in {expected_lang_name}? (10% weight)
   Note: Minor errors in any category should not severely impact the quality score if the overall meaning is preserved.
4. Provide the correct/ideal translation of the ORIGINAL sentence in {expected_lang_name}
5. Give explanation about the ORIGINAL sentence and how to translate it correctly, specifically mentioning any errors in punctuation, word endings, or meaning

IMPORTANT: 
- Write ALL explanations in {interface_lang_name} language
- The TRANSLATION field must ALWAYS contain the actual correct translation in {expected_lang_name}, NEVER words like "Incorrect" or "Correct"
- Consider translations with minor spelling or grammar mistakes as high quality (70-90%) if the meaning is correct
- Only give very low quality scores (0-30%) for completely wrong or off-topic answers
- In your explanation, specifically mention if there are errors in: punctuation, word endings, or semantic meaning

Format your response EXACTLY as:
STATUS: [CORRECT/INCORRECT]
TRANSLATION: [the correct/ideal translation of "{original}" in {expected_lang_name} - MUST be an actual translation, not a status word]
QUALITY: [0-100]
EXPLANATION: [explanation in {interface_lang_name} about the original sentence and its correct translation, mentioning any issues with punctuation, word endings, or meaning]"""
        
        response = await self.client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": f"You are a strict language teacher. Always respond in {interface_lang_name} for explanations."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=400
        )
        
        result = response.choices[0].message.content.strip()
        
        # Parse response with robust status checking
        lines = result.split("\n")
        status_line = lines[0].strip().upper() if lines else ""
        
        # Check for exact status patterns to avoid false positives
        is_correct = status_line.startswith("STATUS:") and "CORRECT" in status_line and "INCORRECT" not in status_line
        
        translation_line = [line for line in lines if "TRANSLATION:" in line]
        correct_translation = translation_line[0].replace("TRANSLATION:", "").strip() if translation_line else user_translation
        
        # Validate that correct_translation is actually a translation, not a status word
        # If it contains words like "Incorrect", "Correct", "Wrong", etc., try to extract from explanation
        invalid_translation_words = ["incorrect", "correct", "wrong", "right", "error"]
        if correct_translation.lower() in invalid_translation_words or len(correct_translation) < 3:
            # Try to extract actual translation from the explanation or re-translate
            try:
                # Use the translate method to get a proper translation
                correct_translation, _ = await self.translate(
                    original,
                    interface_lang,
                    expected_lang,
                    None  # Don't count tokens
                )
            except Exception:
                # If that fails, use user's translation as fallback
                correct_translation = user_translation
        
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
        
        # If no explanation was found, collect remaining lines as explanation
        if not explanation:
            explanation_started = False
            explanation_parts = []
            for line in lines:
                if "EXPLANATION:" in line:
                    explanation_started = True
                    explanation_parts.append(line.replace("EXPLANATION:", "").strip())
                elif explanation_started:
                    explanation_parts.append(line.strip())
            if explanation_parts:
                explanation = " ".join(explanation_parts)
        
        return is_correct, correct_translation, explanation, quality_percentage


translation_service = TranslationService()
