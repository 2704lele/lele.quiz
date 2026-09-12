import re
from typing import List, Tuple
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

def pinyin_to_hidden_pinyin(full_pinyin: str, reveal_mode: str = "first_char_each_syllable") -> str:
    """Convert full pinyin into hidden pinyin with underscores."""
    syllables = full_pinyin.strip().split()
    if not syllables:
        return ""
    
    result_syllables = []
    for i, syl in enumerate(syllables):
        chars = list(syl)
        if not chars:
            continue
        
        hidden_chars = []
        for j, c in enumerate(chars):
            if not c.isalnum() and c not in "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜü":
                hidden_chars.append(c)
                continue
                
            if reveal_mode == "first_char_each_syllable":
                if j == 0:
                    hidden_chars.append(c.lower())
                else:
                    hidden_chars.append("_")
            elif reveal_mode == "first_char_only":
                if i == 0 and j == 0:
                    hidden_chars.append(c.lower())
                else:
                    hidden_chars.append("_")
            else:
                hidden_chars.append("_")
        
        result_syllables.append(" ".join(hidden_chars))
        
    return "   ".join(result_syllables)

def prepare_word_tuple(hanzi: str, custom_pinyin: str = None, custom_hidden: str = None) -> Tuple[str, str, str]:
    hanzi = hanzi.strip()
    full_pinyin = custom_pinyin.strip() if custom_pinyin else hanzi_to_full_pinyin(hanzi)
    hidden_pinyin = custom_hidden.strip() if custom_hidden else pinyin_to_hidden_pinyin(full_pinyin)
    return (hanzi, full_pinyin, hidden_pinyin)
