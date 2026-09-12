/**
 * Social Media Metadata Generator (YouTube Shorts, TikTok, Facebook Reels) for VocabVNQuiz
 */

export function cleanTopicDisplay(topic) {
  if (!topic) return "";
  const parts = topic.split("•");
  if (parts.length > 1) {
    return parts[1].trim();
  }
  return topic.trim();
}

export function generateSocialMetadata(topic, level, words = []) {
  const cleanTopic = cleanTopicDisplay(topic);
  const levelTag = (level || "HSK1").replace(/\s+/g, "").toUpperCase();

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
    "thời tiết": "☀️🌧️"
  };

  let chosenEmoji = "🎯✨";
  const topicLower = (topic || "").toLowerCase();
  for (const [key, emo] of Object.entries(emojiMap)) {
    if (topicLower.includes(key)) {
      chosenEmoji = emo;
      break;
    }
  }

  let ytTitle = `Thử Thách Đoán Tiếng Trung ${level}: ${cleanTopic} ${chosenEmoji} #Shorts`;
  if (ytTitle.length > 95) {
    ytTitle = `Đoán Tiếng Trung ${level}: ${cleanTopic} ${chosenEmoji} #Shorts`;
  }

  const wordLines = (words || []).map((w, idx) => `${idx + 1}. ${w.meaning} ➔ ${w.hanzi} (${w.pinyin})`);
  const wordsFormatted = wordLines.join("\n");

  const ytDescription = `🎯 Thử thách phản xạ Tiếng Việt ➔ Tiếng Trung ${level} chủ đề: ${cleanTopic.toUpperCase()}!
Bạn đoán đúng được bao nhiêu từ trên ${(words || []).length} từ? Hãy comment số điểm của bạn bên dưới nhé! 👇

📚 DANH SÁCH TỪ VỰNG TRONG VIDEO:
${wordsFormatted}

🔔 Đừng quên bấm Like, Đăng ký kênh @lelehoctiengtrung và bật chuông thông báo để cùng luyện phản xạ tiếng Trung mỗi ngày cùng Lê Lê nhé!

#lelehoctiengtrung #hoctiengtrung #tiengtrunggiaotiep #vocabquiz #${levelTag.toLowerCase()} #Shorts #learnchinese #hsk`;

  const tiktokCaption = `Đố bạn đoán đúng 5/5 từ tiếng Trung chủ đề ${cleanTopic} này? ${chosenEmoji} Thử ngay xem bạn được mấy điểm nhé! 💬👇 #lelehoctiengtrung #hoctiengtrung #tiengtrung #${levelTag.toLowerCase()} #vocabquiz #xuhuong #learnchinese`;

  const fbCaption = `Thử tài phản xạ dịch Tiếng Việt sang Tiếng Trung ${level} - Chủ đề ${cleanTopic}! ${chosenEmoji}\nBạn tự tin đúng bao nhiêu câu? Comment kết quả bên dưới cùng Lê Lê nha! ✨\n\n#lelehoctiengtrung #tiengtrung #hoctiengtrung #${levelTag.toLowerCase()} #reelsvn #hsk`;

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

export function getBatchMetadata(metadataCell, topic, level, words = []) {
  if (metadataCell && typeof metadataCell === "string" && !metadataCell.startsWith("http") && !metadataCell.startsWith("#ERROR")) {
    let ytTitle = "";
    let ytDescription = "";
    let tiktokCaption = "";
    let fbCaption = "";

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
