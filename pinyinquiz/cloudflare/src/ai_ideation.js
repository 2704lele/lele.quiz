/**
 * Multi-AI Ideation Engine for LeLe Hoc Tieng Trung
 *
 * Hierarchy:
 * 1. Google AI Studio (6 keys rotating with model fallback: gemini-2.5-flash, gemini-2.0-flash, gemini-1.5-flash)
 * 2. Agnes AI (4 keys rotating: gpt-4o-mini, gemini-2.5-flash, deepseek-chat)
 * 3. Cloudflare Workers AI (@cf/meta/llama-3.3-70b-instruct, @cf/meta/llama-3.1-8b-instruct, @cf/qwen/qwen2.5-72b-instruct)
 * 4. Built-in High-Quality HSK Vocab Bank (Zero-fail fallback)
 */

import { generateHiddenPinyin } from "./pinyin_helper.js";
import { generateSocialMetadata } from "./metadata_helper.js";
import { getVietnamTimestamp } from "./google_sheets.js";

// Built-in verified HSK 1-2 curated topics bank (Fallback - 100% Single Topics)
const BUILTIN_VOCAB_BANK = [
  {
    topic: "HSK 1 • Đồ Ăn",
    level: "HSK 1",
    words: [
      { hanzi: "米饭", pinyin: "mǐ fàn", meaning: "Cơm" },
      { hanzi: "面条", pinyin: "miàn tiáo", meaning: "Mì sợi" },
      { hanzi: "苹果", pinyin: "píng guǒ", meaning: "Quả táo" },
      { hanzi: "面包", pinyin: "miàn bāo", meaning: "Bánh mì" },
      { hanzi: "鸡蛋", pinyin: "jī dàn", meaning: "Trứng gà" }
    ]
  },
  {
    topic: "HSK 1 • Thức Uống",
    level: "HSK 1",
    words: [
      { hanzi: "喝水", pinyin: "hē shuǐ", meaning: "Uống nước" },
      { hanzi: "牛奶", pinyin: "niú nǎi", meaning: "Sữa bò" },
      { hanzi: "茶", pinyin: "chá", meaning: "Trà" },
      { hanzi: "咖啡", pinyin: "kā fēi", meaning: "Cà phê" },
      { hanzi: "果汁", pinyin: "guǒ zhī", meaning: "Nước hoa quả" }
    ]
  },
  {
    topic: "HSK 2 • Sức Khỏe",
    level: "HSK 2",
    words: [
      { hanzi: "生病", pinyin: "shēng bìng", meaning: "Bị ốm / Bị bệnh" },
      { hanzi: "发烧", pinyin: "fā shāo", meaning: "Phát sốt" },
      { hanzi: "吃药", pinyin: "chī yào", meaning: "Uống thuốc" },
      { hanzi: "跑步", pinyin: "pǎo bù", meaning: "Chạy bộ" },
      { hanzi: "游泳", pinyin: "yóu yǒng", meaning: "Bơi lội" }
    ]
  },
  {
    topic: "HSK 2 • Mua Sắm",
    level: "HSK 2",
    words: [
      { hanzi: "打折", pinyin: "dǎ zhé", meaning: "Giảm giá" },
      { hanzi: "刷卡", pinyin: "shuā kǎ", meaning: "Quẹt thẻ" },
      { hanzi: "现金", pinyin: "xiàn jīn", meaning: "Tiền mặt" },
      { hanzi: "收据", pinyin: "shōu jù", meaning: "Hóa đơn / Biên lai" },
      { hanzi: "找钱", pinyin: "zhǎo qián", meaning: "Trả lại tiền thừa" }
    ]
  },
  {
    topic: "HSK 1 • Số Đếm",
    level: "HSK 1",
    words: [
      { hanzi: "多少", pinyin: "duō shao", meaning: "Bao nhiêu" },
      { hanzi: "块钱", pinyin: "kuài qián", meaning: "Đồng (tiền)" },
      { hanzi: "太贵", pinyin: "tài guì", meaning: "Quá đắt" },
      { hanzi: "便宜", pinyin: "pián yi", meaning: "Rẻ" },
      { hanzi: "买单", pinyin: "mǎi dān", meaning: "Thanh toán" }
    ]
  },
  {
    topic: "HSK 2 • Giao Thông",
    level: "HSK 2",
    words: [
      { hanzi: "飞机", pinyin: "fēi jī", meaning: "Máy bay" },
      { hanzi: "火车", pinyin: "huǒ chē", meaning: "Tàu hỏa" },
      { hanzi: "出租车", pinyin: "chū zū chē", meaning: "Xe taxi" },
      { hanzi: "公共汽车", pinyin: "gōng gòng qì chē", meaning: "Xe buýt" },
      { hanzi: "自行车", pinyin: "zì xíng chē", meaning: "Xe đạp" }
    ]
  },
  {
    topic: "HSK 2 • Thời Tiết",
    level: "HSK 2",
    words: [
      { hanzi: "晴天", pinyin: "qíng tiān", meaning: "Trời nắng" },
      { hanzi: "阴天", pinyin: "yīn tiān", meaning: "Trời râm" },
      { hanzi: "下雨", pinyin: "xià yǔ", meaning: "Mưa rơi" },
      { hanzi: "刮风", pinyin: "guā fēng", meaning: "Gió thổi" },
      { hanzi: "下雪", pinyin: "xià xuě", meaning: "Tuyết rơi" }
    ]
  },
  {
    topic: "HSK 2 • Cảm Xúc",
    level: "HSK 2",
    words: [
      { hanzi: "快乐", pinyin: "kuài lè", meaning: "Vui vẻ / Hạnh phúc" },
      { hanzi: "难过", pinyin: "nán guò", meaning: "Buồn bã" },
      { hanzi: "着急", pinyin: "zháo jí", meaning: "Lo lắng / Vội vàng" },
      { hanzi: "聪明", pinyin: "cōng ming", meaning: "Thông minh" },
      { hanzi: "热情", pinyin: "rè qíng", meaning: "Nhiệt tình" }
    ]
  },
  {
    topic: "HSK 3 • Sinh Hoạt",
    level: "HSK 3",
    words: [
      { hanzi: "锻炼", pinyin: "duàn liàn", meaning: "Rèn luyện / Tập thể dục" },
      { hanzi: "习惯", pinyin: "xí guàn", meaning: "Thói quen" },
      { hanzi: "干净", pinyin: "gān jìng", meaning: "Sạch sẽ" },
      { hanzi: "刷牙", pinyin: "shuā yá", meaning: "Đánh răng" },
      { hanzi: "洗澡", pinyin: "xǐ zǎo", meaning: "Tắm rửa" }
    ]
  },
  {
    topic: "HSK 3 • Công Sở",
    level: "HSK 3",
    words: [
      { hanzi: "会议", pinyin: "huì yì", meaning: "Cuộc họp" },
      { hanzi: "同事", pinyin: "tóng shì", meaning: "Đồng nghiệp" },
      { hanzi: "经理", pinyin: "jīng lǐ", meaning: "Giám đốc / Quản lý" },
      { hanzi: "请假", pinyin: "qǐng jià", meaning: "Xin nghỉ phép" },
      { hanzi: "完成", pinyin: "wán chéng", meaning: "Hoàn thành" }
    ]
  },
  {
    topic: "HSK 3 • Môi Trường",
    level: "HSK 3",
    words: [
      { hanzi: "环境", pinyin: "huán jìng", meaning: "Môi trường" },
      { hanzi: "保护", pinyin: "bǎo hù", meaning: "Bảo vệ" },
      { hanzi: "森林", pinyin: "sēn lín", meaning: "Rừng rậm" },
      { hanzi: "世界", pinyin: "shì jiè", meaning: "Thế giới" },
      { hanzi: "新鲜", pinyin: "xīn xiān", meaning: "Tươi mới / Trong lành" }
    ]
  }
];

