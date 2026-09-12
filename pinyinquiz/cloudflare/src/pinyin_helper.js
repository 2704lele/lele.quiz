/**
 * Pinyin & Hidden Pinyin Utilities (Matching Python pinyin_utils.py logic)
 */

/**
 * Convert full pinyin string into hidden pinyin format with underscores.
 * Default rule: First letter of EACH syllable is revealed, remaining letters are underscores.
 * E.g., "píng guǒ" -> "p _ _ _   g _ _"
 *       "lǎo shī"   -> "l _ _   s _ _"
 *       "xué xiào"  -> "x _ _   x _ _ _"
 * 
 * @param {string} fullPinyin 
 * @param {string} revealMode 'first_char_each_syllable' (default)
 * @returns {string}
 */
export function pinyinToHiddenPinyin(fullPinyin, revealMode = "first_char_each_syllable") {
  if (!fullPinyin || typeof fullPinyin !== "string") {
    return "";
  }

  const syllables = fullPinyin.trim().split(/\s+/);
  if (syllables.length === 0) {
    return "";
  }

  const resultSyllables = [];
  const toneChars = "āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜüĀÁǍÀĒÉĚÈĪÍǏÌŌÓǑÒŪÚǓÙǕǗǙǛÜ";

  for (let i = 0; i < syllables.length; i++) {
    const syl = syllables[i];
    const chars = Array.from(syl);
    if (chars.length === 0) continue;

    const hiddenChars = [];
    for (let j = 0; j < chars.length; j++) {
      const c = chars[j];
      const isAlpha = /[a-zA-Z0-9]/.test(c) || toneChars.includes(c);

      if (!isAlpha) {
        hiddenChars.push(c);
        continue;
      }

      if (revealMode === "first_char_each_syllable") {
        if (j === 0) {
          hiddenChars.push(c.toLowerCase());
        } else {
          hiddenChars.push("_");
        }
      } else if (revealMode === "first_char_only") {
        if (i === 0 && j === 0) {
          hiddenChars.push(c.toLowerCase());
        } else {
          hiddenChars.push("_");
        }
      } else {
        hiddenChars.push("_");
      }
    }

    resultSyllables.push(hiddenChars.join(" "));
  }

  return resultSyllables.join("   ");
}

export function generateHiddenPinyin(fullPinyin) {
  return pinyinToHiddenPinyin(fullPinyin);
}

/**
 * Prepare word tuple object with hanzi, full pinyin, hidden pinyin, and meaning.
 */
export function prepareWordItem(hanzi, pinyin, meaning) {
  const cleanHanzi = (hanzi || "").trim();
  const cleanPinyin = (pinyin || "").trim();
  const cleanMeaning = (meaning || "").trim();
  const hiddenPinyin = pinyinToHiddenPinyin(cleanPinyin);

  return {
    hanzi: cleanHanzi,
    pinyin: cleanPinyin,
    hidden_pinyin: hiddenPinyin,
    meaning: cleanMeaning,
    formatted_cell: `${cleanHanzi} | ${cleanPinyin} | ${hiddenPinyin} | ${cleanMeaning}`
  };
}
