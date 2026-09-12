import re
import logging
from typing import Dict, Any, List, Tuple, Optional, Set

logger = logging.getLogger("PreRenderValidator")

try:
    import opencc
    _opencc_converter = opencc.OpenCC('t2s')
except ImportError:
    _opencc_converter = None

TONE_VOWELS = set("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ")

VALID_NEUTRAL_SYLLABLES: Set[str] = {
    "de", "le", "ma", "ba", "ne", "zi", "men", "tou", "fu", "er", "r",
    "ya", "la", "ge", "huo", "bian", "shang", "xia", "li", "you",
    "me", "xi", "xie", "sheng", "huan", "bai", "liang", "shi", "fan", "shu",
    "nao", "jie", "di", "zhe", "guo", "wa", "qian", "hou", "mian",
    "dao", "hu", "sa", "luo", "dian", "kuai", "nai", "mei", "ye",
    "shao", "yi", "ming", "bo", "qi", "qing", "niang", "ting", "tu",
    "su", "ban", "chu", "duo", "dai", "jing", "po", "tai", "da", "gu", "xing", "fa", "tao", "fang"
}

# Comprehensive Traditional Chinese characters that have distinct Simplified forms
TRADITIONAL_CHARS_STRING = (
    "體國說學這會個門經車愛書買點誰麼後電語漢們聽開關讓幫幾邊錢號飯題視爲為樂長師筆鐘"
    "飛樣醫難機歡顏貓藍綠雞畫雙傘齒麵髮龍媽話發頭見東廣氣兒業產當實問動過進無報萬選與"
    "對總結聲變陽陰雲風魚鳥馬豬網寫讀課試檢認識記請謝賣貴賓館飲飽餓餃餅鴨鵝藥療診斷傷"
    "熱溫涼霧颱輛輪鐵銀幣帳單費稅價優質數據圖紙腦頻響錶環衛廚廳臥臺樓櫃燈鏡褲襪帶鹹鮮"
    "週遲舊圓彎遠裡處親鄰孫爺侶練護導遊員蘋傳統灣習節歲曆歷區縣鄉鎮郵園廠庫橋樹葉雜誌"
    "條隻塊張種類齊龜豐艷麗義專業務辦協參緊牽艱嘆應慶廢莊廁廂廈閃閉閏閑閔閘閣閥閱閹閻"
    "闊闌闐闔闕關韋韌韓韻頁頂頃項順須頑顧頓頗領頡頤飠飾餡餛飩饅饌饗駕駝駐駿騎騙鬆鬍"
    "鬧魂魘魯魷鮑鮫鮭鯉鯊鯨鰓鳩鳳鳴鳶鴉鴦鴛鴕鴿鴻鵑鵠鵬鶴鸚鵡鹵麥黃黨黌鈔"
)

STRICT_TRADITIONAL_CHARS: Set[str] = set(TRADITIONAL_CHARS_STRING)

