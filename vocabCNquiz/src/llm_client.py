import os
import sys
import re
import time
import json
import logging
import requests
from typing import List, Dict, Any, Optional, Union

logger = logging.getLogger("LLMClient")

DEFAULT_LLM_URL = os.getenv("LLM_BASE_URL", "")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.7-flash")
FALLBACK_GEMINI_MODELS = ["gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.6-flash-high", "gemini-3.5-flash"]
GEMINI_ENDPOINT_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Rich pool of verified HSK 1, HSK 2, HSK 3 vocabulary topics complying 100% with Gatekeeper 1 standards
FALLBACK_VOCAB_BANK = [
    # --- HSK 1 ---
    ("Gia Đình Thân Yêu", "HSK 1", [
        ("爸爸", "bà ba", "Bố / Ba"),
        ("妈妈", "mā ma", "Mẹ"),
        ("儿子", "ér zi", "Con trai"),
        ("女儿", "nǚ ér", "Con gái"),
        ("朋友", "péng you", "Bạn bè")
    ]),
    ("Thời Gian Hàng Ngày", "HSK 1", [
        ("今天", "jīn tiān", "Hôm nay"),
        ("明天", "míng tiān", "Ngày mai"),
        ("昨天", "zuó tiān", "Hôm qua"),
        ("现在", "xiàn zài", "Bây giờ"),
        ("点钟", "diǎn zhōng", "Giờ giấc")
    ]),
    ("Đồ Ăn & Thức Uống", "HSK 1", [
        ("米饭", "mǐ fàn", "Cơm"),
        ("面条", "miàn tiáo", "Mì sợi"),
        ("苹果", "píng guǒ", "Quả táo"),
        ("茶水", "chá shuǐ", "Nước trà"),
        ("牛奶", "niú nǎi", "Sữa tươi")
    ]),
    ("Địa Điểm Thân Quen", "HSK 1", [
        ("学校", "xué xiào", "Trường học"),
        ("医院", "yī yuàn", "Bệnh viện"),
        ("商店", "shāng diàn", "Cửa hàng"),
        ("饭馆", "fàn guǎn", "Quán ăn / Nhà hàng"),
        ("家", "jiā", "Nhà / Gia đình")
    ]),
    ("Đồ Dùng Hàng Ngày", "HSK 1", [
        ("桌子", "zhuō zi", "Cái bàn"),
        ("椅子", "yǐ zi", "Cái ghế"),
        ("衣服", "yī fu", "Quần áo"),
        ("杯子", "bēi zi", "Cái cốc / ly"),
        ("书本", "shū běn", "Sách vở")
    ]),
    ("Hành Động Cơ Bản", "HSK 1", [
        ("喝水", "hē shuǐ", "Uống nước"),
        ("吃饭", "chī fàn", "Ăn cơm"),
        ("看书", "kàn shū", "Đọc sách"),
        ("听歌", "tīng gē", "Nghe nhạc"),
        ("睡觉", "shuì jiào", "Đi ngủ")
    ]),
    ("Số Đếm & Mua Bán", "HSK 1", [
        ("多少", "duō shao", "Bao nhiêu"),
        ("块钱", "kuài qián", "Đồng tiền"),
        ("太贵", "tài guì", "Quá đắt"),
        ("便宜", "pián yi", "Rẻ"),
        ("买单", "mǎi dān", "Thanh toán")
    ]),

    # --- HSK 2 ---
    ("Giao Tiếp Xã Hội", "HSK 2", [
        ("帮助", "bāng zhù", "Giúp đỡ"),
        ("介绍", "jiè shào", "Giới thiệu"),
        ("欢迎", "huān yíng", "Chào đón"),
        ("回答", "huí dá", "Trả lời"),
        ("希望", "xī wàng", "Hy vọng")
    ]),
    ("Phương Tiện Giao Thông", "HSK 2", [
        ("飞机", "fēi jī", "Máy bay"),
        ("出租车", "chū zū chē", "Xe tắc-xi"),
        ("公共汽车", "gōng gòng qì chē", "Xe buýt"),
        ("火车站", "huǒ chē zhàn", "Ga tàu hỏa"),
        ("自行车", "zì xíng chē", "Xe đạp")
    ]),
    ("Thời Tiết Bốn Mùa", "HSK 2", [
        ("晴天", "qíng tiān", "Trời nắng"),
        ("下雨", "xià yǔ", "Trời mưa"),
        ("下雪", "xià xuě", "Tuyết rơi"),
        ("刮风", "guā fēng", "Gió thổi"),
        ("温度", "wēn dù", "Nhiệt độ")
    ]),
    ("Cảm Xúc & Tâm Trạng", "HSK 2", [
        ("快乐", "kuài lè", "Vui vẻ"),
        ("难过", "nán guò", "Buồn bã"),
        ("着急", "zháo jí", "Lo lắng / Nóng vội"),
        ("聪明", "cōng míng", "Thông minh"),
        ("热情", "rè qíng", "Nhiệt tình")
    ]),
    ("Mua Sắm Hàng Ngày", "HSK 2", [
        ("打折", "dǎ zhé", "Giảm giá"),
        ("刷卡", "shuā kǎ", "Quẹt thẻ"),
        ("现金", "xiàn jīn", "Tiền mặt"),
        ("找钱", "zhǎo qián", "Trả lại tiền thừa"),
        ("收据", "shōu jù", "Hóa đơn")
    ]),
    ("Sức Khỏe & Thể Thao", "HSK 2", [
        ("生病", "shēng bìng", "Bị ốm / Bệnh"),
        ("发烧", "fā shāo", "Phát sốt"),
        ("吃药", "chī yào", "Uống thuốc"),
        ("跑步", "pǎo bù", "Chạy bộ"),
        ("游泳", "yóu yǒng", "Bơi lội")
    ]),

    # --- HSK 3 ---
    ("Môi Trường Làm Việc", "HSK 3", [
        ("同事", "tóng shì", "Đồng nghiệp"),
        ("会议", "huì yì", "Cuộc họp"),
        ("经理", "jīng lǐ", "Giám đốc / Quản lý"),
        ("请假", "qǐng jià", "Xin nghỉ phép"),
        ("加班", "jiā bān", "Tăng ca")
    ]),
    ("Thói Quen Sinh Hoạt", "HSK 3", [
        ("锻炼", "duàn liàn", "Rèn luyện / Tập thể dục"),
        ("习惯", "xí guàn", "Thói quen"),
        ("干净", "gān jìng", "Sạch sẽ"),
        ("刷牙", "shuā yá", "Đánh răng"),
        ("洗澡", "xǐ zǎo", "Tắm rửa")
    ]),
    ("Giao Tiếp Xã Giao", "HSK 3", [
        ("礼貌", "lǐ mào", "Lịch sự"),
        ("客气", "kè qi", "Khách sáo"),
        ("原谅", "yuán liàng", "Tha thứ"),
        ("感谢", "gǎn xiè", "Cảm ơn"),
        ("祝贺", "zhù hè", "Chúc mừng")
    ]),
    ("Du Lịch & Khám Phá", "HSK 3", [
        ("行李", "xíng li", "Hành lý"),
        ("照相机", "zhào xiàng jī", "Máy ảnh"),
        ("地图", "dì tú", "Bản đồ"),
        ("护照", "hù zhào", "Hộ chiếu"),
        ("风景", "fēng jǐng", "Phong cảnh")
    ]),
    ("Môi Trường Tự Nhiên", "HSK 3", [
        ("环境", "huán jìng", "Môi trường"),
        ("保护", "bǎo hù", "Bảo vệ"),
        ("森林", "sēn lín", "Rừng rậm"),
        ("世界", "shì jiè", "Thế giới"),
        ("新鲜", "xīn xiān", "Trong lành / Tươi mới")
    ]),
    ("Sức Khỏe Đời Sống", "HSK 3", [
        ("感冒", "gǎn mào", "Cảm cúm"),
        ("检查", "jiǎn chá", "Kiểm tra / Khám"),
        ("健康", "jiàn kāng", "Sức khỏe"),
        ("舒服", "shū fu", "Dễ chịu / Thoải mái"),
        ("疼", "téng", "Đau đớn")
    ]),
    ("Sở Thích & Giải Trí", "HSK 1", [
        ("看书", "kàn shū", "Đọc sách"),
        ("听音乐", "tīng yīn yuè", "Nghe nhạc"),
        ("画画", "huà huà", "Vẽ tranh"),
        ("跳舞", "tiào wǔ", "Nhảy múa"),
        ("唱歌", "chàng gē", "Hát ca")
    ]),
    ("Màu Sắc & Hình Dạng", "HSK 1", [
        ("红色", "hóng sè", "Màu đỏ"),
        ("黄色", "huáng sè", "Màu vàng"),
        ("白色", "bái sè", "Màu trắng"),
        ("黑色", "hēi sè", "Màu đen"),
        ("蓝色", "lán sè", "Màu xanh da trời")
    ]),
    ("Động Vật Trong Nhà", "HSK 1", [
        ("猫", "māo", "Con mèo"),
        ("狗", "gǒu", "Con chó"),
        ("鸟", "niǎo", "Con chim"),
        ("鱼", "yú", "Con cá"),
        ("兔子", "tù zi", "Con thỏ")
    ]),
    ("Trang Phục & Thời Trang", "HSK 2", [
        ("衣服", "yī fu", "Quần áo"),
        ("裤子", "kù zi", "Quần dài"),
        ("鞋子", "xié zi", "Đôi giày"),
        ("帽子", "mào zi", "Cái mũ"),
        ("裙子", "qún zi", "Váy vóc")
    ]),
    ("Nghề Nghiệp & Công Việc", "HSK 2", [
        ("医生", "yī shēng", "Bác sĩ"),
        ("老师", "lǎo shī", "Giáo viên"),
        ("服务员", "fú wù yuán", "Nhân viên phục vụ"),
        ("司机", "sī jī", "Tài xế"),
        ("记者", "jì zhě", "Nhà báo")
    ]),
    ("Trường Học & Học Tập", "HSK 2", [
        ("考试", "kǎo shì", "Thi cử"),
        ("作业", "zuò yè", "Bài tập về nhà"),
        ("课本", "kè běn", "Sách giáo khoa"),
        ("教室", "jiào shì", "Phòng học"),
        ("成绩", "chéng jì", "Thành tích")
    ]),
    ("Văn Phòng & Thiết Bị", "HSK 3", [
        ("电脑", "diàn nǎo", "Máy tính"),
        ("打印机", "dǎ yìn jī", "Máy in"),
        ("传真", "chuán zhēn", "Bức điện / Công văn"),
        ("文件", "wén jiàn", "Tài liệu"),
        ("会议室", "huì yì shì", "Phòng họp")
    ]),
    ("Giao Thông & Đường Xá", "HSK 3", [
        ("马路", "mǎ lù", "Đường lộ"),
        ("红绿灯", "hóng lǜ dēng", "Đèn giao thông"),
        ("堵车", "dǔ chē", "Kẹt xe"),
        ("立交桥", "lì jiāo qiáo", "Cầu vượt"),
        ("高速公路", "gāo sù gōng lù", "Đường cao tốc")
    ]),
    ("Lễ Hội & Kỷ Niệm", "HSK 3", [
        ("春节", "chūn jié", "Tết Nguyên Đán"),
        ("节日", "jié rì", "Ngày lễ"),
        ("礼物", "lǐ wù", "Món quà"),
        ("庆祝", "qìng zhù", "Chúc mừng / Ăn mừng"),
        ("聚会", "jù huì", "Tụ họp / Tụ tập")
    ])
]


