from openai import AsyncOpenAI
from typing import Optional, Tuple, List, Dict
import re
import json
import aiohttp
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
        # Pre-map LanguageTool language tags
        self.lt_lang_map = {
            "de": "de-DE",
            "en": "en-US",
            "ru": "ru-RU",
            "uk": "uk-UA",
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
        Strictly evaluate a translation attempt.
        Returns: (is_correct, correct_translation, explanation, quality_percentage)
        """
        # Language names for prompt clarity
        lang_names = {"uk": "Ukrainian", "ru": "Russian", "en": "English", "de": "German"}
        interface_lang_name = lang_names.get(interface_lang, interface_lang)
        expected_lang_name = lang_names.get(expected_lang, expected_lang)

        # Strict JSON-only evaluation prompt
        eval_prompt = f"""
Evaluate a learner translation. Input:
ORIGINAL: {original}
LEARNER: {user_translation}
TARGET_LANG: {expected_lang_name}

Rules:
- If there is ANY grammar, morphology, article, case, conjugation, word order, capitalization or clear spelling error, status MUST be INCORRECT.
- Only PERFECT answers (no errors) can be CORRECT.
- Score quality 0-100 (perfect=100; minor style only=90-99; small grammar errors=60-84; multiple errors=30-59; severe=1-29; off-topic/meaning wrong=0).
- Provide the best CORRECT translation in TARGET_LANG in the "correct" field.
- Return STRICT JSON only: {{"status":"CORRECT|INCORRECT","correct":"...","quality":<int>,"errors":["error 1","error 2",...]}}
- Explanations in errors must be in {interface_lang_name} and name concrete issues (article/case/verb/word order/orthography), with correct forms.
""".strip()

        response = await self.client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a strict language teacher for precise grammar checking. Respond with strict JSON only."},
                {"role": "user", "content": eval_prompt},
            ],
            temperature=0.1,
            max_tokens=400,
        )

        raw = (response.choices[0].message.content or "").strip()

        # Defaults
        is_correct = False
        correct_translation = ""
        quality_percentage = 0
        errors_list = []

        # Try parse JSON
        try:
            data = json.loads(raw)
            status_val = str(data.get("status", "")).upper()
            is_correct = status_val == "CORRECT"
            correct_translation = (data.get("correct") or "").strip()
            quality_percentage = int(data.get("quality", 0))
            quality_percentage = max(0, min(100, quality_percentage))
            errors = data.get("errors") or []
            if isinstance(errors, list):
                errors_list = [str(e) for e in errors if str(e).strip()]
            else:
                errors_list = [str(errors)]
        except Exception:
            # Fallback very defensive parse
            # If model misbehaved, mark as incorrect and compute later
            errors_list = [
                "Автоматический парсер: ответ не в JSON, применены строгие правила."
            ]
            is_correct = False
            correct_translation = ""
            quality_percentage = 40

        # Ensure we always provide a correct translation string
        if not correct_translation:
            try:
                correct_translation, _ = await self.translate(original, interface_lang, expected_lang, None)
            except Exception:
                correct_translation = ""

        # German-specific rule-based penalties and corrections
        penalties = 0
        u = user_translation.strip()
        u_lower = u.lower()
        if expected_lang.lower() == "de":
            def penalize(reason: str, amount: int = 10):
                nonlocal penalties, errors_list
                penalties += max(0, amount)
                if reason not in errors_list:
                    errors_list.append(reason)

            # Common mistakes
            if "eden tag" in u_lower:  # jeden Tag
                penalize("Орфография: нужно 'jeden Tag' (Akkusativ)", 20)
            if "das gesund" in u_lower or re.search(r"\bgesund(?!heit)\b", u_lower):
                penalize("Лексика/существительное: требуется 'die Gesundheit' (существительное с заглавной)", 25)
            if "damit" in u_lower and " zu " in u_lower:
                penalize("Конструкция цели: вместо 'damit ... zu' использовать 'um ... zu'", 20)
            # Capitalization of nouns: very rough heuristic – if line contains 'gesundheit' in lowercase
            if "gesundheit" in u_lower and "Gesundheit" not in u:
                penalize("Правописание: существительные в немецком с заглавной — 'Gesundheit'", 10)

        # Apply penalties to quality and correctness
        if penalties:
            quality_percentage = max(0, quality_percentage - penalties)
            is_correct = False

        # LanguageTool grammar check (deterministic). Non-fatal if unavailable.
        lt_matches: List[Dict] = []
        if settings.LANGUAGETOOL_ENABLED and settings.LANGUAGETOOL_URL:
            try:
                lt_lang = self.lt_lang_map.get(expected_lang.lower(), expected_lang)
                lt_matches = await self._languagetool_check(text=u, language=lt_lang)
                if lt_matches:
                    # Penalize per match, capped
                    penalty_per_issue = 6
                    max_penalty = 40
                    lt_penalty = min(max_penalty, penalty_per_issue * len(lt_matches))
                    quality_percentage = max(0, quality_percentage - lt_penalty)
                    is_correct = False
                    # Add top messages to errors
                    for m in lt_matches[:5]:
                        msg = m.get("message") or m.get("shortMessage") or "Grammar issue"
                        rule_id = (m.get("rule", {}) or {}).get("id", "")
                        formatted = f"[LT] {msg}{f' ({rule_id})' if rule_id else ''}"
                        if formatted not in errors_list:
                            errors_list.append(formatted)
            except Exception:
                # If LT is down, proceed without it
                pass

        # Final strictness: ensure CORRECT only if high score and no errors
        if is_correct and (quality_percentage < 90 or errors_list):
            is_correct = False

        # Build tutor-style explanation in interface language from errors
        explanation = "\n".join(errors_list).strip()
        if not explanation:
            # Provide minimal educational note even when perfect
            explanation = (
                "Перевод соответствует оригиналу без грамматических ошибок." if is_correct
                else "В ответе обнаружены ошибки. Проверьте статьи, падежи, орфографию и порядок слов."
            )

        return is_correct, correct_translation, explanation, quality_percentage

    async def _languagetool_check(self, text: str, language: str) -> List[Dict]:
        """Call LanguageTool HTTP server /v2/check and return matches list.
        Non-raising: returns [] on any error.
        """
        base = settings.LANGUAGETOOL_URL.rstrip("/")
        url = f"{base}/v2/check"
        data = {
            "text": text,
            "language": language,
            "enabledOnly": "false",
        }
        timeout = aiohttp.ClientTimeout(total=6)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, data=data) as resp:
                if resp.status != 200:
                    return []
                payload = await resp.json(content_type=None)
                matches = payload.get("matches") or []
                # Normalize a bit
                norm: List[Dict] = []
                for m in matches:
                    if isinstance(m, dict):
                        norm.append({
                            "message": m.get("message"),
                            "shortMessage": m.get("shortMessage"),
                            "offset": m.get("offset"),
                            "length": m.get("length"),
                            "rule": m.get("rule") or {},
                        })
                return norm


translation_service = TranslationService()
