/**
 * Social Media Metadata Generator (YouTube Shorts, TikTok, Facebook Reels)
 * Matching the viral templates from Python src/metadata_generator.py
 */

export function cleanTopicDisplay(topic) {
  if (!topic) return "";
  const parts = topic.split("•");
  if (parts.length > 1) {
    return parts[1].trim();
  }
  return topic.trim();
}

/**
 * Generate viral metadata for social platforms
 * @param {string} topic 
 * @param {string} level 
 * @param {Array<{hanzi: string, pinyin: string, meaning: string}>} words 
 * @returns {object}
 */
export function generateSocialMetadata(topic, level, words) {
  const cleanTopic = cleanTopicDisplay(topic);
  const levelTag = (level || "HSK1").replace(/\s+/g, "").toUpperCase();

  // Emoji mappings based on common topics
  const emojiMap = {
    "đồ ăn": "🍎🍜",
    "thức uống": "🧋🥤",
    "đời sống": "🏠✨",
    "gia đình": "👨‍👩‍👧‍👦❤️",
    "số đếm": "🔢⏰",
    "thời gian": "⏳🕰️",
    "địa điểm": "🏫✈️",
    "cảm xúc": "😄🥰",
    "mua sắm": "🛍️🏷️",
    "phương tiện": "🚗🚌",
    "thời tiết": "☀️🌧️",
    "nghề nghiệp": "💼👨‍⚕️",
    "động vật": "🐱🐶",
    "trang phục": "👕👗",
    "giao tiếp": "🗣️💬"
  };

  let chosenEmoji = "🎯✨";
  const topicLower = topic.toLowerCase();
  for (const [key, emo] of Object.entries(emojiMap)) {
    if (topicLower.includes(key)) {
      chosenEmoji = emo;
      break;
    }
  }

  // 1. YouTube Shorts Metadata
  let ytTitle = `Thử Thách Đoán Pinyin ${level}: ${cleanTopic} ${chosenEmoji} | Lê Lê Học Tiếng Trung #Shorts`;
  if (ytTitle.length > 95) {
    ytTitle = `Đoán Pinyin ${level}: ${cleanTopic} ${chosenEmoji} #Shorts`;
  }

  const wordLines = (words || []).map((w, idx) => {
    return `${idx + 1}. ${w.hanzi} (${w.pinyin}): ${w.meaning}`;
  });
  const wordsFormatted = wordLines.join("\n");

  const ytDescription = `🎯 Thử thách đoán Pinyin tiếng Trung ${level} chủ đề: ${cleanTopic.toUpperCase()}!
Bạn đoán đúng được bao nhiêu từ trên ${(words || []).length} từ? Hãy comment số điểm của bạn bên dưới nhé! 👇

📚 DANH SÁCH TỪ VỰNG TRONG VIDEO:
${wordsFormatted}

🔔 Đừng quên bấm Like, Đăng ký kênh @lelehoctiengtrung và bật chuông thông báo để cùng luyện phản xạ tiếng Trung mỗi ngày cùng Lê Lê nhé!

#lelehoctiengtrung #hoctiengtrung #tiengtrunggiaotiep #pinyinquiz #${levelTag.toLowerCase()} #tiengtrungonline #Shorts #learnchinese #hsk`;

  // 2. TikTok Metadata
  const tiktokCaption = `Đố bạn đoán đúng 5/5 Pinyin chủ đề ${cleanTopic} này? ${chosenEmoji} Thử ngay xem bạn được mấy điểm nhé! 💬👇 #lelehoctiengtrung #hoctiengtrung #pinyin #tiengtrungmoibatdau #${levelTag.toLowerCase()} #pinyinquiz #xuhuong #learnchinese`;

  // 3. Facebook Reels Metadata
  const fbCaption = `Thử tài phản xạ đoán Pinyin tiếng Trung ${level} - Chủ đề ${cleanTopic}! ${chosenEmoji}
Bạn tự tin đúng bao nhiêu câu? Comment kết quả bên dưới cùng Lê Lê nha! ✨

#lelehoctiengtrung #tiengtrung #hoctiengtrung #pinyin #${levelTag.toLowerCase()} #reelsvn #hsk`;

  // Formatted Text Summary (Never start with = to avoid Sheet formula error)
  const formattedText = `📝 METADATA CHO VIDEO: ${topic} (${level})
───────────────────────────────────────────────────────────────────

【 1. YOUTUBE SHORTS 】
Tiêu đề (Title):
${ytTitle}

Mô tả (Description):
${ytDescription}

【 2. TIKTOK 】
Caption & Hashtags:
${tiktokCaption}

【 3. FACEBOOK REELS 】
Caption & Hashtags:
${fbCaption}
`;

  return {
    youtube: {
      title: ytTitle,
      description: ytDescription
    },
    tiktok: {
      caption: tiktokCaption
    },
    facebook: {
      caption: fbCaption
    },
    formatted_text: formattedText,
    formattedText: formattedText
  };
}