function buildSystemPrompt(history = {}, count = 1) {
  const recentTopics = history.recentTopics || [];
  const recentTopicsStr = recentTopics.join(", ");

  // Format past batches summary for LLM context
  const pastBatches = history.pastBatches || [];
  const recentBatchesStr = pastBatches.slice(-15).map(b => `[${b.topic}: ${b.words.join(",")}]`).join(" | ");

    return `Bạn là chuyên gia biên soạn giáo trình HSK cho kênh TikTok/YouTube Shorts "Lê Lê Học Tiếng Trung".
Nhiệm vụ: Tạo ${count} bộ chủ đề từ vựng HSK 1, HSK 2 hoặc HSK 3 hấp dẫn, sinh động, chuẩn sư phạm và tối ưu thuật toán giữ chân người xem (Retention).

QUY TẮC SẮP XẾP 5 TỪ THEO "ĐỒ THỊ CẢM XÚC" (RETENTION EMOTIONAL CURVE):
Mỗi bộ kịch bản gồm đúng 5 câu hỏi/từ được sắp xếp tăng dần độ kịch tính:
- TỪ 1 (CỰC DỄ - INSTANT HOOK): Từ/cụm từ cực kỳ quen thuộc hàng ngày hoặc âm gần gũi (ví dụ: 谢谢, 苹果, 咖啡, 你好, 早上, 喝水) để người xem đoán đúng ngay trong 1 giây đầu, tạo cảm giác tự tin xem hết video.
- TỪ 2 & 3 (CHUẨN TRÌNH ĐỘ - CORE HSK): Các từ vựng cốt lõi chuẩn theo chủ đề và trình độ HSK.
- TỪ 4 (BẪY THANH ĐIỆU / BIẾN ÂM ⚡): Từ dễ gây bẫy phát âm (thanh 1 vs 4, thanh 2 vs 3, phân biệt 买 mǎi / 卖 mài), hoặc chứa biến điệu của "不" (bù/bú), "一" (yī/yí/yì), biến âm 2 thanh 3 đi liền nhau (ví dụ: 你好, 可以). Khiến người xem khựng lại suy nghĩ, tối ưu thời gian giữ chân (Watch Time).
- TỪ 5 (THỬ THÁCH BOSS / THÀNH NGỮ VIRAL 🔥): Từ thử thách nhất, chứa các âm dễ nhầm lẫn (c/z, x/sh, q/ch, zh/ch, 练习 liànxí vs 联系 liánxì) hoặc với HSK 3 là cụm từ 3-4 chữ viral phim ảnh / thành ngữ thông dụng (ví dụ: 真的吗, 没关系, 不好意思, 一清二白). Khiến người xem phải xem lại video (Loop) hoặc nhấn Lưu video (Save).

QUY TẮC BẮT BUỘC VỀ CHỦ ĐỀ & TỪ VỰNG:
1. 🏷️ CHỦ ĐỀ RÕ RÀNG, TỰ NHIÊN:
   - Tên chủ đề ngắn gọn, tự nhiên (Ví dụ: 'HSK 1 • Đồ Ăn', 'HSK 1 • Thức Uống', 'HSK 1 • Gia Đình', 'HSK 2 • Giao Thông', 'HSK 2 • Thời Tiết', 'HSK 2 • Cảm Xúc và Tâm Trạng', 'HSK 2 • Mua Sắm', 'HSK 3 • Sinh Hoạt', 'HSK 3 • Câu Thoại Phim', 'HSK 3 • Thành Ngữ Phổ Biến'...). Các từ nối tự nhiên như 'và', '&' hoàn toàn được chấp nhận.
2. 🌟 ĐA DẠNG HÓA TRÌNH ĐỘ HSK (HSK 1 - HSK 2 - HSK 3):
   - Phân bổ luân phiên, cân bằng giữa các cấp độ HSK 1, HSK 2 và HSK 3. TUYỆT ĐỐI KHÔNG cố định duy nhất một trình độ HSK 1.
3. 🔄 TẦNG SUẤT LẶP LẠI CHỦ ĐỀ (RECURRENCE AFTER 5-6 VIDEOS):
   - CẤM lặp lại các chủ đề đã xuất hiện trong 5-6 video gần nhất: [${recentTopicsStr}].
   - (Sau 5-6 video, có thể sử dụng lại chủ đề đó nhưng với bộ từ mới).
4. 🔒 QUY TẮC CẶP TỪ DUY NHẤT TRONG LỊCH SỬ (NO 2-WORD PAIR OVERLAP):
   - Được phép tái sử dụng tối đa 1 từ của một video cũ bất kỳ trong lịch sử để ôn tập.
   - TUYỆT ĐỐI CẤM 2 từ từng cùng xuất hiện trong 1 video cũ lại cùng xuất hiện trong video mới!
   - Ngữ cảnh các video gần đây: ${recentBatchesStr}
5. 🎯 100% TỪ VỰNG PHẢI LIÊN QUAN TRỰC TIẾP ĐẾN CHỦ ĐỀ:
   - Cả 5 từ vựng BẮT BUỘC thuộc đúng chủ đề đơn đó (Ví dụ: Chủ đề 'Nhà Hàng' thì 5 từ phải về ăn uống/phục vụ, cấm lớp học, bài tập).
6. 🇻🇳 NGHĨA TIẾNG VIỆT 100% (VIETNAMESE MEANING ONLY):
   - Cột nghĩa BẮT BUỘC LÀ TIẾNG VIỆT CHUẨN THUẦN TÚY. TUYỆT ĐỐI CẤM DÙNG TIẾNG ANH (CẤM từ mượn tiếng Anh như 'taxi', 'bus', 'shopping', 'apple', 'chair', 'window'...).
7. 🔤 Pinyin CHUẨN XÁC, CÁCH NHAU TỪNG ÂM TIẾT BẰNG DẤU CÁCH (ví dụ: 'shāng diàn', 'dōng xi', 'dǎ zhé', 'zěn me yàng'). Lưu ý thanh nhẹ (như 'me' trong 怎么样, 'zi' trong 桌子, 'men' trong 我们, 'ba' trong 爸爸, 'ma' trong 妈妈, 'xi' trong 东西, 'nai' trong 奶奶, 'mei' trong 妹妹) không có dấu thanh điệu. Các từ uốn lưỡi Erhua (儿化 - như 哪儿: nǎr, 这儿: zhèr, 那儿: nàr, 玩儿: wánr, 一点儿: yì diǎnr) viết đuôi 'r' hoặc tách âm đều hoàn toàn chuẩn xác.
8. 🇨🇳 100% CHỮ HÁN LÀ GIẢN THỂ (Simplified Chinese), mỗi từ/cụm gồm 1 đến tối đa 4 chữ Hán.
9. 📦 Phản hồi DUY NHẤT một chuỗi JSON hợp lệ.

CẤU TRÚC JSON MẪU:
[
  {
    "topic": "HSK 2 • Nhà Hàng",
    "level": "HSK 2",
    "words": [
      {"hanzi": "喝水", "pinyin": "hē shuǐ", "meaning": "Uống nước"},
      {"hanzi": "菜单", "pinyin": "cài dān", "meaning": "Thực đơn"},
      {"hanzi": "点菜", "pinyin": "diǎn cài", "meaning": "Gọi món"},
      {"hanzi": "不辣", "pinyin": "bù là", "meaning": "Không cay"},
      {"hanzi": "买单", "pinyin": "mǎi dān", "meaning": "Tính tiền"}
    ]
  }
]`;
}

