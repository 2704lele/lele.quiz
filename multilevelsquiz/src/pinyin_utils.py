import re
from typing import List, Tuple, Optional
from pypinyin import pinyin, Style

def hanzi_to_pinyin_list(hanzi: str) -> List[str]:
    """Convert Chinese text to list of pinyin syllables with tone marks."""
    cleaned = hanzi.strip()
    py_list = pinyin(cleaned, style=Style.TONE)
    return [p[0] for p in py_list if p]

def hanzi_to_full_pinyin(hanzi: str) -> str:
    """Convert Chinese text to space-separated pinyin string with tones."""
    syllables = hanzi_to_pinyin_list(hanzi)
    return " ".join(syllables)

def prepare_word_tuple(hanzi: str, custom_pinyin: str = None) -> Tuple[str, str]:
    hanzi = hanzi.strip()
    full_pinyin = custom_pinyin.strip() if custom_pinyin else hanzi_to_full_pinyin(hanzi)
    return (hanzi, full_pinyin)