# Forbidden English words in Vietnamese definitions
ENGLISH_FORBIDDEN_WORDS = [
    "chair", "chairs", "table", "tables", "window", "windows", "door", "doors",
    "bed", "beds", "lamp", "lamps", "bookshelf", "bookshelves", "desk", "desks",
    "cup", "cups", "glass", "glasses", "bottle", "bottles", "bowl", "bowls",
    "plate", "plates", "chopsticks", "chopstick", "spoon", "spoons", "fork", "forks",
    "knife", "knives", "mirror", "mirrors", "clock", "clocks", "watch", "watches",
    "key", "keys", "bag", "bags", "wallet", "wallets", "box", "boxes",
    "fan", "fans", "fridge", "fridges", "refrigerator", "refrigerators",
    "television", "radio", "washing machine", "air conditioner",
    "computer", "computers", "telephone", "telephones", "phone", "phones", "camera", "cameras", "screen", "screens",
    "keyboard", "keyboards", "mouse", "mice", "headphone", "headphones", "earphone", "earphones",
    "tablet", "tablets", "software",
    "apple", "apples", "banana", "bananas", "orange", "oranges", "grape", "grapes",
    "watermelon", "strawberry", "fruit", "fruits", "vegetable", "vegetables",
    "rice", "noodle", "noodles", "bread", "meat", "beef", "pork", "chicken", "chickens",
    "fish", "fishes", "egg", "eggs", "soup", "cake", "cakes", "candy", "candies",
    "sugar", "salt", "pepper", "water", "tea", "coffee", "milk", "beer", "wine",
    "juice", "drink", "drinks", "food", "foods", "pizza",
    "car", "cars", "bus", "buses", "taxi", "taxis", "train", "trains",
    "plane", "planes", "airplane", "airplanes", "flight", "flights", "airport", "airports",
    "station", "stations", "bicycle", "bicycles", "bike", "bikes",
    "motorbike", "motorbikes", "motorcycle", "motorcycles", "boat", "boats", "ship", "ships",
    "subway", "metro", "ticket", "tickets", "hotel", "hotels", "tour", "tours", "trip", "trips",
    "teacher", "teachers", "student", "students", "doctor", "doctors", "nurse", "nurses",
    "driver", "drivers", "worker", "workers", "engineer", "engineers", "lawyer", "lawyers",
    "police", "father", "mother", "dad", "mom", "brother", "brothers", "sister", "sisters",
    "sons", "daughter", "daughters", "baby", "babies", "child", "children",
    "family", "families", "friend", "friends", "boy", "boys", "girl", "girls",
    "man", "woman", "women", "person", "people",
    "dog", "dogs", "cat", "cats", "bird", "birds", "duck", "ducks",
    "pig", "pigs", "cow", "cows", "horse", "horses", "sheep",
    "monkey", "monkeys", "tiger", "tigers", "lion", "lions", "elephant", "elephants",
    "bear", "bears", "snake", "snakes", "rabbit", "rabbits", "rat", "rats",
    "animal", "animals", "pet", "pets",
    "house", "houses", "home", "homes", "room", "rooms", "kitchen", "kitchens",
    "bedroom", "bedrooms", "bathroom", "bathrooms", "living", "office", "offices", "building", "buildings",
    "school", "schools", "university", "universities", "hospital", "hospitals",
    "bank", "banks", "park", "parks", "store", "stores", "shop", "shops", "shopping", "meeting",
    "market", "markets", "supermarket", "supermarkets", "restaurant", "restaurants",
    "cinema", "theatre", "theater", "city", "cities", "town", "country", "countries",
    "eat", "eating", "drink", "drinking", "sleep", "sleeping", "wake", "walk", "walking",
    "run", "running", "swim", "swimming", "fly", "flying", "drive", "driving", "ride", "riding",
    "read", "reading", "write", "writing", "speak", "speaking", "listen", "listening",
    "hear", "see", "look", "watch", "watching", "buy", "buying", "sell", "selling",
    "pay", "cost", "work", "working", "study", "studying", "learn", "learning",
    "teach", "teaching", "sing", "singing", "dance", "dancing", "play", "playing",
    "cook", "cooking", "clean", "cleaning", "wash", "washing", "open", "close",
    "start", "stop", "wait", "help", "meet", "love", "like", "hate", "want", "need",
    "think", "know", "understand",
    "good", "bad", "big", "small", "large", "little", "tall", "short", "long", "fat",
    "thin", "hot", "cold", "warm", "cool", "fast", "slow", "new", "old", "young",
    "dirty", "happy", "sad", "angry", "afraid", "scared", "tired", "hungry",
    "thirsty", "rich", "poor", "cheap", "expensive", "easy", "hard", "difficult",
    "beautiful", "pretty", "ugly", "red", "blue", "green", "yellow", "black", "white",
    "brown", "pink", "purple", "gray", "grey",
    "sun", "moon", "star", "stars", "sky", "cloud", "clouds", "rain", "snow", "wind",
    "tree", "trees", "flower", "flowers", "leaf", "leaves", "grass", "plant", "plants",
    "mountain", "mountains", "river", "rivers", "sea", "seas", "ocean", "oceans",
    "lake", "lakes", "weather", "spring", "summer", "autumn", "fall", "winter",
    "time", "hour", "hours", "minute", "minutes", "second", "seconds",
    "day", "days", "night", "nights", "morning", "afternoon", "evening",
    "today", "tomorrow", "yesterday", "week", "weeks", "month", "months", "year", "years",
    "book", "books", "pen", "pens", "pencil", "pencils", "notebook", "notebooks",
    "ruler", "rulers", "eraser", "erasers", "shoes", "shirt", "shirts", "tshirt",
    "dress", "dresses", "skirt", "skirts", "pants", "jacket", "jackets", "coat", "coats",
    "hat", "hats", "cap", "caps", "socks", "sock", "ring", "money", "dollar", "dollars",
    "card", "cards", "credit", "passport", "sofa", "desk", "desks", "towel", "soap", "shampoo",
    "brush", "comb", "gift", "gifts", "present", "party", "holiday", "vacation", "trip", "travel",
    "tour", "flight", "visa", "luggage", "suitcase", "suit", "tie", "belt", "boot", "boots",
    "glove", "gloves", "necklace", "sunglasses", "bar", "club", "gym", "stadium", "bridge",
    "apartment", "floor", "wall", "light", "lights", "clothes", "dish", "dishes",
    "language", "state", "village", "forest", "beach", "earth", "world", "space",
    "guitar", "guitars", "piano", "pianos", "music", "movie", "movies", "job", "jobs", "medicine",
    "number", "numbers", "near", "far", "left", "right", "under", "with", "and", "or", "but",
    "because", "very", "too", "also", "always", "never", "sometimes", "often", "already", "now",
    "later", "before", "after", "here", "there", "where", "what", "who", "when", "why", "how",
    "much", "many", "few", "more", "most", "all", "some", "any", "not", "yes", "please",
    "thanks", "thank", "sorry", "hello", "goodbye", "hi", "bye", "street", "road", "zoo",
    "have", "make", "go", "come", "back", "leave", "arrive", "give", "get", "find",
    "lose", "call", "ask", "answer", "question", "questions", "name", "names", "talk"
]