/**
 * Extract social metadata from Column J text if present,
 * otherwise dynamically generate from topic, level, words.
 */
export function getBatchMetadata(metadataCell, topic, level, words = []) {
  if (metadataCell && typeof metadataCell === "string" && !metadataCell.startsWith("http") && !metadataCell.startsWith("#ERROR")) {
    let ytTitle = "";
    let ytDescription = "";
    let tiktokCaption = "";
    let fbCaption = "";

    // Pattern 1: 【 1. YOUTUBE SHORTS 】 or === 1. YOUTUBE SHORTS ===
    const ytMatch = metadataCell.match(/(?:【\s*1\.\s*YOUTUBE SHORTS\s*】|===\s*1\.\s*YOUTUBE SHORTS\s*===)\s*(?:Tiêu đề \(Title\):)?\s*\n([^\n]+)\s*(?:Mô tả \(Description\):)?\s*\n([\s\S]*?)(?=(?:【\s*2\.\s*TIKTOK\s*】|===\s*2\.\s*TIKTOK\s*===)|$)/i);
    if (ytMatch) {
      ytTitle = (ytMatch[1] || "").trim();
      ytDescription = (ytMatch[2] || "").trim();
    }

    const ttMatch = metadataCell.match(/(?:【\s*2\.\s*TIKTOK\s*】|===\s*2\.\s*TIKTOK\s*===)\s*(?:Caption & Hashtags:)?\s*\n([\s\S]*?)(?=(?:【\s*3\.\s*FACEBOOK REELS\s*】|===\s*3\.\s*FACEBOOK REELS\s*===)|$)/i);
    if (ttMatch) {
      tiktokCaption = (ttMatch[1] || "").trim();
    }

    const fbMatch = metadataCell.match(/(?:【\s*3\.\s*FACEBOOK REELS\s*】|===\s*3\.\s*FACEBOOK REELS\s*===)\s*(?:Caption & Hashtags:)?\s*\n([\s\S]*?)$/i);
    if (fbMatch) {
      fbCaption = (fbMatch[1] || "").trim();
    }

    // Pattern 2: [YouTube]: ... [TikTok]: ...
    if (!ytTitle && metadataCell.includes("[YouTube]:")) {
      const ytSimpleMatch = metadataCell.match(/\[YouTube\]:\s*([^\n]+)/i);
      if (ytSimpleMatch) ytTitle = ytSimpleMatch[1].trim();
      const ttSimpleMatch = metadataCell.match(/\[TikTok\]:\s*([^\n]+)/i);
      if (ttSimpleMatch) tiktokCaption = ttSimpleMatch[1].trim();
    }

    const fallback = generateSocialMetadata(topic, level, words);
    return {
      youtube: {
        title: ytTitle || fallback.youtube.title,
        description: ytDescription || fallback.youtube.description
      },
      tiktok: {
        caption: tiktokCaption || fallback.tiktok.caption
      },
      facebook: {
        caption: fbCaption || fallback.facebook.caption
      },
      formatted_text: metadataCell
    };
  }

  return generateSocialMetadata(topic, level, words);
}