def mask_key(key: Optional[str]) -> str:
    """
    Mask an API key for safe logging.
    Never logs full plaintext keys.
    """
    if not key or not str(key).strip():
        return "None"
    k = str(key).strip()
    if len(k) <= 8:
        return "****"
    return f"{k[:6]}...****"


def parse_gemini_keys(keys_input: Optional[Union[str, List[str]]] = None) -> List[str]:
    """
    Parse ephemeral Gemini API keys from argument, list, or environment variables.
    Supports comma-separated strings, newline-separated strings, or list of keys.
    """
    keys = []

    # 1. From direct input argument
    if keys_input:
        if isinstance(keys_input, list):
            for item in keys_input:
                if item and isinstance(item, str):
                    for sub in re.split(r"[\n,;]+", item):
                        clean = sub.strip()
                        if clean and clean not in keys:
                            keys.append(clean)
        elif isinstance(keys_input, str):
            for sub in re.split(r"[\n,;]+", keys_input):
                clean = sub.strip()
                if clean and clean not in keys:
                    keys.append(clean)

    # 2. From environment variables (GEMINI_API_KEYS, GEMINI_API_KEY, GOOGLE_API_KEY)
    if not keys:
        env_raw = os.getenv("GEMINI_API_KEYS") or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        if env_raw:
            for sub in re.split(r"[\n,;]+", env_raw):
                clean = sub.strip()
                if clean and clean not in keys:
                    keys.append(clean)

    return keys