# Whitelist of valid Vietnamese words and accepted loanwords
VIETNAMESE_VALID_WORDS_WHITELIST = {
    # Genuine Vietnamese homographs that must not collide with foreign words
    "no", "do", "say", "son", "men",
    # Accepted loanwords and technical terms
    "ly", "tv", "tivi", "ti-vi", "internet", "wifi", "email", "online", "offline",
    "website", "web", "app", "apps", "video", "videos", "clip", "clips", "audio",
    "game", "games", "laptop", "smartphone",
    "cafe", "café", "cà phê", "bia", "so-mi", "sơ-mi", "ca", "ga", "pin",
    "xăng", "môtô", "mo-to", "buýt", "xe buýt", "xe taxi", "link", "links", "post", "page", "fanpage"
}

_ENGLISH_REGEX = re.compile(r'\b(' + '|'.join(re.escape(w) for w in sorted(set(ENGLISH_FORBIDDEN_WORDS), key=len, reverse=True)) + r')\b', re.IGNORECASE)
PINYIN_TONE_REGEX = re.compile(r'[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]', re.IGNORECASE)
PINYIN_SYL_REGEX = re.compile(r'(?:zh|ch|sh|[bpmfdtnlgkhjqxrzcsyw])?(?:[aāáǎàeēéěèiīíǐìoōóǒòuūúǔùüǖǘǚǜv]+(?:ng|n|r)?)', re.IGNORECASE)


def normalize_topic_string(topic: str) -> str:
    """Normalize topic string by removing level prefix, punctuation, and lowercasing."""
    if not topic:
        return ""
    clean = topic.strip().lower()
    # Strip common level prefix (e.g. "hsk 1 •", "hsk 2 -", "hsk 3:")
    clean = re.sub(r'^hsk\s*[1-6]\s*[•\-\:\.\/]\s*', '', clean)
    clean = re.sub(r'[\s\-_•\:\;\/]+', ' ', clean).strip()
    return clean