/**
 * Universal JSON response parser with multi-format normalization
 */
export function parseAIResponseJson(rawText) {
  if (!rawText) return null;
  let text = String(rawText).trim();

  // Strip markdown code fences
  text = text.replace(/^```(?:json)?\s*/i, "").replace(/\s*```$/i, "").trim();

  const normalizeResult = (obj) => {
    if (!obj) return null;
    if (Array.isArray(obj)) {
      return obj.filter(item => item && (item.words || item.topic));
    }
    if (typeof obj === "object") {
      if (Array.isArray(obj.topics)) return obj.topics;
      if (Array.isArray(obj.batches)) return obj.batches;
      if (Array.isArray(obj.data)) return obj.data;
      if (Array.isArray(obj.results)) return obj.results;
      if (Array.isArray(obj.words) || obj.topic) return [obj];
      const values = Object.values(obj);
      if (values.length > 0 && values.some(v => v && (v.words || v.topic))) {
        return values.filter(v => v && (v.words || v.topic));
      }
    }
    return null;
  };

  // 1. Direct parse
  try {
    const direct = JSON.parse(text);
    const normalized = normalizeResult(direct);
    if (normalized && normalized.length > 0) return normalized;
  } catch (e) {}

  // 2. Extract JSON Array [ ... ]
  try {
    const arrayMatch = text.match(/\[\s*\{[\s\S]*\}\s*\]/);
    if (arrayMatch) {
      const arr = JSON.parse(arrayMatch[0]);
      const normalized = normalizeResult(arr);
      if (normalized && normalized.length > 0) return normalized;
    }
  } catch (e) {}

  // 3. Extract JSON Object { ... }
  try {
    const objMatch = text.match(/\{[\s\S]*\}/);
    if (objMatch) {
      const obj = JSON.parse(objMatch[0]);
      const normalized = normalizeResult(obj);
      if (normalized && normalized.length > 0) return normalized;
    }
  } catch (e) {}

  return null;
}

