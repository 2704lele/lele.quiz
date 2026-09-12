import re
import unicodedata
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

ENGLISH_FORBIDDEN_WORDS = [
    "chair", "table", "window", "door", "bed", "lamp", "desk", "cup", "glass", "bottle",
    "plate", "spoon", "fork", "knife", "clock", "watch", "key", "bag", "wallet", "box",
    "fan", "fridge", "computer", "phone", "camera", "apple", "banana", "orange", "grape",
    "watermelon", "rice", "noodle", "bread", "meat", "beef", "pork", "chicken", "fish",
    "water", "tea", "coffee", "milk", "beer", "wine", "juice", "car", "bus", "taxi", "train",
    "plane", "bicycle", "teacher", "student", "doctor", "nurse", "police", "father", "mother",
    "house", "room", "school", "hospital", "bank", "park", "store", "shop", "restaurant"
]

def normalize_vn_str(s: str) -> str:
    """Normalize Vietnamese string for deduplication."""
    if not s:
        return ""
    s_lower = s.lower().strip()
    s_lower = re.sub(r'[\/•\-_,\.\(\)]+', ' ', s_lower)
    return " ".join(s_lower.split())

class PreRenderValidator:
    """
    Gatekeeper 1 Validator for Multilevels Quiz (1 Nghĩa - 5 Cấp độ HSK):
    - Negative Context Deduplication (Cấm lặp lại chủ đề/ý niệm đã làm)
    - Exact 5 HSK levels (HSK 1 -> HSK 5)
    - 100% Simplified Chinese (Tuyệt đối cấm chữ Phồn thể)
    - Pinyin tone consistency (Đầy đủ dấu thanh điệu chuẩn)
    - Han-Viet present
    - Vietnamese meaning pure & concise (Tối đa 25 ký tự, ưu tiên thành ngữ tương đương)
    """
    def __init__(self):
        pass

    def is_simplified_chinese(self, text: str) -> Tuple[bool, str]:
        """Check whether text contains any Traditional Chinese characters."""
        if not text:
            return False, "Chuỗi ký tự tiếng Trung trống."

        for char in text:
            if char in STRICT_TRADITIONAL_CHARS:
                return False, f"Chứa ký tự phồn thể '{char}'. Vui lòng dùng chữ giản thể."

        if _opencc_converter:
            simplified = _opencc_converter.convert(text)
            if simplified != text:
                diffs = [f"{o}➔{s}" for o, s in zip(text, simplified) if o != s]
                return False, f"Phát hiện chữ phồn thể qua OpenCC: {', '.join(diffs[:3])}."

        return True, ""

    def validate_pinyin_format(self, pinyin_str: str, expected_syllables: int = None) -> Tuple[bool, str]:
        """Validate pinyin formatting and tones."""
        if not pinyin_str or not pinyin_str.strip():
            return False, "Pinyin trống."

        clean_py = pinyin_str.strip()
        syllables = clean_py.split()

        if expected_syllables and len(syllables) != expected_syllables:
            # Check for Erhua (e.g. nǎr has 1 syllable for 2 chars)
            if not any(s.endswith("r") or s == "r" for s in syllables):
                return False, f"Số âm tiết pinyin ({len(syllables)}) không khớp số chữ Hán ({expected_syllables})."

        for s in syllables:
            s_clean = s.lower().strip(",.!?")
            has_tone = any(c in TONE_VOWELS for c in s_clean)
            if not has_tone and s_clean not in VALID_NEUTRAL_SYLLABLES and not s_clean.endswith("r"):
                return False, f"Âm tiết '{s}' thiếu dấu thanh điệu chuẩn."

        return True, ""

    def validate_vietnamese_meaning(self, meaning: str) -> Tuple[bool, str]:
        """
        Check for clean Vietnamese text:
        - Within single-line length limits (<= 25 chars, <= 4 words)
        - Direct and concise, using equivalent idioms where appropriate
        - No forbidden English words
        """
        if not meaning or not meaning.strip():
            return False, "Nghĩa tiếng Việt trống."

        clean_m = meaning.strip()
        if len(clean_m) > 28:
            return False, f"Nghĩa tiếng Việt quá dài ({len(clean_m)} ký tự > tối đa 28 ký tự). Vui lòng rút gọn để nằm trọn trên 1 dòng đơn."

        words = clean_m.split()
        if len(words) > 5:
            return False, f"Nghĩa tiếng Việt quá nhiều từ ({len(words)} từ > tối đa 5 từ). Vui lòng dùng 1-4 từ ngắn gọn hoặc thành ngữ tương đương."

        m_lower = clean_m.lower()
        for forbidden in ENGLISH_FORBIDDEN_WORDS:
            pattern = rf"\b{re.escape(forbidden)}\b"
            if re.search(pattern, m_lower):
                return False, f"Nghĩa tiếng Việt chứa từ tiếng Anh bị cấm: '{forbidden}'."

        return True, ""

    def validate_negative_context(self, concept_name: str, existing_concepts: List[str]) -> Tuple[bool, str]:
        """Check whether concept duplicates any previously processed topic."""
        if not concept_name or not existing_concepts:
            return True, ""

        norm_current = normalize_vn_str(concept_name)
        if not norm_current:
            return True, ""

        for past in existing_concepts:
            norm_past = normalize_vn_str(past)
            if not norm_past:
                continue
            if norm_current == norm_past or norm_current in norm_past or norm_past in norm_current:
                return False, f"Chủ đề ý niệm '{concept_name}' bị trùng lặp với chủ đề đã tạo trước đó ('{past}')."

        return True, ""

    def validate_single_level(self, level_data: Dict[str, Any], expected_level_num: int) -> Tuple[bool, List[str]]:
        """Validate a single level entry."""
        errors = []
        lvl_num = level_data.get("level")
        if lvl_num != expected_level_num:
            errors.append(f"Level thứ tự không khớp: kỳ vọng {expected_level_num}, nhận {lvl_num}.")

        hanzi = str(level_data.get("hanzi", "")).strip()
        pinyin = str(level_data.get("pinyin", "")).strip()
        han_viet = str(level_data.get("han_viet", "")).strip()
        meaning = str(level_data.get("meaning_vi", "")).strip()

        if not hanzi:
            errors.append(f"Level {expected_level_num}: Thiếu chữ Hán.")
        else:
            simp_ok, simp_err = self.is_simplified_chinese(hanzi)
            if not simp_ok:
                errors.append(f"Level {expected_level_num} ({hanzi}): {simp_err}")

        if not pinyin:
            errors.append(f"Level {expected_level_num}: Thiếu pinyin.")
        else:
            py_ok, py_err = self.validate_pinyin_format(pinyin, len(hanzi))
            if not py_ok:
                errors.append(f"Level {expected_level_num} ({pinyin}): {py_err}")

        if not han_viet:
            errors.append(f"Level {expected_level_num}: Thiếu âm Hán-Việt.")

        if not meaning:
            errors.append(f"Level {expected_level_num}: Thiếu nghĩa tiếng Việt.")
        else:
            vn_ok, vn_err = self.validate_vietnamese_meaning(meaning)
            if not vn_ok:
                errors.append(f"Level {expected_level_num} ({meaning}): {vn_err}")

        return len(errors) == 0, errors

    def validate_batch(
        self,
        batch_data: Dict[str, Any],
        existing_concepts: Optional[List[str]] = None
    ) -> Tuple[bool, List[str]]:
        """
        Validate complete 1 Nghĩa - 5 Cấp Độ batch:
        - Must pass Negative Context deduplication
        - Must have concept_name_vi
        - Must have exactly 5 levels (Level 1..5)
        """
        errors = []
        concept = str(batch_data.get("concept_name_vi", "")).strip()
        if not concept:
            errors.append("Thiếu tên khái niệm cốt lõi (concept_name_vi).")
        elif existing_concepts:
            neg_ok, neg_err = self.validate_negative_context(concept, existing_concepts)
            if not neg_ok:
                errors.append(neg_err)

        levels = batch_data.get("levels", [])
        if not isinstance(levels, list) or len(levels) != 5:
            errors.append(f"Số lượng level phải đúng bằng 5 (nhận được {len(levels) if isinstance(levels, list) else 0}).")
            return False, errors

        for i, lvl in enumerate(levels, start=1):
            if not isinstance(lvl, dict):
                errors.append(f"Level {i} không phải là đối tượng JSON hợp lệ.")
                continue
            lvl_ok, lvl_errors = self.validate_single_level(lvl, i)
            if not lvl_ok:
                errors.extend(lvl_errors)

        return len(errors) == 0, errors