def parse_json_from_llm(content: str) -> Optional[Any]:
    """
    Robust JSON parser for LLM responses.
    Handles Markdown code fences (```json ... ```), raw arrays/objects,
    and trailing comma cleanups.
    """
    if not content or not isinstance(content, str):
        return None

    cleaned = content.strip()

    # 1. Check for markdown code fences ```json ... ``` or ``` ... ```
    if "```" in cleaned:
        code_block_pattern = re.compile(r"```(?:json)?\s*([\s\S]*?)\s*```", re.IGNORECASE)
        matches = code_block_pattern.findall(cleaned)
        for match in matches:
            candidate = match.strip()
            try:
                parsed = json.loads(candidate)
                if parsed is not None:
                    return parsed
            except json.JSONDecodeError:
                # Try fixing trailing commas before closing brackets
                fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
                try:
                    parsed = json.loads(fixed)
                    if parsed is not None:
                        return parsed
                except json.JSONDecodeError:
                    continue

    # 2. Direct JSON load attempt
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Helper function to extract and load container with trailing comma cleanup
    def _extract_container(start_idx: int, end_idx: int) -> Optional[Any]:
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            candidate = cleaned[start_idx:end_idx + 1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                fixed = re.sub(r",\s*([\]}])", r"\1", candidate)
                try:
                    return json.loads(fixed)
                except json.JSONDecodeError:
                    pass
        return None

    # 3. Determine whether '[' or '{' starts first in un-fenced text
    start_arr = cleaned.find("[")
    end_arr = cleaned.rfind("]")
    start_obj = cleaned.find("{")
    end_obj = cleaned.rfind("}")

    if start_obj != -1 and (start_arr == -1 or start_obj < start_arr):
        # Extract object {...} first
        res = _extract_container(start_obj, end_obj)
        if res is not None:
            return res
        # Fallback: try array [...] if object extraction failed
        res = _extract_container(start_arr, end_arr)
        if res is not None:
            return res
    elif start_arr != -1 and (start_obj == -1 or start_arr < start_obj):
        # Extract array [...] first
        res = _extract_container(start_arr, end_arr)
        if res is not None:
            return res
        # Fallback: try object {...} if array extraction failed
        res = _extract_container(start_obj, end_obj)
        if res is not None:
            return res

    return None


def call_gemini_api(
    prompt: str,
    system_prompt: Optional[str] = None,
    api_keys: Optional[List[str]] = None,
    model: str = DEFAULT_GEMINI_MODEL,
    temperature: float = 0.7,
    timeout: int = 25,
    max_recovery_cycles: int = 2
) -> Optional[str]:
    """
    Direct Google AI Studio Gemini API call with key rotation, model failover,
    and automatic Quota Recovery Loop (waiting for Rate Limit cooldown if all keys exhausted).
    """
    keys = parse_gemini_keys(api_keys)
    if not keys:
        logger.warning("No Gemini API keys provided for direct Google AI Studio call.")
        return None

    candidate_models = [model]
    for fb in FALLBACK_GEMINI_MODELS:
        if fb not in candidate_models:
            candidate_models.append(fb)

    for cycle in range(max_recovery_cycles + 1):
        rate_limit_hits = 0
        for key_idx, key in enumerate(keys):
            masked = mask_key(key)
            for cur_model in candidate_models:
                url = f"{GEMINI_ENDPOINT_BASE}/{cur_model}:generateContent?key={key}"
                logger.info(f"Calling Google AI Studio (Model: {cur_model}, Key [{key_idx + 1}/{len(keys)}]: {masked})...")

                payload = {
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": prompt}]
                        }
                    ],
                    "generationConfig": {
                        "temperature": temperature,
                        "responseMimeType": "application/json"
                    }
                }

                if system_prompt:
                    payload["systemInstruction"] = {
                        "parts": [{"text": system_prompt}]
                    }

                headers = {
                    "Content-Type": "application/json"
                }

                try:
                    resp = requests.post(url, headers=headers, json=payload, timeout=(5.0, float(timeout)))
                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            text_parts = [p.get("text", "") for p in parts if not p.get("thought") and p.get("text")]
                            if not text_parts and parts:
                                text_parts = [parts[0].get("text", "")]
                            full_text = "".join(text_parts).strip()
                            if full_text:
                                logger.info(f" Google AI Studio ({cur_model}) returned valid response ({len(full_text)} chars).")
                                return full_text
                    elif resp.status_code == 429:
                        rate_limit_hits += 1
                        logger.warning(f"Google AI Studio Rate Limit (429) for key {masked}. Rotating to next key...")
                        break  # Break model loop and switch to next key
                    elif resp.status_code in (400, 403, 404):
                        logger.warning(f"Google AI Studio error ({resp.status_code}) with model {cur_model} on key {masked}: {resp.text[:200]}")
                        continue
                    else:
                        logger.warning(f"Google AI Studio error HTTP {resp.status_code}: {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"Google AI Studio request exception on key {masked} ({cur_model}): {e}")
                    continue

        # If all keys hit rate limits and we still have recovery cycles
        if rate_limit_hits >= len(keys) and cycle < max_recovery_cycles:
            cooldown_sec = 60
            logger.warning(f"🚨 [QUOTA EXHAUSTED] All {len(keys)} Gemini keys hit Rate Limit (429)! Entering cooldown recovery ({cooldown_sec}s) before cycle {cycle + 2}/{max_recovery_cycles + 1}...")
            time.sleep(cooldown_sec)

    logger.warning("All Google AI Studio Gemini keys/models exhausted after recovery attempts.")
    return None


def call_openai_compatible_api(
    prompt: str,
    system_prompt: str = "",
    base_url: str = DEFAULT_LLM_URL,
    model: str = "gemini-2.5-flash",
    api_key: Optional[str] = None,
    timeout: int = 45
) -> Optional[str]:
    """Call OpenAI-compatible chat completions endpoint as fallback with auto-retry and model cascading."""
    if not base_url or not str(base_url).strip():
        return None
    url = f"{base_url.rstrip('/')}/chat/completions"
    headers = {
        "Content-Type": "application/json"
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    candidate_models = [model]
    for alt in ["gemini-2.5-flash", "gemini-3.6-flash-high"]:
        if alt not in candidate_models:
            candidate_models.append(alt)

    for cur_model in candidate_models:
        payload = {
            "model": cur_model,
            "messages": messages,
            "temperature": 0.7
        }
        for attempt in range(1, 3):
            try:
                resp = requests.post(url, headers=headers, json=payload, timeout=float(timeout))
                if resp.status_code == 200:
                    text_resp = resp.text.strip()
                    if not text_resp:
                        time.sleep(1)
                        continue
                    data = json.loads(text_resp)
                    choices = data.get("choices", [])
                    if choices:
                        content = choices[0].get("message", {}).get("content", "").strip()
                        if content:
                            logger.info(f"OpenAI-compatible API ({cur_model}) returned valid response ({len(content)} chars).")
                            return content
                else:
                    logger.warning(f"OpenAI-compatible API ({cur_model}) HTTP {resp.status_code}: {resp.text[:150]}")
            except Exception as e:
                logger.warning(f"OpenAI-compatible API attempt {attempt} exception ({url}, model: {cur_model}): {e}")
                time.sleep(1.5)

    return None


def build_system_prompt() -> str:
    """
    Strict linguistic and structural system prompt conforming to Gatekeeper 1 standards
    and 5-Word Emotional Curve for vocabCNquiz channel (@lelehoctiengtrung).
    """
    return (
        "Bạn là chuyên gia ngôn ngữ tiếng Trung và biên tập viên trưởng của kênh 'Lê Lê Học Tiếng Trung' (@lelehoctiengtrung).\n"
        "Nhiệm vụ của bạn là tạo các bộ từ vựng luyện tập đoán nghĩa tiếng Trung (vocabCN) trình độ HSK 1, HSK 2 hoặc HSK 3 hấp dẫn, chuẩn xác, gần gũi với đời sống thực tế và tối ưu thuật toán giữ chân (Retention).\n\n"
        "QUY TẮC SẮP XẾP 5 TỪ THEO ĐỒ THỊ CẢM XÚC (RETENTION CURVE):\n"
        "- Từ 1 (CỰC DỄ - HOOK): Từ/cụm từ cực kỳ quen thuộc hàng ngày hoặc phát âm gần gũi (ví dụ: 谢谢, 苹果, 咖啡, 你好, 早上, 喝水) để người xem đoán đúng ngay trong 1 giây đầu.\n"
        "- Từ 2 & 3 (CORE HSK): Các từ vựng cốt lõi theo chủ đề đúng cấp độ HSK.\n"
        "- Từ 4 (BẪY THANH ĐIỆU / BIẾN ÂM ⚡): Chứa bẫy thanh điệu (thanh 1 vs 4, thanh 2 vs 3, phân biệt 买 mǎi / 卖 mài), hoặc biến âm của '不' (bù/bú), '一' (yī/yí/yì), 2 thanh 3 đi liền nhau (ví dụ: 你好, 可以). Kích thích người xem suy nghĩ kỹ, tăng watch-time.\n"
        "- Từ 5 (THỬ THÁCH BOSS 🔥): Khó nhất bộ, chứa âm dễ nhầm lẫn (c/z, x/sh, q/ch, zh/ch, 练习 liànxí vs 联系 liánxì) hoặc với HSK 3 là cụm từ 3-4 chữ viral phim ảnh / thành ngữ thông dụng (ví dụ: 真的吗, 没关系, 不好意思, 一清二白). Kích thích lưu bài hoặc xem lại.\n\n"
        "QUY TẮC BẮT BUỘC (TUÂN THỦ 100% TIÊU CHUẨN GATEKEEPER 1):\n"
        "1. 100% Chữ Giản Thể (Simplified Chinese): Tuyệt đối không dùng chữ Phồn thể.\n"
        "2. Chủ đề tự nhiên, thu hút: Tên chủ đề ngắn gọn (3-7 từ), các từ nối tự nhiên như 'và', '&' hoàn toàn được chấp nhận (ví dụ: 'Cảm xúc và Tâm trạng', 'Thời tiết và Khí hậu', 'Đồ ăn & Thức uống').\n"
        "3. 100% Nghĩa Tiếng Việt thuần túy: Tuyệt đối không chứa từ tiếng Anh (chair, table, dog, cat, car, water, taxi, bus,...).\n"
        "4. Pinyin chuẩn xác & cách nhau bằng dấu cách (Space-separated): Mỗi âm tiết Pinyin phải cách nhau bằng dấu cách (ví dụ: 'shāng diàn', 'dōng xi', 'dǎ zhé', 'zěn me yàng'). Lưu ý các âm mang thanh nhẹ (như 'me' trong 怎么样, 'zi' trong 桌子, 'men' trong 我们, 'ba' trong 爸爸, 'ma' trong 妈妈, 'xi' trong 东西, 'nai' trong 奶奶, 'mei' trong 妹妹) không có dấu thanh điệu. Các từ uốn lưỡi Erhua (儿化 - như 哪儿: nǎr, 这儿: zhèr, 那儿: nàr, 玩儿: wánr, 一点儿: yì diǎnr) viết đuôi 'r' hoặc tách âm đều 100% hợp lệ.\n"
        "5. Phân bổ trình độ HSK đa dạng: Trải đều phong phú giữa HSK 1, HSK 2 và HSK 3, không cố định duy nhất một cấp độ HSK 1.\n"
        "6. Mỗi bộ chủ đề gồm đúng 5 từ vựng, mỗi từ dài từ 1 đến 4 chữ Hán.\n"
        "7. Bắt buộc trả về định dạng JSON thuần túy (Array hoặc Object theo yêu cầu), không thêm bất kỳ lời dẫn hay giải thích nào."
    )


def generate_hsk_topics_with_llm(
    existing_words: Optional[List[str]] = None,
    count: int = 5,
    api_keys: Optional[Union[str, List[str]]] = None,
    model: str = DEFAULT_GEMINI_MODEL,
    existing_topics: Optional[List[str]] = None,
    target_level: Optional[str] = None,
    base_url: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """
    Generate non-repeating HSK vocabulary batches using Direct Google AI Studio Gemini API
    with fallback to OpenAI-compatible endpoint.
    Supports specific target_level (HSK 1, HSK 2, HSK 3) or diverse multi-level distribution.
    """
    system_prompt = build_system_prompt()

    used_words_sample = ", ".join(list(existing_words)[-100:]) if existing_words else "chưa có"
    used_topics_sample = ", ".join(list(existing_topics)[-30:]) if existing_topics else "chưa có"

    if target_level:
        level_instruction = f"CẤP ĐỘ MỤC TIÊU: {target_level}. Hãy tạo các bộ từ vựng đúng chuẩn trình độ {target_level}."
        example_level = target_level
    else:
        level_instruction = "CẤP ĐỘ MỤC TIÊU: ĐA DẠNG HSK 1, HSK 2 VÀ HSK 3. Hãy phân bổ luân phiên, xen kẽ giữa HSK 1, HSK 2 và HSK 3 (Ví dụ: Batch 1: HSK 1, Batch 2: HSK 2, Batch 3: HSK 3... Tuyệt đối KHÔNG cố định một cấp độ)."
        example_level = "HSK 2"

    user_prompt = f"""Hãy tạo đúng {count} bộ chủ đề từ vựng tiếng Trung mới lạ, thiết thực và hấp dẫn cho kênh @lelehoctiengtrung.
{level_instruction}
Mỗi bộ chủ đề phải có đúng 5 từ vựng.

NGỮ CẢNH LOẠI TRỪ (NEGATIVE CONTEXT - TUYỆT ĐỐI KHÔNG TRÙNG LẶP HOẶC TƯƠNG TỰ):
- Các chủ đề đã có gần đây: [{used_topics_sample}]
- Các từ vựng đã xuất hiện gần đây: [{used_words_sample}]

Định dạng JSON yêu cầu (Trả về duy nhất 1 JSON Array):
[
  {{
    "topic": "Đồ Dùng Nhà Bếp",
    "level": "{example_level}",
    "words": [
      {{"hanzi": "筷子", "pinyin": "kuài zi", "meaning": "Đôi đũa"}},
      {{"hanzi": "碗", "pinyin": "wǎn", "meaning": "Cái bát / chén"}},
      {{"hanzi": "盘子", "pinyin": "pán zi", "meaning": "Cái đĩa"}},
      {{"hanzi": "勺子", "pinyin": "sháo zi", "meaning": "Cái thìa / muỗng"}},
      {{"hanzi": "锅", "pinyin": "guō", "meaning": "Cái nồi / chảo"}}
    ]
  }}
]
"""

    # 1. Try Direct Google AI Studio Gemini API
    raw_content = None
    keys = parse_gemini_keys(api_keys)
    if keys:
        raw_content = call_gemini_api(
            prompt=user_prompt,
            system_prompt=system_prompt,
            api_keys=keys,
            model=model,
            temperature=0.7
        )

    # 2. Fallback to OpenAI-compatible endpoint if Gemini failed
    if not raw_content:
        logger.info("Trying fallback to OpenAI-compatible LLM endpoint...")
        raw_content = call_openai_compatible_api(
            prompt=user_prompt,
            system_prompt=system_prompt,
            base_url=base_url or DEFAULT_LLM_URL,
            model="gemini-2.5-flash"
        )

    if not raw_content:
        logger.warning("Failed to obtain raw content from all LLM providers.")
        return None

    parsed = parse_json_from_llm(raw_content)
    if isinstance(parsed, list) and len(parsed) > 0:
        logger.info(f" Successfully generated and parsed {len(parsed)} HSK batches!")
        return parsed
    elif isinstance(parsed, dict) and "topic" in parsed:
        logger.info(" Parsed 1 batch (dict converted to list).")
        return [parsed]

    logger.warning("LLM response could not be parsed into a valid list of topic batches.")
    return None


def generate_single_replacement_topic(
    existing_words: Optional[List[str]] = None,
    row_id: str = "1",
    rejected_topic: str = "",
    error_reasons: Optional[Union[str, List[str]]] = None,
    api_keys: Optional[Union[str, List[str]]] = None,
    target_level: Optional[str] = None,
    model: str = DEFAULT_GEMINI_MODEL
) -> Optional[Dict[str, Any]]:
    """
    Generate exactly 1 replacement HSK batch for a rejected row (Step 2 Targeted Re-Generation).
    Explicitly provides the previous rejected topic and error reasons to avoid repeating mistakes.
    """
    system_prompt = build_system_prompt()

    used_sample = ", ".join(list(existing_words)[-100:]) if existing_words else "chưa có"

    if isinstance(error_reasons, list):
        errors_text = " | ".join(error_reasons)
    else:
        errors_text = str(error_reasons or "Không rõ")

    level_req = f"Trình độ mục tiêu: {target_level}" if target_level else "Trình độ: Đa dạng linh hoạt giữa HSK 1, HSK 2 hoặc HSK 3"

    user_prompt = f"""Dòng #{row_id} trước đó đã bị Cloudflare Gatekeeper TỪ CHỐI do vi phạm các tiêu chuẩn sau:
- Chủ đề bị từ chối: "{rejected_topic or 'Chưa có'}"
- Nguyên nhân vi phạm cụ thể: "{errors_text}"
- {level_req}

YÊU CẦU TÁI SINH DÒNG #{row_id}:
Hãy tạo DUY NHẤT 1 bộ chủ đề từ vựng tiếng Trung (HSK 1, HSK 2 hoặc HSK 3) hoàn toàn MỚI để thay thế dòng #{row_id}.
Tuyệt đối KHẮC PHỤC TRIỆT ĐỂ tất cả các lỗi vi phạm nêu trên:
- Tên chủ đề rõ ràng, hấp dẫn (có thể dùng 'và', '&' như 'Cảm xúc và Tâm trạng').
- Đúng 5 từ vựng, 100% Giản thể, 100% Nghĩa tiếng Việt, Pinyin cách nhau từng âm tiết (ví dụ: 'shāng diàn') và chuẩn thanh điệu.
- Không trùng lặp với các từ vựng đã có: [{used_sample}].

Định dạng JSON yêu cầu (Trả về duy nhất 1 JSON Object):
{{
  "topic": "Đồ Dùng Học Tập",
  "level": "{target_level or 'HSK 2'}",
  "words": [
    {{"hanzi": "书包", "pinyin": "shū bāo", "meaning": "Cặp sách"}},
    {{"hanzi": "铅笔", "pinyin": "qiān bǐ", "meaning": "Bút chì"}},
    {{"hanzi": "本子", "pinyin": "běn zi", "meaning": "Vở / Sổ tay"}},
    {{"hanzi": "尺子", "pinyin": "chǐ zi", "meaning": "Thước kẻ"}},
    {{"hanzi": "橡皮", "pinyin": "xiàng pí", "meaning": "Cục tẩy / gôm"}}
  ]
}}
"""

    raw_content = None
    keys = parse_gemini_keys(api_keys)
    if keys:
        raw_content = call_gemini_api(
            prompt=user_prompt,
            system_prompt=system_prompt,
            api_keys=keys,
            model=model,
            temperature=0.7
        )

    if not raw_content:
        logger.info("Trying fallback to OpenAI-compatible LLM endpoint for single row replacement...")
        raw_content = call_openai_compatible_api(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model="gemini-2.5-flash"
        )

    if not raw_content:
        logger.warning(f"Failed to generate replacement topic for row #{row_id}.")
        return None

    parsed = parse_json_from_llm(raw_content)
    if isinstance(parsed, dict) and "words" in parsed and "topic" in parsed:
        logger.info(f" Successfully generated replacement topic for row #{row_id}: '{parsed.get('topic')}'")
        return parsed
    elif isinstance(parsed, list) and len(parsed) > 0 and isinstance(parsed[0], dict):
        logger.info(f" Successfully generated replacement topic (from array) for row #{row_id}: '{parsed[0].get('topic')}'")
        return parsed[0]

    logger.warning(f"Could not parse valid single topic object for row #{row_id} from output: {raw_content[:200]}")
    return None