/**
 * 1. Call Google AI Studio (Gemini v1beta REST API)
 * Fully compatible with Gemini 2.5 / 2.0 / 1.5 Flash models and multi-part / thinking responses.
 */
async function callGeminiAPI(apiKey, requestedModel, systemPrompt, userPrompt, config = {}) {
  const primaryModel = (requestedModel || "gemini-3.7-flash").trim().replace(/^models\//, "");
  // Keep top 2 models to stay strictly within Cloudflare 50 subrequests limit
  const modelCandidates = [
    primaryModel,
    "gemini-3.7-flash",
    "gemini-3.6-flash"
  ];
  const uniqueModels = [...new Set(modelCandidates.filter(Boolean))];

  const accountId = config.accountId || "3591f5b61af3263ca14af7a1765cc954";
  const gatewayName = config.aiGatewayName || "lelepinyinquiz";

  let lastError = null;

  for (const cleanModel of uniqueModels) {
    const url = gatewayName
      ? `https://gateway.ai.cloudflare.com/v1/${accountId}/${gatewayName}/google-ai-studio/v1beta/models/${cleanModel}:generateContent?key=${apiKey}`
      : `https://generativelanguage.googleapis.com/v1beta/models/${cleanModel}:generateContent?key=${apiKey}`;

    try {
      const isGw = url.includes("gateway.ai.cloudflare.com");
      const response = await fetch(url, {
        method: "POST",
        signal: AbortSignal.timeout(15000),
        headers: {
          "Content-Type": "application/json",
          "x-goog-api-key": apiKey
        },
        body: JSON.stringify({
          systemInstruction: {
            parts: [{ text: systemPrompt }]
          },
          contents: [
            {
              role: "user",
              parts: [{ text: userPrompt }]
            }
          ],
          generationConfig: {
            temperature: 0.7,
            responseMimeType: "application/json"
          }
        })
      });

      if (!response.ok) {
        const errText = await response.text();
        throw new Error(`[Model: ${cleanModel}] (${response.status}): ${errText.substring(0, 150)}`);
      }

      const data = await response.json();
      const candidate = data.candidates?.[0];
      const parts = candidate?.content?.parts || [];

      // Separate actual content from thinking parts in Gemini 2.5 / 2.0 / 3.x
      const textParts = parts.filter(p => !p.thought && p.text).map(p => p.text);
      const rawText = textParts.length > 0
        ? textParts.join("\n")
        : parts.map(p => p.text || "").join("\n");

      const parsed = parseAIResponseJson(rawText);
      if (parsed && parsed.length > 0) {
        return { data: parsed, modelUsed: cleanModel, viaGateway: isGw };
      }

      throw new Error(`[Model: ${cleanModel}] Không thể phân tích định dạng JSON từ phản hồi.`);
    } catch (err) {
      lastError = err;
      console.warn(`⚠️ Gemini attempt (${cleanModel}) failed: ${err.message}`);
      if (err.message && (err.message.includes("API_KEY_INVALID") || err.message.includes("API key not valid"))) {
        throw err;
      }
    }
  }

  throw lastError || new Error("Tất cả các model Gemini đều không phản hồi thành công.");
}

/**
 * 2. Call Agnes AI (apihub.agnes-ai.com / OpenAI-compatible API Gateway)
 */
async function callAgnesAPI(apiKey, baseUrl, requestedModel, systemPrompt, userPrompt) {
  const cleanBase = (baseUrl || "https://apihub.agnes-ai.com/v1").replace(/\/+$/, "");
  const url = `${cleanBase}/chat/completions`;
  const rawModel = (requestedModel || "agnes-2.0-flash").trim();

  const response = await fetch(url, {
    method: "POST",
    signal: AbortSignal.timeout(15000),
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json"
    },
    body: JSON.stringify({
      model: rawModel,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt }
      ],
      temperature: 0.7
    })
  });

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`(${response.status}): ${errText.substring(0, 150)}`);
  }

  const data = await response.json();
  const choice = data.choices?.[0];
  let rawText = choice?.message?.content;

  if (Array.isArray(rawText)) {
    rawText = rawText.map(item => item.text || item.content || "").join("\n");
  } else if (!rawText && choice?.message?.reasoning_content) {
    rawText = choice.message.reasoning_content;
  }

  const parsed = parseAIResponseJson(rawText);
  if (parsed && parsed.length > 0) {
    return { data: parsed, modelUsed: rawModel };
  }

  throw new Error("Không thể phân tích định dạng JSON từ phản hồi Agnes AI.");
}