class PreRenderValidator:
    """
    Pre-render Linguistic and Negative Context Validator for VocabVNQuiz.
    Enforces the 5 Gatekeeper 1 Linguistic Rules and Negative Context Deduplication against Google Sheets tab 'vocabVN'.
    """

    @classmethod
    def check_simplified_chinese(cls, hanzi: str, idx: int = 1) -> List[str]:
        """Rule 1: 100% Simplified Chinese characters (reject Traditional variants)."""
        errors = []
        clean_hz = hanzi.strip()
        if not clean_hz:
            return [f"Từ #{idx}: Thiếu chữ Hán."]

        # Check OpenCC conversion if available
        if _opencc_converter:
            simplified = _opencc_converter.convert(clean_hz)
            if simplified != clean_hz:
                errors.append(f"Từ #{idx} '{clean_hz}': Chứa chữ Hán Phồn thể (Yêu cầu Giản thể '{simplified}').")
                return errors

        # Fallback / Direct character-by-character scan
        trad_found = [c for c in clean_hz if c in STRICT_TRADITIONAL_CHARS]
        if trad_found:
            unique_trad = sorted(list(set(trad_found)))
            errors.append(f"Từ #{idx} '{clean_hz}': Ký tự Phồn thể [{', '.join(unique_trad)}] bị cấm (Yêu cầu Giản thể).")

        return errors

    @classmethod
    def check_single_topic(cls, topic: str) -> List[str]:
        """Rule 2: Single focused topic (no list delimiters ';', '|', 'etc.', length 2..50 chars)."""
        errors = []
        clean_topic = (topic or "").strip()

        if not clean_topic:
            return ["Chủ đề không được để trống."]

        if len(clean_topic) < 2:
            errors.append("Chủ đề quá ngắn (tối thiểu 2 ký tự).")
        elif len(clean_topic) > 50:
            errors.append(f"Chủ đề '{clean_topic}' quá dài ({len(clean_topic)} ký tự, tối đa 50 ký tự).")

        # Reject list delimiters
        if ";" in clean_topic or "|" in clean_topic:
            errors.append(f"Chủ đề '{clean_topic}' chứa ký tự phân tách danh sách (; hoặc |). Phải là 1 chủ đề đơn rõ ràng.")

        # Reject enumeration abbreviations
        if re.search(r'(?:v\.v\.|v\/v|\betc\b|\bvv\b)', clean_topic, re.IGNORECASE):
            errors.append(f"Chủ đề '{clean_topic}' chứa ký hiệu liệt kê (etc, v.v.). Phải là 1 chủ đề rõ ràng.")

        return errors

    @classmethod
    def check_vietnamese_meaning(cls, meaning: str, hanzi: str = "", pinyin: str = "", idx: int = 1) -> List[str]:
        """Rule 3: 100% Vietnamese definitions (zero forbidden English words, no underscores/hidden pinyin)."""
        errors = []
        clean_mean = (meaning or "").strip()

        if not clean_mean:
            return [f"Từ #{idx}: Thiếu nghĩa tiếng Việt."]

        if "_" in clean_mean:
            errors.append(f"Từ #{idx}: Nghĩa tiếng Việt '{clean_mean}' bị dính ký tự gạch dưới '_' của Pinyin ẩn (Thiếu nghĩa tiếng Việt thực tế)!")

        if clean_mean == pinyin or clean_mean == hanzi:
            errors.append(f"Từ #{idx}: Nghĩa tiếng Việt '{clean_mean}' bị trùng với Pinyin/Hanzi!")

        if not re.search(r'[a-zA-ZàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]', clean_mean):
            errors.append(f"Từ #{idx}: Nghĩa '{clean_mean}' không chứa ký tự từ ngữ Tiếng Việt hợp lệ!")

        # Multi-word whitelist replacement before checking tokens (e.g., 'xe buýt', 'xe taxi', 'cà phê', 'so-mi', 'sơ-mi')
        temp_mean = clean_mean.lower()
        for wl in sorted(VIETNAMESE_VALID_WORDS_WHITELIST, key=len, reverse=True):
            if " " in wl or "-" in wl:
                temp_mean = re.sub(r'\b' + re.escape(wl) + r'\b', ' ', temp_mean)

        # Token-based check for foreign / forbidden English words
        tokens = re.findall(r'[a-zA-ZàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]+', temp_mean)
        found_forbidden = []

        for token in tokens:
            t_lower = token.lower().strip()
            if not t_lower or len(t_lower) < 2:
                continue
            if t_lower in VIETNAMESE_VALID_WORDS_WHITELIST:
                continue
            # Direct forbidden check
            if _ENGLISH_REGEX.fullmatch(t_lower):
                found_forbidden.append(t_lower)
            # Foreign consonants (f, j, w, z) check if not in whitelist
            elif re.search(r'[fjwz]', t_lower):
                found_forbidden.append(t_lower)

        if found_forbidden:
            unique_forbidden = sorted(list(set(found_forbidden)))
            errors.append(f"Từ #{idx}: Nghĩa tiếng Việt '{clean_mean}' chứa từ tiếng Anh/ngoại ngữ bị cấm: {unique_forbidden}.")

        return errors

    @classmethod
    def check_pinyin_syllables_and_tones(cls, hanzi: str, pinyin: str, idx: int = 1) -> List[str]:
        """Convenience alias returning only errors list for syllable and tone checks."""
        errors, _ = cls.check_pinyin_syllables(hanzi, pinyin, idx)
        return errors

    @classmethod
    def check_pinyin_syllables(cls, hanzi: str, pinyin: str, idx: int = 1) -> Tuple[List[str], str]:
        """
        Rule 4: 1:1 syllable Pinyin with valid tone marks for every character.
        Returns (errors, normalized_space_separated_pinyin).
        """
        errors = []
        clean_hz = re.sub(r'[\s\u3000]', '', hanzi.strip())
        clean_py = pinyin.strip()

        if not clean_hz:
            return [f"Từ #{idx}: Thiếu chữ Hán."], clean_py
        if not clean_py:
            return [f"Từ #{idx}: Thiếu Pinyin."], clean_py

        hanzi_count = len(clean_hz)
        syllables = [s for s in clean_py.split() if s]
        pinyin_count = len(syllables)

        # Erhua check (e.g. 哪儿: nǎr [2 chars -> 1 syl ending in r] or nǎ er [2 chars -> 2 syls]; 一点儿: yì diǎnr [3 chars -> 2 syls ending in r])
        is_contracted_erhua = (
            clean_hz.endswith("儿") and
            pinyin_count == hanzi_count - 1 and
            pinyin_count > 0 and
            re.sub(r'[^a-zA-Z]', '', syllables[-1]).lower() != "er" and
            syllables[-1].lower().endswith("r") and
            not re.sub(r'[^a-zA-Z]', '', syllables[-1]).lower().startswith("r")
        )
        has_contracted_r = any(
            re.sub(r'[^a-zA-Z]', '', s).lower() != "er" and
            s.lower().endswith("r") and
            not re.sub(r'[^a-zA-Z]', '', s).lower().startswith("r")
            for s in syllables
        )

        # Auto-segment unspaced pinyin if needed
        if not is_contracted_erhua and not has_contracted_r and len(syllables) != hanzi_count and len(syllables) == 1 and hanzi_count > 1:
            matched = PINYIN_SYL_REGEX.findall(clean_py)
            if matched and len(matched) == hanzi_count:
                syllables = matched
                clean_py = " ".join(matched)
                pinyin_count = len(syllables)

        # 1. Syllable count check 1:1 & Erhua validity
        if has_contracted_r and not is_contracted_erhua:
            errors.append(
                f"Từ #{idx} '{clean_hz}': Âm tiết Erhua uốn lưỡi '{clean_py}' không hợp lệ cho từ '{clean_hz}'."
            )
        elif hanzi_count != pinyin_count and not is_contracted_erhua:
            errors.append(
                f"Từ #{idx} '{clean_hz}': Số âm tiết Pinyin ({pinyin_count} âm: '{clean_py}') "
                f"không khớp 1:1 với số chữ Hán ({hanzi_count} chữ: '{clean_hz}')."
            )

        # 2. Tone mark & Neutral tone check
        # Multi-syllable word (hanzi_count > 1): MUST have at least 1 tone mark.
        # Single-syllable word (hanzi_count == 1): Must have tone mark unless it is a recognized single neutral particle.
        has_at_least_one_tone = any(PINYIN_TONE_REGEX.search(s) for s in syllables)
        if hanzi_count == 1:
            if not has_at_least_one_tone:
                syl_clean = re.sub(r'[^a-zA-Z]', '', syllables[0]).lower()
                if syl_clean not in {"de", "le", "ma", "ba", "ne", "r", "ge"}:
                    errors.append(f"Từ #{idx} '{clean_hz}': Pinyin '{clean_py}' thiếu dấu thanh điệu hợp lệ.")
        else:
            if not has_at_least_one_tone:
                errors.append(f"Từ #{idx} '{clean_hz}': Pinyin '{clean_py}' thiếu dấu thanh điệu hợp lệ.")
            else:
                # Check each un-toned syllable
                for s_idx, syl in enumerate(syllables):
                    if not PINYIN_TONE_REGEX.search(syl):
                        clean_syl = re.sub(r'[^a-zA-Z]', '', syl).lower()
                        if clean_syl not in VALID_NEUTRAL_SYLLABLES and not (is_contracted_erhua and clean_syl.endswith("r")):
                            errors.append(f"Từ #{idx} '{clean_hz}': Âm tiết '{syl}' không có dấu thanh điệu và không phải thanh nhẹ hợp lệ.")

        return errors, " ".join(syllables)

    @classmethod
    def validate_batch(cls, batch_data: Dict[str, Any], history: Optional[Dict[str, Any]] = None) -> Tuple[bool, List[str]]:
        """
        Full Linguistic and Negative Context Gatekeeper 1 validation for a single batch candidate.
        """
        errors = []
        topic = (batch_data.get("topic") or "").strip()

        # 1. Topic validation (Rule 2)
        topic_errors = cls.check_single_topic(topic)
        errors.extend(topic_errors)

        # 2. Word count validation (Rule 5)
        words = batch_data.get("words", [])
        if not isinstance(words, list) or len(words) != 5:
            errors.append(f"Số lượng từ không đúng chuẩn ({len(words) if isinstance(words, list) else 0}/5 từ). Bắt buộc phải có đúng 5 từ.")

        seen_hanzi = set()
        seen_meaning = set()

        # Validate each of the 5 words
        for idx, w in enumerate(words, start=1):
            if not isinstance(w, dict):
                errors.append(f"Từ #{idx}: Định dạng từ vựng không hợp lệ.")
                continue

            hz = (w.get("hanzi") or "").strip()
            py = (w.get("pinyin") or "").strip()
            mean = (w.get("meaning") or "").strip()

            # Rule 1: Simplified Chinese
            hz_errors = cls.check_simplified_chinese(hz, idx=idx)
            errors.extend(hz_errors)

            # Rule 3: Vietnamese definition
            mean_errors = cls.check_vietnamese_meaning(mean, hanzi=hz, pinyin=py, idx=idx)
            errors.extend(mean_errors)

            # Rule 4: 1:1 Syllable Pinyin with tones
            py_errors, normalized_py = cls.check_pinyin_syllables(hz, py, idx=idx)
            errors.extend(py_errors)
            if normalized_py:
                w["pinyin"] = normalized_py

            # Rule 5: Intra-batch duplicates
            if hz:
                if hz in seen_hanzi:
                    errors.append(f"Từ #{idx}: Trùng chữ Hán '{hz}' trong cùng một batch.")
                seen_hanzi.add(hz)

            if mean:
                mean_key = mean.lower().strip()
                if mean_key in seen_meaning:
                    errors.append(f"Từ #{idx}: Trùng nghĩa tiếng Việt '{mean}' trong cùng một batch.")
                seen_meaning.add(mean_key)

        # 3. Negative Context Deduplication against History
        if history:
            history_errors = cls.validate_against_history(batch_data, history=history)
            errors.extend(history_errors)

        return len(errors) == 0, errors

    @classmethod
    def validate_against_history(
        cls,
        batch_data: Dict[str, Any],
        history: Optional[Dict[str, Any]] = None,
        recent_topics: Optional[List[str]] = None,
        past_batches: Optional[List[Dict[str, Any]]] = None
    ) -> List[str]:
        """
        Enforce Negative Context Deduplication against Google Sheets tab 'vocabCN' history:
        - Reject candidate if topic matches any recent topic in history.
        - Reject candidate if >= 2 words overlap with any prior batch across sheet history.
        """
        errors = []
        candidate_topic = (batch_data.get("topic") or "").strip()
        candidate_words = [
            (w.get("hanzi") or "").strip() for w in batch_data.get("words", [])
            if isinstance(w, dict) and (w.get("hanzi") or "").strip()
        ]

        # Extract history containers
        topics_list = recent_topics or []
        batches_list = past_batches or []

        if history:
            if not topics_list and "recent_topics" in history:
                topics_list = history["recent_topics"]
            if not batches_list and "past_batches" in history:
                batches_list = history["past_batches"]

        # Deduplication A: Topic Recurrence
        clean_candidate_topic = normalize_topic_string(candidate_topic)
        if clean_candidate_topic:
            for past_top in topics_list:
                clean_past_top = normalize_topic_string(str(past_top))
                if clean_past_top and clean_candidate_topic == clean_past_top:
                    errors.append(
                        f"Vi phạm Negative Context: Chủ đề '{candidate_topic}' trùng lặp với chủ đề "
                        f"đã có trong lịch sử Google Sheets tab 'vocabCN' ('{past_top}')."
                    )
                    break

        # Deduplication B: Pair Repetition (>= 2 words overlap with ANY past batch)
        if batches_list and candidate_words:
            candidate_set = set(candidate_words)
            for pb in batches_list:
                pb_id = pb.get("id", "N/A")
                pb_topic = pb.get("topic", "N/A")
                pb_words = pb.get("words", [])

                overlap = candidate_set.intersection(set(pb_words))
                if len(overlap) >= 2:
                    overlap_list = sorted(list(overlap))
                    errors.append(
                        f"Vi phạm Negative Context: Trùng lặp cặp {len(overlap)} từ {overlap_list} "
                        f"với bộ kịch bản cũ #{pb_id} ('{pb_topic}'). Tối đa chỉ được trùng 1 từ để ôn tập!"
                    )

        return errors

    @classmethod
    def fetch_vocabvn_history(cls, gsheet_mgr: Optional[Any] = None) -> Dict[str, Any]:
        """
        Dynamic history loader that fetches all existing rows from tab 'vocabVN'.
        Returns structured dictionary with 'recent_topics' and 'past_batches'.
        """
        recent_topics = []
        past_batches = []

        try:
            if gsheet_mgr is None:
                from src.gsheet_manager import GSheetManager
                gsheet_mgr = GSheetManager()

            all_rows = gsheet_mgr.get_all_rows()
            for r in all_rows:
                topic = str(r.get("Topic", "")).strip()
                row_id = str(r.get("#", "")).replace("#", "").strip()
                if not row_id and "_row_number" in r:
                    row_id = str(r["_row_number"])

                if topic and topic not in recent_topics:
                    recent_topics.append(topic)

                words = []
                for i in range(1, 6):
                    w_raw = str(r.get(f"Word {i}", "")).strip()
                    if w_raw:
                        hanzi = w_raw.split("|")[0].strip()
                        if hanzi:
                            words.append(hanzi)

                if words:
                    past_batches.append({
                        "id": row_id or str(len(past_batches) + 1),
                        "topic": topic,
                        "words": words
                    })

            logger.info(f"Loaded history from Google Sheets (tab '{gsheet_mgr.tab_name}'): {len(recent_topics)} topics, {len(past_batches)} past batches.")
        except Exception as e:
            logger.warning(f"Could not load Google Sheets history dynamically: {e}")

        return {
            "recent_topics": recent_topics,
            "past_batches": past_batches
        }

    @classmethod
    def fetch_vocabcn_history(cls, gsheet_mgr: Optional[Any] = None) -> Dict[str, Any]:
        """Backwards-compatibility alias for fetch_vocabvn_history."""
        return cls.fetch_vocabvn_history(gsheet_mgr)
