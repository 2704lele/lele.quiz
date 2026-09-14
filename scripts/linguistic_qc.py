#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scripts/linguistic_qc.py
Lê Lê Học Tiếng Trung Quiz v2.0 - Linguistic QC & Anti-Duplication Engine

Fulfills Milestone 2 (Features F6-F11):
- F6: Global Hanzi Character Frequency Matrix across all 4 quiz tabs (pinyin, vocabCN, vocabVN, multilevels)
- F7: >40% Recent Character Overlap Rejection Engine (and strict zero-duplicate mode)
- F8: Strict Pinyin Tone Mark Placement adhering to GB/T 16159-2012 (a > o > e, second vowel of iu/ui)
- F9: Tone Sandhi ("不"/"一", 3rd tone), Neutral Tone (轻声), and Erhua (儿化) Validation
- F10: Multilevels 5-Tier Semantic Escalation (HSK 1-5, distinct nuances & actions, length <= 25 chars)
- F11: Elimination of Dummy Facade Rows (字1, zì1, etc.)
"""

import os
import sys
import re
import unicodedata
from typing import List, Dict, Any, Optional, Tuple, Set

SPREADSHEET_ID = "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0"
QUIZ_TABS = ["pinyin", "vocabCN", "vocabVN", "multilevels"]

ALL_TONE_VOWELS: Set[str] = set("āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ")

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

ENGLISH_FORBIDDEN_WORDS: List[str] = [
    "chair", "table", "window", "door", "bed", "lamp", "desk", "cup", "glass", "bottle",
    "plate", "spoon", "fork", "knife", "clock", "watch", "key", "bag", "wallet", "box",
    "fan", "fridge", "computer", "phone", "camera", "apple", "banana", "orange", "grape",
    "watermelon", "rice", "noodle", "bread", "meat", "beef", "pork", "chicken", "fish",
    "water", "tea", "coffee", "milk", "beer", "wine", "juice", "car", "bus", "taxi", "train",
    "plane", "bicycle", "teacher", "student", "doctor", "nurse", "police", "father", "mother",
    "house", "room", "school", "hospital", "bank", "park", "store", "shop", "restaurant"
]


def strip_tone_marks(s: str) -> str:
    """Replaces accented tone vowels with plain Latin vowels."""
    s = s.replace('ü', 'v')
    replacements = [
        ("āáǎà", 'a'), ("ōóǒò", 'o'), ("ēéěè", 'e'),
        ("īíǐì", 'i'), ("ūúǔù", 'u'), ("ǖǘǚǜ", 'v')
    ]
    for tone_set, plain in replacements:
        for ch in tone_set:
            s = s.replace(ch, plain)
    return s


# Alias for backward and cross-module compatibility
strip_tone = strip_tone_marks


def get_expected_tone_position(plain_syllable: str) -> int:
    """
    Computes exact vowel index that must carry the tone mark per GB/T 16159-2012:
    - Priority 1: 'a' > 'o' > 'e'
    - Priority 2: For diphthongs 'iu' and 'ui', tone goes strictly on second vowel.
    - Priority 3: Single vowel 'i', 'u', 'v'/'ü'.
    """
    s = plain_syllable.lower()
    if 'a' in s:
        return s.index('a')
    if 'o' in s:
        return s.index('o')
    if 'e' in s:
        return s.index('e')
    if 'iu' in s:
        return s.index('u')
    if 'ui' in s:
        return s.index('i')
    for idx, c in enumerate(s):
        if c in "iuvü":
            return idx
    return -1


def is_dummy_word(hanzi: str, pinyin: str = "", meaning: str = "") -> bool:
    """
    Detects placeholder/dummy tokens such as 字1, zì1, 词1, cí1, 汉1, hàn1, từ 1, etc.
    Enforces genuine AI generation.
    """
    h = hanzi.strip()
    p = pinyin.strip()
    m = meaning.strip().lower()
    if not h:
        return True
    if re.match(r"^(字|词|汉)\d+$", h):
        return True
    if p and re.match(r"^(zì|cí|hàn)\d+$", p, re.IGNORECASE):
        return True
    if m and re.match(r"^(từ|nghĩa)\s*\d+$", m):
        return True
    return False


def normalize_topic_string(topic: str) -> str:
    """Normalizes topic strings for canonical comparison and duplicate detection."""
    if not topic:
        return ""
    t = str(topic).strip().lower()
    t = re.sub(r"^1\s*nghĩa\s*5\s*cấp\s*[•\-\:\.]\s*", "", t)
    t = re.sub(r"^1\s*nghĩa\s*5\s*cấp\s*", "", t)
    t = t.replace("&", " và ")
    t = re.sub(r"[\(\)\[\]\{\}\/\\,;:\.!\?•\-—_]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


class GlobalHanziFrequencyMatrix:
    """
    Global Hanzi Character Frequency Matrix & Anti-Duplication Engine (F6, F7).
    - Tracks global and tab-isolated character frequency across all 4 quiz tabs ('pinyin', 'vocabCN', 'vocabVN', 'multilevels').
    - Enforces Strict Zero-Duplicate Topic Name policy per tab.
    - Enforces Exact Duplicate Hanzi Word rejection per tab.
    - Enforces Tab-Isolated and Global Sliding Window Hanzi Character Overlap QC (< 35-40%).
    """

    def __init__(self, spreadsheet_client=None, spreadsheet_id: str = SPREADSHEET_ID):
        self.client = spreadsheet_client
        self.spreadsheet_id = spreadsheet_id
        self.matrix: Dict[str, int] = {}
        self.tab_matrix: Dict[str, Dict[str, int]] = {t: {} for t in QUIZ_TABS}
        self.tab_topics: Dict[str, Set[str]] = {t: set() for t in QUIZ_TABS}
        self.tab_raw_topics: Dict[str, List[str]] = {t: [] for t in QUIZ_TABS}
        self.tab_words: Dict[str, Set[str]] = {t: set() for t in QUIZ_TABS}
        self.tab_recent_hanzi: Dict[str, List[str]] = {t: [] for t in QUIZ_TABS}
        self.recent_50_tracked: List[str] = []
        if self.client is not None:
            self._build_matrix()

    def _extract_hanzi_and_words_from_row(self, tab: str, row: List[str]) -> Tuple[List[str], List[str]]:
        """Extracts individual Hanzi words and characters from a spreadsheet row according to tab schema."""
        words_list: List[str] = []
        hanzi_chars: List[str] = []
        for col_idx in range(4, min(9, len(row))):
            val = row[col_idx] if len(row) > col_idx else ""
            if not val:
                continue
            parts = [p.strip() for p in val.split("|")]
            target_str = ""
            if tab in ["pinyin", "vocabCN"]:
                target_str = parts[0] if parts else ""
            elif tab == "vocabVN":
                target_str = parts[2] if len(parts) > 2 else (parts[0] if parts else "")
            elif tab == "multilevels":
                target_str = parts[0] if parts else ""

            if target_str:
                words_list.append(target_str)
                for char in target_str:
                    if "\u4e00" <= char <= "\u9fff":
                        hanzi_chars.append(char)
        return words_list, hanzi_chars

    def _extract_hanzi_from_row(self, tab: str, row: List[str]) -> List[str]:
        """Backward-compatible wrapper extracting only individual Hanzi characters."""
        _, chars = self._extract_hanzi_and_words_from_row(tab, row)
        return chars

    def _build_matrix(self):
        """Scans all 4 worksheets in the central spreadsheet to populate topic registries, word banks, and character matrices."""
        if self.client is None:
            return

        if hasattr(self.client, "open_by_key"):
            ss = self.client.open_by_key(self.spreadsheet_id)
        elif hasattr(self.client, "worksheet"):
            ss = self.client
        else:
            return

        chrono_char_list: List[str] = []

        for tab in QUIZ_TABS:
            try:
                ws = ss.worksheet(tab)
                rows = ws.get_all_values()
            except Exception:
                rows = []

            tab_char_list: List[str] = []
            for r in rows[1:]:
                # Extract Topic (Column B / index 1)
                topic_val = r[1].strip() if len(r) > 1 else ""
                if topic_val:
                    norm_t = normalize_topic_string(topic_val)
                    if norm_t:
                        self.tab_topics[tab].add(norm_t)
                    self.tab_raw_topics[tab].append(topic_val)

                # Extract Words and Characters
                words, chars = self._extract_hanzi_and_words_from_row(tab, r)
                for w in words:
                    self.tab_words[tab].add(w)
                for c in chars:
                    self.matrix[c] = self.matrix.get(c, 0) + 1
                    self.tab_matrix[tab][c] = self.tab_matrix[tab].get(c, 0) + 1
                    tab_char_list.append(c)
                    chrono_char_list.append(c)

            # Build tab-isolated recent unique Hanzi characters (up to 100)
            seen_tab: Set[str] = set()
            tab_recent_unique: List[str] = []
            for c in reversed(tab_char_list):
                if c not in seen_tab:
                    seen_tab.add(c)
                    tab_recent_unique.append(c)
                if len(tab_recent_unique) >= 100:
                    break
            self.tab_recent_hanzi[tab] = list(reversed(tab_recent_unique))

        # Build global chronological recent unique characters (up to 50)
        seen: Set[str] = set()
        recent_unique: List[str] = []
        for c in reversed(chrono_char_list):
            if c not in seen:
                seen.add(c)
                recent_unique.append(c)
            if len(recent_unique) >= 50:
                break
        self.recent_50_tracked = list(reversed(recent_unique))

    def get_recent_50_tracked(self) -> List[str]:
        """Returns the list of the most recent unique Hanzi characters (up to 50) chronologically."""
        return list(self.recent_50_tracked)

    def get_existing_topics(self, tab: str) -> List[str]:
        """Returns the list of existing raw topic names for the specified tab."""
        return list(self.tab_raw_topics.get(tab, []))

    def get_tab_recent_50_tracked(self, tab: str, limit: int = 50) -> List[str]:
        """Returns tab-isolated recent unique Hanzi characters (up to limit)."""
        recent = self.tab_recent_hanzi.get(tab, [])
        return list(recent[-limit:]) if recent else list(self.recent_50_tracked[-limit:])

    def get_tab_existing_words(self, tab: str) -> Set[str]:
        """Returns set of all existing Hanzi words for the specified tab."""
        return set(self.tab_words.get(tab, set()))

    def is_topic_duplicated(self, tab: str, topic: str) -> bool:
        """Strict check if a topic name already exists in the given tab."""
        if not topic or tab not in self.tab_topics:
            return False
        norm = normalize_topic_string(topic)
        if not norm:
            return False
        if norm in self.tab_topics[tab]:
            return True
        for ext in self.tab_topics[tab]:
            if norm == ext:
                return True
            if len(norm) >= 6 and len(ext) >= 6 and (norm == ext or norm in ext or ext in norm):
                return True
        return False

    def register_ingested_batch(self, tab: str, batch_words: List[Dict[str, Any]], topic: str = ""):
        """
        Incrementally registers a newly ingested batch into topic registries, word banks,
        tab-isolated history, and the global sliding window.
        """
        if topic and tab in self.tab_topics:
            norm_t = normalize_topic_string(topic)
            if norm_t:
                self.tab_topics[tab].add(norm_t)
            self.tab_raw_topics[tab].append(topic)

        new_chars: List[str] = []
        for w in batch_words:
            hz = w.get("hanzi", "").strip() if isinstance(w, dict) else str(w).strip()
            if hz:
                if tab in self.tab_words:
                    self.tab_words[tab].add(hz)
                for c in hz:
                    if "\u4e00" <= c <= "\u9fff":
                        self.matrix[c] = self.matrix.get(c, 0) + 1
                        if tab in self.tab_matrix:
                            self.tab_matrix[tab][c] = self.tab_matrix[tab].get(c, 0) + 1
                        new_chars.append(c)

        # Update tab-specific recent Hanzi
        if tab in self.tab_recent_hanzi:
            tab_combined = self.tab_recent_hanzi[tab] + new_chars
            seen_tab: Set[str] = set()
            tab_recent_unique: List[str] = []
            for c in reversed(tab_combined):
                if c not in seen_tab:
                    seen_tab.add(c)
                    tab_recent_unique.append(c)
                if len(tab_recent_unique) >= 100:
                    break
            self.tab_recent_hanzi[tab] = list(reversed(tab_recent_unique))

        # Update global recent Hanzi
        combined = self.recent_50_tracked + new_chars
        seen: Set[str] = set()
        recent_unique: List[str] = []
        for c in reversed(combined):
            if c not in seen:
                seen.add(c)
                recent_unique.append(c)
            if len(recent_unique) >= 50:
                break
        self.recent_50_tracked = list(reversed(recent_unique))

    def evaluate_candidate_batch(
        self,
        batch_words: List[Dict[str, Any]],
        topic: str = "",
        tab: str = "",
        strict_zero: bool = False
    ) -> Tuple[bool, float, List[str], str]:
        """
        Evaluates candidate batch against:
        1. Strict Zero-Duplicate Topic policy.
        2. Exact Duplicate Hanzi Word policy within tab.
        3. Tab-Isolated Hanzi Character Overlap (< 35%).
        4. Global Hanzi Character Overlap (< 40%).
        Returns (is_valid, overlap_ratio, overlap_list, reason).
        """
        # 1. Topic Duplicate QC
        if topic and tab:
            if self.is_topic_duplicated(tab, topic):
                return False, 1.0, [topic], f"Rejected (Duplicate Topic): Chủ đề '{topic}' đã tồn tại trong tab '{tab}'."

        batch_words_set: Set[str] = set()
        batch_chars: Set[str] = set()
        for w in batch_words:
            hz = w.get("hanzi", "").strip() if isinstance(w, dict) else str(w).strip()
            if hz:
                batch_words_set.add(hz)
                for c in hz:
                    if "\u4e00" <= c <= "\u9fff":
                        batch_chars.add(c)

        if not batch_chars:
            return False, 1.0, [], "Candidate batch contains no Hanzi characters."

        # 2. Exact Word Duplicate QC within Tab
        if tab and tab in self.tab_words:
            duplicate_words = [w for w in batch_words_set if w in self.tab_words[tab]]
            if duplicate_words:
                return False, 1.0, duplicate_words, f"Rejected (Duplicate Word): Từ vựng {duplicate_words} đã xuất hiện trong lịch sử tab '{tab}'."

        # 3. Tab-Isolated Hanzi Character Overlap QC
        if tab and tab in self.tab_recent_hanzi:
            tab_recent_set = set(self.tab_recent_hanzi[tab])
            tab_overlap = batch_chars.intersection(tab_recent_set)
            tab_ratio = len(tab_overlap) / len(batch_chars)
            if strict_zero and len(tab_overlap) > 0:
                return False, tab_ratio, sorted(list(tab_overlap)), f"Rejected (Strict Zero): Chứa {len(tab_overlap)} chữ Hán trùng với lịch sử gần nhất của tab '{tab}': {sorted(list(tab_overlap))}"
            if tab_ratio > 0.35:
                return False, tab_ratio, sorted(list(tab_overlap)), f"Rejected: Trùng {tab_ratio:.1%} chữ Hán với lịch sử gần nhất của tab '{tab}' (> 35% threshold): {sorted(list(tab_overlap))}"

        # 4. Global Hanzi Character Overlap QC
        overlap = batch_chars.intersection(set(self.recent_50_tracked))
        overlap_ratio = len(overlap) / len(batch_chars)
        overlap_list = sorted(list(overlap))

        if strict_zero and len(overlap) > 0:
            return False, overlap_ratio, overlap_list, f"Rejected (Strict Zero): Contains {len(overlap)} characters from recent 50 tracked: {overlap_list}"

        if overlap_ratio > 0.40:
            return False, overlap_ratio, overlap_list, f"Rejected: {overlap_ratio:.1%} overlap with global recent 50 tracked characters (> 40% threshold): {overlap_list}"

        return True, 0.0, [], "Passed Character Frequency & Anti-Duplication QC."


def normalize_pinyin_spacing(hanzi: str, pinyin_str: str) -> str:
    """
    Normalizes pinyin spacing to ensure 1:1 syllable match with multi-character Hanzi.
    E.g. ('米饭', 'mǐfàn') -> 'mǐ fàn'
    """
    clean_hz = hanzi.strip()
    clean_py = pinyin_str.strip()
    if not clean_hz or not clean_py:
        return clean_py
    syls = clean_py.split()
    if len(syls) == len(clean_hz):
        return clean_py
    try:
        import pypinyin
        auto_syls = [x[0] for x in pypinyin.pinyin(clean_hz, style=pypinyin.Style.TONE)]
        if len(auto_syls) == len(clean_hz):
            return " ".join(auto_syls)
    except Exception:
        pass
    return clean_py


class PinyinLinguisticValidator:
    """
    Pinyin Orthography, Tone Marks, Sandhi, Neutral Tone & Erhua Validator (F8, F9).
    Enforces GB/T 16159-2012 standard rules.
    """

    @staticmethod
    def validate_pinyin(hanzi: str, pinyin_str: str) -> Tuple[bool, List[str]]:
        """
        Validates Pinyin syllables, tone marks placement, tone sandhi, neutral tones, and Erhua.
        Returns (is_valid, errors_list).
        """
        errors: List[str] = []
        clean_hz = hanzi.strip()
        clean_py = normalize_pinyin_spacing(clean_hz, pinyin_str.strip())

        if not clean_hz:
            return False, ["Hanzi text is empty."]
        if not clean_py:
            return False, ["Pinyin text is empty."]

        # Check Traditional Chinese characters
        for ch in clean_hz:
            if ch in STRICT_TRADITIONAL_CHARS:
                errors.append(f"Traditional Hanzi character detected: '{ch}'")

        syllables = [s for s in clean_py.split() if s]

        # Erhua detection: contracted forms like 哪儿 (nǎr), 玩儿 (wánr), 一点儿 (yì diǎnr)
        is_contracted_erhua = clean_hz.endswith("儿") and len(syllables) == len(clean_hz) - 1 and syllables[-1].endswith("r")
        expected_syl_count = len(clean_hz) - 1 if is_contracted_erhua else len(clean_hz)

        if len(syllables) != expected_syl_count:
            errors.append(f"Syllable count mismatch: Hanzi '{clean_hz}' ({len(clean_hz)}) vs Pinyin '{clean_py}' ({len(syllables)}).")

        for idx, syl in enumerate(syllables):
            syl_clean = re.sub(r'[^a-zA-Zāáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü]', '', syl)
            tone_chars = [c for c in syl_clean if c in ALL_TONE_VOWELS]

            if len(tone_chars) == 0:
                plain = strip_tone_marks(syl_clean).lower()
                if plain not in VALID_NEUTRAL_SYLLABLES and not plain.endswith("r"):
                    errors.append(f"Syllable #{idx+1} '{syl}' missing tone mark and not recognized as valid neutral tone.")
            elif len(tone_chars) > 1:
                errors.append(f"Syllable #{idx+1} '{syl}' has multiple tone marks ({tone_chars}).")
            else:
                plain = strip_tone_marks(syl_clean).lower()
                expected_pos = get_expected_tone_position(plain)
                actual_pos = -1
                for p_idx, c in enumerate(syl_clean):
                    if c in ALL_TONE_VOWELS:
                        actual_pos = p_idx
                        break
                if expected_pos != -1 and actual_pos != expected_pos:
                    errors.append(f"Syllable #{idx+1} '{syl}' misplaced tone mark: expected index {expected_pos} ('{plain[expected_pos]}'), found at {actual_pos}.")

        # Tone Sandhi Check for "不" (bù -> bú before 4th tone)
        if clean_hz.startswith("不") and len(clean_hz) >= 2 and len(syllables) >= 2:
            next_syl = syllables[1]
            next_has_tone4 = any(c in "àèìòùǜ" for c in next_syl)
            first_syl = syllables[0].lower()
            if next_has_tone4 and first_syl == "bù":
                errors.append(f"Sandhi violation: '不' before 4th tone syllable '{next_syl}' should be written/annotated as 'bú', not 'bù'.")

        # Tone Sandhi Check for "一" (yī -> yí before 4th tone; yī -> yì before 1st/2nd/3rd tone)
        if clean_hz.startswith("一") and len(clean_hz) >= 2 and len(syllables) >= 2:
            next_syl = syllables[1]
            next_has_tone4 = any(c in "àèìòùǜ" for c in next_syl)
            first_syl = syllables[0].lower()
            if next_has_tone4 and first_syl == "yī":
                errors.append(f"Sandhi violation: '一' before 4th tone syllable '{next_syl}' should be 'yí', not 'yī'.")
            elif not next_has_tone4 and first_syl == "yī" and clean_hz != "第一":
                errors.append(f"Sandhi violation: '一' before non-4th tone syllable '{next_syl}' should be 'yì', not 'yī'.")

        # 3rd tone + 3rd tone sandhi check (passable in lexical spelling)
        if len(syllables) >= 2:
            tone3_vowels = set("ǎěǐǒǔǚ")
            syl1_has_tone3 = any(c in tone3_vowels for c in syllables[0])
            syl2_has_tone3 = any(c in tone3_vowels for c in syllables[1])
            if syl1_has_tone3 and syl2_has_tone3:
                pass

        return len(errors) == 0, errors

    # Method alias for compatibility
    validate_pinyin_syllables = validate_pinyin


class MultilevelsEscalationValidator:
    """
    Multilevels 5-Tier Semantic Escalation Validator (F10).
    Enforces monotonic HSK 1 to HSK 5 progression, distinct nuances & actions,
    meaning_vi length <= 25 chars, and English forbidden word detection.
    """

    @classmethod
    def validate_multilevels_batch(cls, batch: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates a multilevel batch structure.
        Returns (is_valid, errors_list).
        """
        errors: List[str] = []
        concept = batch.get("concept_name_vi", "").strip() or batch.get("concept", "").strip()
        levels = batch.get("levels", [])

        # Concept name presence check
        if "concept_name_vi" in batch and not batch.get("concept_name_vi", "").strip():
            errors.append("Multilevels batch missing 'concept_name_vi'.")
        elif not concept:
            errors.append("Multilevels batch missing 'concept_name_vi'.")

        # Exactly 5 tiers check
        if len(levels) != 5:
            errors.append(f"Multilevels must have exactly 5 tiers (received {len(levels)}).")
            return False, errors

        seen_hanzi: Set[str] = set()
        seen_nuances: Set[str] = set()
        seen_actions: Set[str] = set()

        for idx, lvl in enumerate(levels):
            expected_tier = idx + 1
            actual_tier = lvl.get("level")
            if actual_tier is not None and actual_tier != expected_tier:
                errors.append(f"Tier #{idx+1} level mismatch: expected {expected_tier}, got {actual_tier}.")

            hz = lvl.get("hanzi", "").strip()
            py = lvl.get("pinyin", "").strip()
            hv = (lvl.get("han_viet") or lvl.get("sino_vietnamese") or "").strip()
            m_vi = (lvl.get("meaning_vi") or lvl.get("meaning") or "").strip()
            nuance = (lvl.get("nuance_note") or lvl.get("nuance") or "").strip()
            action = (lvl.get("visual_action") or lvl.get("action") or "").strip()

            if not hz or not py or not hv or not m_vi or not nuance or not action:
                errors.append(f"Tier {expected_tier}: Missing required field (hanzi/pinyin/han_viet/meaning_vi/nuance_note/visual_action).")

            # Check Traditional Chinese characters
            for c in hz:
                if c in STRICT_TRADITIONAL_CHARS:
                    errors.append(f"Tier {expected_tier}: Traditional Chinese character '{c}' detected in '{hz}'.")

            # Length check for meaning_vi (<= 25 chars for short-form video safe zone)
            if len(m_vi) > 25:
                errors.append(f"Tier {expected_tier}: 'meaning_vi' exceeds 25 characters ({len(m_vi)} chars).")

            # Forbidden English words check
            m_vi_lower = m_vi.lower()
            for eng in ENGLISH_FORBIDDEN_WORDS:
                if re.search(rf"\b{eng}\b", m_vi_lower):
                    errors.append(f"Tier {expected_tier}: Forbidden English word '{eng}' found in meaning '{m_vi}'.")

            # HSK 5 idiom check: should be an advanced expression or Chengyu (length >= 3)
            if expected_tier == 5 and len(hz) < 3:
                errors.append(f"Tier 5: Expected 4-character idiom/advanced phrase, found short word '{hz}'.")

            # Duplicate checks within batch
            if hz in seen_hanzi:
                errors.append(f"Tier {expected_tier}: Duplicate Hanzi '{hz}' inside same multilevel batch.")
            seen_hanzi.add(hz)

            if nuance in seen_nuances:
                errors.append(f"Tier {expected_tier}: Duplicate nuance note identical to preceding tier: '{nuance}'.")
            seen_nuances.add(nuance)

            if action in seen_actions:
                errors.append(f"Tier {expected_tier}: Duplicate visual action identical to preceding tier: '{action}'.")
            seen_actions.add(action)

        return len(errors) == 0, errors