/**
 * 3. Call Cloudflare Workers AI (Native binding)
 */
async function callCloudflareAI(env, model, systemPrompt, userPrompt) {
  if (!env.AI) return null;

  const rawModel = (model || "@cf/meta/llama-3.3-70b-instruct").trim();
  const modelCandidates = [
    rawModel,
    "@cf/meta/llama-3.3-70b-instruct",
    "@cf/meta/llama-3.1-8b-instruct",
    "@cf/qwen/qwen2.5-72b-instruct",
    "@cf/deepseek-ai/deepseek-r1-distill-qwen-32b"
  ];
  const uniqueModels = [...new Set(modelCandidates.filter(Boolean))];

  for (const cfModel of uniqueModels) {
    try {
      console.log(`[AI-Pool] Trying Cloudflare Workers AI with model: ${cfModel}`);
      const response = await env.AI.run(cfModel, {
        messages: [
          { role: "system", content: systemPrompt },
          { role: "user", content: userPrompt }
        ],
        temperature: 0.7,
        max_tokens: 2048
      });

      let rawOutput = "";
      if (typeof response === "string") {
        rawOutput = response;
      } else if (response?.response) {
        rawOutput = response.response;
      } else if (response?.result?.response) {
        rawOutput = response.result.response;
      } else if (response?.choices?.[0]?.message?.content) {
        rawOutput = response.choices[0].message.content;
      } else if (response?.text) {
        rawOutput = response.text;
      } else {
        rawOutput = JSON.stringify(response);
      }

      const parsed = parseAIResponseJson(rawOutput);
      if (parsed && parsed.length > 0) {
        return { data: parsed, modelUsed: cfModel };
      }
    } catch (err) {
      console.warn(`⚠️ Cloudflare Workers AI (${cfModel}) failed: ${err.message}`);
    }
  }

  return null;
}

/**
 * Gatekeeper #1: Content Uniqueness & Pedagogical Quality Validator
 * Validates AI output BEFORE saving to Google Sheet
 */
