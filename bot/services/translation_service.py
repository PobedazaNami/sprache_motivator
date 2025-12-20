from openai import AsyncOpenAI
from typing import Optional, Tuple, List, Dict
import re
import json
import aiohttp
from bot.config import settings
from bot.services.redis_service import redis_service


class TranslationService:
    # Keywords indicating educational feedback about language issues
    EDUCATIONAL_KEYWORDS = [
        'grammar', 'article', 'case', 'verb', 'word order',
        'spelling', 'punctuation', 'capitalization',
        'грамматика', 'артикль', 'падеж', 'глагол', 
        'порядок слов', 'орфография', 'пунктуация',
        'граматика', 'відмінок', 'дієслово', 
        'написання', 'пунктуація'
    ]
    
    # Phrases indicating system errors (not educational feedback)
    SYSTEM_ERROR_PHRASES = [
        'internal error', 'unable to process', 
        'error processing', 'system error',
        'внутренняя ошибка', 'невозможно обработать'
    ]
    
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
        elif source_lang == "auto":
            # Auto-detect source language for English/German text
            prompt = f"Translate the following text to {target_lang}. Provide only the translation without explanations.\n\nText: {text}"
        else:
            prompt = f"Translate the following text from {source_lang} to {target_lang}. Provide only the translation without explanations.\n\nText: {text}"
        
        # Call OpenAI API
        response = await self.client.chat.completions.create(
            model="gpt-4o",
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
    
    async def generate_sentence(self, difficulty: str, target_lang: str, interface_lang: str, topic=None, user_id: int = None) -> str:
        """Generate a sentence for daily trainer.
        If user_id is provided, avoids generating sentences the user has already mastered (100% quality).
        """
        from bot.models.database import TrainerTopic, TOPIC_METADATA
        from bot.services import mongo_service
        import random
        import hashlib
        
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
        
        # Sentence length limits by difficulty level (in words)
        sentence_length_limits = {
            "A2": "5-10 words",
            "B1": "8-14 words", 
            "B2": "10-18 words",
            "A2-B2": "6-15 words"
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
        
        # Get mastered sentence hashes if user_id provided
        mastered_hashes = set()
        if user_id and mongo_service.is_ready():
            topic_value = topic.value if topic and topic != TrainerTopic.RANDOM else None
            mastered_hashes = set(await mongo_service.get_mastered_sentences_hashes(user_id, topic_value))
        
        def _hash_sentence(sentence: str) -> str:
            """Create a normalized hash of a sentence for comparison."""
            normalized = ' '.join(sentence.lower().strip().split())
            return hashlib.md5(normalized.encode('utf-8')).hexdigest()
        
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
        
        # Sentence style variations for more engaging content
        style_variations = [
            "from a first-person perspective, as if someone is sharing their experience",
            "as a dialogue line that someone might say in a real conversation",
            "describing a relatable everyday situation with a touch of humor",
            "expressing an opinion or feeling about something",
            "telling a mini-story or interesting fact",
            "as a question someone might ask in daily life",
            "with a slight emotional undertone (happiness, curiosity, surprise)",
            "describing a sensory experience (what someone sees, hears, or feels)",
            "as advice or a life tip someone might share",
            "about a common problem or funny mishap",
        ]
        
        # Try up to 5 times to generate a non-mastered sentence
        max_attempts = 5
        length_limit = sentence_length_limits.get(difficulty, "6-12 words")
        
        for attempt in range(max_attempts):
            selected_style = random.choice(style_variations)
            
            # Add uniqueness instruction on retries
            uniqueness_hint = ""
            if attempt > 0:
                uniqueness_hint = f"\n- This is attempt {attempt + 1}, so create something completely different from typical sentences"
            
            prompt = f"""Generate a lively, natural sentence in {interface_lang_name} at {difficulty_descriptions.get(difficulty, 'A2')} difficulty level{topic_instruction}.

Style: {selected_style}

Requirements:
- IMPORTANT: Keep the sentence SHORT - exactly {length_limit}. No longer!
- Make it feel like something a real person would actually say
- Include concrete details, names, or specific situations when appropriate
- Avoid generic or textbook-style sentences
- The sentence should evoke emotion, curiosity, or a smile
- Keep it natural and conversational
- ONE simple idea per sentence, no compound sentences with multiple clauses{uniqueness_hint}

Provide only the sentence without any explanations."""
            
            response = await self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a creative language teacher who creates engaging, memorable practice sentences. Your sentences feel alive - they tell mini-stories, express real emotions, and describe situations that learners can relate to. You avoid boring, generic sentences like 'The book is on the table' and instead create sentences that make people smile, think, or feel something."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.9,
                max_tokens=150
            )
            
            sentence = response.choices[0].message.content.strip()
            
            # Check if this sentence is already mastered
            sentence_hash = _hash_sentence(sentence)
            if sentence_hash not in mastered_hashes:
                return sentence
            
            # If mastered, try again with higher temperature
        
        # After max attempts, return the last generated sentence anyway
        # (very unlikely to hit this with GPT's randomness)
        return sentence
    
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
- Score quality 0-100 using this FAIR scale:
  * 100: Perfect translation, no errors at all
  * 95-99: Nearly perfect, only minor stylistic differences (word choice synonym, slightly different but correct phrasing)
  * 90-94: One tiny error (missing/wrong punctuation, minor capitalization)
  * 85-89: One small grammar error (wrong article, small case error, minor spelling typo)
  * 80-84: Two small errors OR one medium error (wrong verb form, word order issue)
  * 70-79: Several small errors OR one significant error affecting meaning slightly
  * 50-69: Multiple errors that affect understanding but core meaning is preserved
  * 30-49: Many errors, meaning partially lost
  * 10-29: Severe errors, hard to understand
  * 0-9: Completely wrong, off-topic, or meaning totally lost
- Provide the best CORRECT translation in TARGET_LANG in the "correct" field.
- Return STRICT JSON only: {{"status":"CORRECT|INCORRECT","correct":"...","quality":<int>,"errors":["error 1","error 2",...]}}
- Explanations in errors must be in {interface_lang_name} and name concrete issues (article/case/verb/word order/orthography), with correct forms.
""".strip()

        response = await self.client.chat.completions.create(
            model="gpt-4o",
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
        json_parsed = False
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
            json_parsed = True
        except Exception:
            # Fallback: try to extract JSON from response if it's embedded in text
            # Look for JSON objects that contain "status" field
            json_match = re.search(r'\{(?:[^{}]|(?:\{[^{}]*\}))*?"status"(?:[^{}]|(?:\{[^{}]*\}))*?\}', raw, re.DOTALL)
            if json_match:
                try:
                    data = json.loads(json_match.group(0))
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
                    json_parsed = True
                except Exception:
                    pass
            
            # If JSON extraction failed, try to parse as structured text
            if not json_parsed:
                # Try to extract information from text format
                is_correct = False
                quality_percentage = 40
                
                # Try to extract errors/explanations from the response
                # Look for common patterns like lists, error descriptions, etc.
                lines = raw.split('\n')
                extracted_errors = []
                
                for line in lines:
                    line = line.strip()
                    # Skip empty lines, JSON artifacts, and system error messages
                    if not line or line in ['{', '}', '[', ']']:
                        continue
                    # Skip generic system errors (not educational feedback)
                    if any(phrase in line.lower() for phrase in self.SYSTEM_ERROR_PHRASES):
                        continue
                    # Look for educational error descriptions (lines that describe language issues)
                    # Common patterns: starts with list markers, or contains grammar/language issue keywords
                    if (line.startswith('-') or line.startswith('*') or 
                        line.startswith('•') or re.match(r'^\d+[.\)]\s+', line) or
                        any(word in line.lower() for word in self.EDUCATIONAL_KEYWORDS)):
                        # Clean up the line (remove list markers)
                        cleaned = re.sub(r'^[-*•\d.)]+\s*', '', line)
                        if cleaned and len(cleaned) > 10:  # Require meaningful length
                            extracted_errors.append(cleaned)
                
                if extracted_errors:
                    errors_list = extracted_errors
                else:
                    # If we couldn't extract anything meaningful, provide a helpful default
                    # based on the interface language
                    if interface_lang == "uk":
                        errors_list = ["Знайдено помилки в граматиці, пунктуації або значенні. Перевірте артиклі, відмінки, закінчення слів та порядок слів."]
                    else:  # Russian
                        errors_list = ["Обнаружены ошибки в грамматике, пунктуации или значении. Проверьте артикли, падежи, окончания слов и порядок слов."]

        # Ensure we always provide a correct translation string
        if not correct_translation:
            try:
                correct_translation, _ = await self.translate(original, interface_lang, expected_lang, None)
            except Exception:
                correct_translation = ""

        # Language-specific rule-based penalties and corrections
        penalties = 0
        u = user_translation.strip()
        u_lower = u.lower()
        
        def penalize(reason: str, amount: int = 10):
            nonlocal penalties, errors_list
            penalties += max(0, amount)
            if reason not in errors_list:
                errors_list.append(reason)
        
        # German-specific heuristics
        if expected_lang.lower() == "de":
            # Common mistakes
            # catch 'eden Tag' only when 'jeden Tag' is not present
            if "eden tag" in u_lower and "jeden tag" not in u_lower:  # jeden Tag
                penalize("Орфография: нужно 'jeden Tag' (Akkusativ)", 20)
            if "das gesund" in u_lower or re.search(r"\bgesund(?!heit)\b", u_lower):
                penalize("Лексика/существительное: требуется 'die Gesundheit' (существительное с заглавной)", 25)
            if "damit" in u_lower and " zu " in u_lower:
                penalize("Конструкция цели: вместо 'damit ... zu' использовать 'um ... zu'", 20)
            # Capitalization of nouns: very rough heuristic – if line contains 'gesundheit' in lowercase
            if "gesundheit" in u_lower and "Gesundheit" not in u:
                penalize("Правописание: существительные в немецком с заглавной — 'Gesundheit'", 10)
        
        # English-specific heuristics
        elif expected_lang.lower() == "en":
            # Common ESL mistakes
            # Subject-verb agreement: "he go" instead of "he goes"
            if re.search(r"\b(he|she|it)\s+(go|do|have)\b", u_lower):
                penalize("Grammar: subject-verb agreement (he/she/it + verb+s)", 15)
            # Double negatives: "don't have no"
            if re.search(r"\bdon't\s+\w*\s*no\b", u_lower) or re.search(r"\bno\s+\w*\s*not\b", u_lower):
                penalize("Grammar: avoid double negatives in standard English", 15)
            # Article errors: "an" before consonant sounds (university, European, one)
            # Note: 'u' in 'university' has /j/ consonant sound, so needs 'a'
            if re.search(r"\ban\s+(university|user|uniform|euro|one)\b", u_lower):
                penalize("Article: use 'a' before consonant sounds (a university, a European)", 10)
            # "a" before vowel sounds (but not before 'u' with /j/ sound)
            if re.search(r"\ba\s+(apple|orange|hour|elephant|umbrella|idea)\b", u_lower):
                penalize("Article: use 'an' before vowel sounds (an apple, an hour)", 10)
            # Common spelling: "recieve" instead of "receive"
            if "recieve" in u_lower:
                penalize("Spelling: 'receive' (i before e except after c)", 10)
            # "alot" instead of "a lot"
            if "alot" in u_lower:
                penalize("Spelling: 'a lot' (two words)", 10)

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
            if interface_lang == "uk":
                explanation = (
                    "Переклад відповідає оригіналу без граматичних помилок." if is_correct
                    else "У відповіді виявлено помилки. Перевірте артиклі, відмінки, орфографію та порядок слів."
                )
            else:  # Russian
                explanation = (
                    "Перевод соответствует оригиналу без грамматических ошибок." if is_correct
                    else "В ответе обнаружены ошибки. Проверьте артикли, падежи, орфографию и порядок слов."
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