export function validateTopicUniquenessAndQuality(topicItem, history = {}) {
  const recentTopics = (history.recentTopics || []).map(t => t.toLowerCase().trim());
  const pastBatches = history.pastBatches || [];

  const errors = [];
  const rawTopicTitle = (topicItem?.topic || "").trim();
  const words = topicItem?.words || [];

  // Clean topic for comparison (e.g. 'HSK 1 • Đồ Ăn' -> 'đồ ăn')
  let cleanTopic = rawTopicTitle.toLowerCase();
  if (cleanTopic.includes("•")) cleanTopic = cleanTopic.split("•")[1].trim();
  else if (cleanTopic.includes("-")) cleanTopic = cleanTopic.split("-")[1].trim();

  // 1. Topic Format & Length Check
  if (rawTopicTitle.length < 2 || rawTopicTitle.length > 50) {
    errors.push(`Chủ đề '${rawTopicTitle}' có độ dài không hợp lệ (từ 2-50 ký tự).`);
  }
  if (rawTopicTitle.includes(";") || rawTopicTitle.includes("|")) {
    errors.push(`Chủ đề '${rawTopicTitle}' chứa ký tự phân tách danh sách (; hoặc |).`);
  }

  // 2. Topic Recurrence Check (Cấm lặp lại trong 5-6 video gần nhất)
  const isRecentTopic = recentTopics.some(rt => {
    let cleanRt = rt;
    if (cleanRt.includes("•")) cleanRt = cleanRt.split("•")[1].trim();
    else if (cleanRt.includes("-")) cleanRt = cleanRt.split("-")[1].trim();
    return cleanRt === cleanTopic;
  });
  if (isRecentTopic) {
    errors.push(`Chủ đề '${rawTopicTitle}' vừa mới xuất hiện trong 5-6 video gần nhất trên kênh. Hãy chọn chủ đề khác!`);
  }

  // 3. Exactly 5 Words Check
  if (!Array.isArray(words) || words.length !== 5) {
    errors.push(`Số lượng từ vựng không đúng 5 từ (hiện có: ${words.length}).`);
  }

  // 4. Internal Duplicates Check within the batch
  const newHanziList = [];
  const internalDuplicates = new Set();

  for (const w of words) {
    const hz = (w?.hanzi || "").trim();
    if (!hz) {
      errors.push("Phát hiện từ vựng bị rỗng chữ Hán.");
      continue;
    }
    if (internalDuplicates.has(hz)) {
      errors.push(`Từ '${hz}' bị lặp lại 2 lần trong cùng một video.`);
    }
    internalDuplicates.add(hz);
    newHanziList.push(hz);
  }

  // 5. Strict Pair Overlap Check against ALL Past Batches in History
  // (Cho phép dùng lại 1 từ của video cũ để ôn tập, CẤM trùng >= 2 từ từ cùng 1 video cũ)
  if (Array.isArray(pastBatches) && pastBatches.length > 0) {
    for (const pb of pastBatches) {
      const pastWords = pb.words || [];
      const overlap = newHanziList.filter(hz => pastWords.includes(hz));
      if (overlap.length >= 2) {
        errors.push(`Vi phạm nguyên tắc: Trùng cặp ${overlap.length} từ [${overlap.join(", ")}] với video cũ #${pb.id} (${pb.topic}). Mỗi video cũ tối đa chỉ được trùng 1 từ!`);
      }
    }
  }

  // 6. Strict Vietnamese Meaning Check (Reject English words like Chair, Window, Lamp, Bookshelf)
  const englishWordPattern = /\b(chair|window|lamp|bookshelf|washing machine|table|door|bed|house|school|teacher|student|father|mother|brother|sister|water|apple|bread|food|drink|rice|noodle|dog|cat|car|bus|train|airplane|taxi|bicycle|happy|sad|angry|afraid|cold|hot|warm|weather|rain|snow|sun|wind|cloud|sky|money|cheap|expensive|buy|sell|eat|drink|watch|look|see|listen|speak|read|write|learn|study|work|office|hospital|doctor|nurse)\b/i;

  for (let i = 0; i < words.length; i++) {
    const m = (words[i]?.meaning || "").trim();
    if (!m) {
      errors.push(`Từ #${i + 1} (${words[i]?.hanzi}): Nghĩa tiếng Việt bị rỗng.`);
    } else if (englishWordPattern.test(m)) {
      errors.push(`Từ #${i + 1} (${words[i]?.hanzi}): Nghĩa '${m}' bị trả về bằng Tiếng Anh thay vì Tiếng Việt.`);
    }
  }

  // 7. Semantic Relevance Check (Chặn các trường hợp vô lý "râu ông nọ cắm cằm bà kia")
  const lowerTopic = rawTopicTitle.toLowerCase();
  const allMeanings = words.map(w => (w?.meaning || "").toLowerCase()).join(" ");
  if ((lowerTopic.includes("nhà hàng") || lowerTopic.includes("quán ăn") || lowerTopic.includes("đồ ăn")) &&
      (allMeanings.includes("sách giáo khoa") || allMeanings.includes("phòng học") || allMeanings.includes("bài tập"))) {
    errors.push("Lệch chủ đề nghiêm trọng: Chủ đề Nhà hàng/Ăn uống nhưng từ vựng lại chứa trường học/bài tập!");
  }
  if ((lowerTopic.includes("thời gian") || lowerTopic.includes("ngày tháng")) &&
      (allMeanings.includes("ghế") || allMeanings.includes("cửa sổ") || allMeanings.includes("máy giặt"))) {
    errors.push("Lệch chủ đề nghiêm trọng: Chủ đề Thời gian nhưng từ vựng lại chứa đồ đạc gia dụng!");
  }

  return {
    isValid: errors.length === 0,
    errors: errors,
    newWords: newHanziList
  };
}

/**
 * Multi-Provider Key Rotation & Failover Orchestrator with Built-in Quality Gatekeeper
 * (Google AI Studio + Agnes AI + Cloudflare Workers AI + Curated Vocab Bank)
 */
export async function generateBatchesWithMultiAI(env, config, vocabHistory = {}, count = 1) {
  const systemPrompt = buildSystemPrompt(vocabHistory, count);
  const userPrompt = `Hãy tạo ngay ${count} bộ chủ đề từ vựng HSK 1 - HSK 3 mới nhất dạng JSON chuẩn.`;

  let resultTopics = null;
  let providerUsed = "Fallback VOCAB_BANK";
  let anyAiSucceeded = false;
  const diagnostics = {
    gemini: [],
    agnes: [],
    cloudflare: []
  };

  // 1. Try Google AI Studio Keys (Rotating pool)
  if (config.geminiApiKeys && config.geminiApiKeys.length > 0) {
    const shuffledGeminiKeys = [...config.geminiApiKeys].sort(() => 0.5 - Math.random());

    for (let i = 0; i < shuffledGeminiKeys.length; i++) {
      const key = shuffledGeminiKeys[i];
      const keyShort = `${key.substring(0, 6)}...${key.substring(key.length - 4)}`;
      try {
        console.log(`[AI-Pool] Trying Google AI Studio (Key ${i + 1}/${shuffledGeminiKeys.length}: ${keyShort}) for count=${count}...`);
        const res = await callGeminiAPI(key, config.geminiModel, systemPrompt, userPrompt, config);
        if (res && Array.isArray(res.data) && res.data.length > 0) {
          const validCandidates = [];
          const tempHistory = {
            recentTopics: [...(vocabHistory.recentTopics || [])],
            pastBatches: [...(vocabHistory.pastBatches || [])]
          };

          for (const candidate of res.data) {
            const gateCheck = validateTopicUniquenessAndQuality(candidate, tempHistory);
            if (gateCheck.isValid) {
              validCandidates.push(candidate);
              tempHistory.recentTopics.push(candidate.topic);
              tempHistory.pastBatches.push({
                id: "temp",
                topic: candidate.topic,
                words: (candidate.words || []).map(w => w.hanzi)
              });
              if (validCandidates.length >= count) break;
            } else {
              console.warn(`🛑 [Gatekeeper Rejected] Candidate violated uniqueness: ${gateCheck.errors.join("; ")}`);
            }
          }

          if (validCandidates.length > 0) {
            resultTopics = validCandidates;
            const gwTag = res.viaGateway ? " (AI Gateway)" : "";
            providerUsed = `Google AI Studio${gwTag} (${res.modelUsed} - Key #${i + 1})`;
            anyAiSucceeded = true;
            console.log(`✨ Successfully generated and PASSED Gatekeeper with ${validCandidates.length}/${count} topics from ${providerUsed}!`);
            break;
          } else {
            diagnostics.gemini.push(`Key #${i + 1} (${keyShort}): Không có chủ đề nào vượt qua Gatekeeper`);
          }
        }
      } catch (err) {
        const cleanErr = (err.message || "Unknown error").substring(0, 180);
        diagnostics.gemini.push(`Key #${i + 1} (${keyShort}): ${cleanErr}`);
        console.warn(`⚠️ Google AI Studio Key #${i + 1} failed: ${cleanErr}. Rotating to next key...`);
      }
    }
  }

  // 2. Try Agnes AI Keys if Gemini not successful or incomplete
  if ((!resultTopics || resultTopics.length < count) && config.agnesApiKeys && config.agnesApiKeys.length > 0) {
    const shuffledAgnesKeys = [...config.agnesApiKeys].sort(() => 0.5 - Math.random());

    for (let i = 0; i < shuffledAgnesKeys.length; i++) {
      const key = shuffledAgnesKeys[i];
      const keyShort = `${key.substring(0, 6)}...${key.substring(key.length - 4)}`;
      try {
        console.log(`[AI-Pool] Trying Agnes AI (Key ${i + 1}/${shuffledAgnesKeys.length}: ${keyShort}) for count=${count}...`);
        const res = await callAgnesAPI(key, config.agnesBaseUrl, config.agnesModel, systemPrompt, userPrompt);
        if (res && Array.isArray(res.data) && res.data.length > 0) {
          const validCandidates = [];
          const tempHistory = {
            recentTopics: [...(vocabHistory.recentTopics || [])],
            pastBatches: [...(vocabHistory.pastBatches || [])]
          };

          for (const candidate of res.data) {
            const gateCheck = validateTopicUniquenessAndQuality(candidate, tempHistory);
            if (gateCheck.isValid) {
              validCandidates.push(candidate);
              tempHistory.recentTopics.push(candidate.topic);
              tempHistory.pastBatches.push({
                id: "temp",
                topic: candidate.topic,
                words: (candidate.words || []).map(w => w.hanzi)
              });
              if (validCandidates.length >= count) break;
            } else {
              console.warn(`🛑 [Gatekeeper Rejected] Agnes AI candidate violated uniqueness: ${gateCheck.errors.join("; ")}`);
            }
          }

          if (validCandidates.length > 0) {
            resultTopics = validCandidates;
            providerUsed = `Agnes AI (${res.modelUsed} - Key #${i + 1})`;
            anyAiSucceeded = true;
            console.log(`✨ Successfully generated and PASSED Gatekeeper with ${validCandidates.length}/${count} topics from ${providerUsed}!`);
            break;
          } else {
            diagnostics.agnes.push(`Key #${i + 1} (${keyShort}): Không có chủ đề nào vượt qua Gatekeeper`);
          }
        }
      } catch (err) {
        const cleanErr = (err.message || "Unknown error").substring(0, 180);
        diagnostics.agnes.push(`Key #${i + 1} (${keyShort}): ${cleanErr}`);
        console.warn(`⚠️ Agnes AI Key #${i + 1} failed: ${cleanErr}. Rotating to next key...`);
      }
    }
  }

  // 3. Try Cloudflare Workers AI if Gemini and Agnes are unavailable
  if ((!resultTopics || resultTopics.length < count) && env && env.AI) {
    const cfModel = config.aiModel || "@cf/meta/llama-3.3-70b-instruct";
    try {
      console.log(`[AI-Pool] Trying Cloudflare Workers AI (${cfModel}) for count=${count}...`);
      const cfRes = await callCloudflareAI(env, cfModel, systemPrompt, userPrompt);
      if (cfRes && Array.isArray(cfRes.data) && cfRes.data.length > 0) {
        const validCandidates = [];
        const tempHistory = {
          recentTopics: [...(vocabHistory.recentTopics || [])],
          pastBatches: [...(vocabHistory.pastBatches || [])]
        };

        for (const candidate of cfRes.data) {
          const gateCheck = validateTopicUniquenessAndQuality(candidate, tempHistory);
          if (gateCheck.isValid) {
            validCandidates.push(candidate);
            tempHistory.recentTopics.push(candidate.topic);
            tempHistory.pastBatches.push({
              id: "temp",
              topic: candidate.topic,
              words: (candidate.words || []).map(w => w.hanzi)
            });
            if (validCandidates.length >= count) break;
          }
        }

        if (validCandidates.length > 0) {
          resultTopics = validCandidates;
          providerUsed = `Cloudflare Workers AI (${cfRes.modelUsed})`;
          anyAiSucceeded = true;
          console.log(`✨ Successfully generated and PASSED Gatekeeper with ${validCandidates.length}/${count} topics from ${providerUsed}!`);
        }
      }
    } catch (err) {
      const cleanErr = (err.message || "Unknown error").substring(0, 180);
      diagnostics.cloudflare.push(`CF AI (${cfModel}): ${cleanErr}`);
      console.warn("⚠️ Cloudflare Workers AI failed:", cleanErr);
    }
  }

  // 4. Fallback or Supplement with Curated Vocab Bank if needed
  if (!resultTopics || resultTopics.length < count) {
    console.log(`ℹ️ Supplementing ${count - (resultTopics?.length || 0)} topics from Built-in High Quality Vocab Bank...`);
    const recentTopics = (vocabHistory.recentTopics || []).map(t => t.toLowerCase().trim());
    const pastBatches = vocabHistory.pastBatches || [];

    const validBankTopics = BUILTIN_VOCAB_BANK.filter(topicItem => {
      const topicTitle = (topicItem.topic || "").toLowerCase();
      let cleanTopic = topicTitle;
      if (cleanTopic.includes("•")) cleanTopic = cleanTopic.split("•")[1].trim();

      // Check recent topic
      if (recentTopics.some(rt => rt.includes(cleanTopic))) return false;

      // Check pair overlap >= 2 with past batches
      const bankWords = (topicItem.words || []).map(w => w.hanzi);
      for (const pb of pastBatches) {
        const overlap = bankWords.filter(hz => (pb.words || []).includes(hz));
        if (overlap.length >= 2) return false;
      }
      return true;
    });

    const chosenBank = validBankTopics.length > 0 ? validBankTopics : BUILTIN_VOCAB_BANK;
    const shuffledBank = [...chosenBank].sort(() => 0.5 - Math.random());
    const neededCount = count - (resultTopics?.length || 0);
    const bankSupplement = shuffledBank.slice(0, neededCount);

    if (!resultTopics || resultTopics.length === 0) {
      resultTopics = bankSupplement;
      providerUsed = "Fallback VOCAB_BANK (Single Topic Verified)";
    } else {
      resultTopics = [...resultTopics, ...bankSupplement];
    }
  }

  // Auto-enrich each word with hidden_pinyin
  const enrichedTopics = resultTopics.map(topicItem => {
    const rawWords = topicItem.words || [];
    const words = rawWords.map(w => {
      const hanzi = (w.hanzi || "").trim();
      const pinyin = (w.pinyin || "").trim();
      const meaning = (w.meaning || "").trim();
      const hidden_pinyin = w.hidden_pinyin || generateHiddenPinyin(pinyin);
      return {
        hanzi,
        pinyin,
        hidden_pinyin,
        meaning
      };
    });

    return {
      topic: topicItem.topic || "HSK 1-2 • Từ Vựng Thông Dụng",
      level: topicItem.level || "HSK 1-2",
      words: words
    };
  });

  return {
    topics: enrichedTopics,
    provider: providerUsed,
    isFallbackBank: !anyAiSucceeded,
    diagnostics: diagnostics
  };
}

/**
 * Format generated topics into 16-column Google Sheet rows
 */
export function formatTopicsToSheetRows(topics, providerUsed, startId = 1) {
  const rows = [];
  const now = getVietnamTimestamp();

  topics.forEach((t, idx) => {
    const rowId = startId + idx;
    const meta = generateSocialMetadata(t.topic, t.level, t.words);
    const metaText = meta.formatted_text || "";

    // Format 5 words into "hanzi | pinyin | hidden_pinyin | meaning"
    const wordCols = [];
    for (let wIdx = 0; wIdx < 5; wIdx++) {
      const w = t.words[wIdx];
      if (w) {
        wordCols.push(`${w.hanzi} | ${w.pinyin} | ${w.hidden_pinyin} | ${w.meaning}`);
      } else {
        wordCols.push("");
      }
    }

    const row = [
      String(rowId),                  // Col A: ID
      t.topic,                        // Col B: Topic
      t.level,                        // Col C: Level
      "Pending",                      // Col D: Status
      wordCols[0] || "",              // Col E: Word 1
      wordCols[1] || "",              // Col F: Word 2
      wordCols[2] || "",              // Col G: Word 3
      wordCols[3] || "",              // Col H: Word 4
      wordCols[4] || "",              // Col I: Word 5
      metaText,                       // Col J: Metadata (Clean formatted text)
      "",                             // Col K: Video (GDrive Link)
      "",                             // Col L: Youtube
      "",                             // Col M: Tiktok
      "",                             // Col N: Facebook
      now,                            // Col O: Created At
      `Sinh bởi: ${providerUsed}`     // Col P: Notes
    ];

    rows.push(row);
  });

  return rows;
}
