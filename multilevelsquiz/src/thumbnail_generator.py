import os
import sys
import re
import logging
from typing import Dict, Any, Optional, List
from PIL import Image, ImageDraw, ImageFont, ImageFilter

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from multilevelsquiz.src.config import config
except ImportError:
    from src.config import config

logger = logging.getLogger("ThumbnailGenerator")

FONT_CANDIDATES = [
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "Arial_Bold.ttf"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "Arial.ttf"),
    os.path.expanduser("~/.fonts/Arial_Bold.ttf"),
    os.path.expanduser("~/.fonts/Arial.ttf"),
    "/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
    "/usr/share/fonts/truetype/litefonts/ARIALUNI.TTF",
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "NotoSansSC-Bold.otf"),
    os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "fonts", "NotoSansSC.ttf"),
]

def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    for font_path in FONT_CANDIDATES:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size=size)
            except Exception:
                continue
    return ImageFont.load_default()

def draw_rounded_rect(draw: ImageDraw.ImageDraw, coords, radius: int, fill, outline=None, width: int = 1):
    draw.rounded_rectangle(coords, radius=radius, fill=fill, outline=outline, width=width)

def draw_text_with_shadow(
    draw: ImageDraw.ImageDraw,
    xy,
    text: str,
    font: ImageFont.FreeTypeFont,
    fill: str = "#ffffff",
    shadow_color: str = "#000000",
    shadow_offset: tuple = (4, 4),
    anchor: str = "mm"
):
    x, y = xy
    sx, sy = shadow_offset
    draw.text((x + sx, y + sy), text, font=font, fill=shadow_color, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill, anchor=anchor)

def clean_topic_title(raw_topic: str) -> str:
    t = raw_topic.strip()
    if "•" in t:
        parts = t.split("•", 1)
        t = parts[1].strip()
    elif "-" in t:
        parts = t.split("-", 1)
        t = parts[1].strip()
    return t.upper()

def wrap_text(text: str, max_chars_per_line: int = 12) -> list:
    words = text.split()
    lines = []
    curr = []
    curr_len = 0
    for w in words:
        if curr_len + len(w) + (1 if curr else 0) <= max_chars_per_line:
            curr.append(w)
            curr_len += len(w) + (1 if len(curr) > 1 else 0)
        else:
            if curr:
                lines.append(" ".join(curr))
            curr = [w]
            curr_len = len(w)
    if curr:
        lines.append(" ".join(curr))
    return lines if lines else [text]

def parse_topic_elements(raw_topic: str) -> List[Dict[str, str]]:
    clean_t = clean_topic_title(raw_topic)
    parts = re.split(r'\s+(&|VÀ|\/|\+)\s+', clean_t, flags=re.IGNORECASE)
    if len(parts) >= 3:
        items = []
        for p in parts:
            p_str = p.strip().upper()
            if not p_str:
                continue
            if p_str in ["&", "VÀ", "/", "+"]:
                items.append({"text": p_str, "type": "connector"})
            else:
                wrapped = wrap_text(p_str, max_chars_per_line=12)
                for w_line in wrapped:
                    items.append({"text": w_line, "type": "main"})
        return items

    wrapped = wrap_text(clean_t, max_chars_per_line=12)
    return [{"text": line, "type": "main"} for line in wrapped]

def generate_multilevels_thumbnail(
    batch_id: Any,
    concept_name: str,
    levels: Optional[List[Dict[str, Any]]] = None,
    output_path: Optional[str] = None
) -> str:
    """
    Generate High-CTR 1080x1920 9:16 Vertical Cover Thumbnail for Multilevels Quiz (1 Nghĩa - 5 Cấp độ HSK):
    - Color Scheme: Royal Cyber Violet / Slate Navy (#7C3AED, #9333EA, #1E1B4B) with Radiant Gold (#F59E0B)
    - 3-Zone Clean Layout:
      1. TOP: Level Badge Pill ("1 NGHĨA - 5 CẤP ĐỘ")
      2. MIDDLE: NGHĨA ĐỂ TRONG KHUNG LỚN (Chỉ để nghĩa chính TỨC GIẬN / NỔI CÁU, bỏ 'Ý niệm cốt lõi', bỏ các HSK chips)
      3. BOTTOM: "BẠN ĐANG Ở HSK NÀO?" CTA Badge
    """
    clean_id = str(batch_id).replace("#", "").strip()
    clean_concept = clean_topic_title(concept_name)

    if not output_path:
        os.makedirs(config.output_thumbnails_dir, exist_ok=True)
        output_path = os.path.join(config.output_thumbnails_dir, f"thumb_batch_{clean_id}.jpg")

    width = 1080
    height = 1920

    # Base Background Image (Lighter, vibrant studio gradient)
    bg_img_path = os.path.join(config.base_dir, "assets", "images", "background.jpg")
    if os.path.exists(bg_img_path):
        try:
            base_bg = Image.open(bg_img_path).convert("RGBA")
            base_bg = base_bg.resize((width, height), Image.Resampling.LANCZOS)
        except Exception:
            base_bg = Image.new("RGBA", (width, height), "#0d1326")
    else:
        base_bg = Image.new("RGBA", (width, height), "#0d1326")

    # Soft ambient overlay
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    for y in range(height):
        dist = abs(y - 960) / 960.0
        alpha = int(70 + 75 * (dist ** 1.3))
        overlay_draw.line([(0, y), (width, y)], fill=(13, 19, 38, min(alpha, 180)))

    img = Image.alpha_composite(base_bg, overlay)
    draw = ImageDraw.Draw(img)

    # -------------------------------------------------------------------------
    # 1. TOP ZONE: Level Badge Pill ("1 NGHĨA - 5 CẤP ĐỘ")
    # -------------------------------------------------------------------------
    top_badge_y = 360
    font_level = get_font(52, bold=True)
    level_text = "1 NGHĨA - 5 CẤP ĐỘ"

    bbox = draw.textbbox((width // 2, top_badge_y), level_text, font=font_level, anchor="mm")
    pad_x, pad_y = 55, 20
    bx1, by1, bx2, by2 = bbox[0] - pad_x, bbox[1] - pad_y, bbox[2] + pad_x, bbox[3] + pad_y

    # Glowing outer border
    draw_rounded_rect(
        draw,
        (bx1 - 4, by1 - 4, bx2 + 4, by2 + 4),
        radius=50,
        fill=None,
        outline="#fbbf24",
        width=2
    )
    # Badge Pill (Amber / Gold fill)
    draw_rounded_rect(
        draw,
        (bx1, by1, bx2, by2),
        radius=46,
        fill=(245, 158, 11, 255),
        outline="#fde68a",
        width=3
    )
    draw_text_with_shadow(
        draw,
        (width // 2, top_badge_y),
        level_text,
        font=font_level,
        fill="#0f172a",
        shadow_color="#d97706",
        shadow_offset=(3, 3),
        anchor="mm"
    )

    # -------------------------------------------------------------------------
    # 2. MIDDLE ZONE: NGHĨA ĐỂ TRONG KHUNG LỚN (Chỉ hiển thị nghĩa chính, sạch sẽ)
    # -------------------------------------------------------------------------
    topic_items = parse_topic_elements(clean_concept)
    total_lines = len(topic_items)

    font_size_main = 106 if total_lines <= 2 else (92 if total_lines == 3 else 78)
    font_size_connector = 60
    line_spacing = 145 if total_lines <= 2 else (125 if total_lines == 3 else 102)

    card_h = max(480, total_lines * line_spacing + 160)
    card_w = 980
    card_x1 = (width - card_w) // 2
    card_y1 = 940 - (card_h // 2)
    card_x2 = card_x1 + card_w
    card_y2 = card_y1 + card_h

    # Card outer glow
    draw_rounded_rect(
        draw,
        (card_x1 - 6, card_y1 - 6, card_x2 + 6, card_y2 + 6),
        radius=56,
        fill=None,
        outline="#7c3aed",
        width=3
    )
    # Main Central Card (Deep Royal Slate Navy)
    draw_rounded_rect(
        draw,
        (card_x1, card_y1, card_x2, card_y2),
        radius=50,
        fill=(15, 23, 42, 250),
        outline="#a78bfa",
        width=4
    )

    # Draw Concept text inside the Large Card (Centered, bold and crystal-clear)
    start_y = (card_y1 + card_y2) // 2 - ((total_lines - 1) * line_spacing) // 2
    for i, item in enumerate(topic_items):
        curr_y = start_y + (i * line_spacing)
        if item["type"] == "connector":
            font_conn = get_font(font_size_connector, bold=True)
            draw_text_with_shadow(
                draw,
                (width // 2, curr_y),
                item["text"],
                font=font_conn,
                fill="#fbbf24",
                shadow_color="#000000",
                shadow_offset=(2, 2),
                anchor="mm"
            )
        else:
            font_main = get_font(font_size_main, bold=True)
            draw_text_with_shadow(
                draw,
                (width // 2, curr_y),
                item["text"],
                font=font_main,
                fill="#ffffff",
                shadow_color="#1e1b4b",
                shadow_offset=(4, 4),
                anchor="mm"
            )

    # -------------------------------------------------------------------------
    # 3. BOTTOM ZONE: 'BẠN ĐANG Ở HSK NÀO?' CTA Badge
    # -------------------------------------------------------------------------
    bottom_badge_y = 1530
    font_bottom = get_font(48, bold=True)
    bottom_text = "BẠN ĐANG Ở HSK NÀO?"

    bb = draw.textbbox((width // 2, bottom_badge_y), bottom_text, font=font_bottom, anchor="mm")
    bbx1, bby1, bbx2, bby2 = bb[0] - 42, bb[1] - 22, bb[2] + 42, bb[3] + 22

    draw_rounded_rect(
        draw,
        (bbx1 - 5, bby1 - 5, bbx2 + 5, bby2 + 5),
        radius=65,
        fill=None,
        outline="#f59e0b",
        width=3
    )
    draw_rounded_rect(
        draw,
        (bbx1, bby1, bbx2, bby2),
        radius=60,
        fill=(124, 58, 237, 250),  # Royal Violet 600
        outline="#c4b5fd",
        width=3
    )
    draw_text_with_shadow(
        draw,
        (width // 2, bottom_badge_y),
        bottom_text,
        font=font_bottom,
        fill="#fde047",  # Vivid Yellow
        shadow_color="#3b0764",
        shadow_offset=(3, 3),
        anchor="mm"
    )

    # Save as RGB JPEG
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    final_img = img.convert("RGB")
    final_img.save(output_path, "JPEG", quality=95)
    logger.info(f"Generated Clean High-CTR Multilevels Cover: {output_path}")
    return output_path

def create_high_ctr_thumbnail(batch_data: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """Wrapper function matching channel convention."""
    b_id = batch_data.get("id", batch_data.get("row_id", "0"))
    topic = batch_data.get("concept_name_vi", batch_data.get("topic", "1 NGHĨA - 5 CẤP ĐỘ"))
    levels = batch_data.get("levels", [])
    return generate_multilevels_thumbnail(b_id, topic, levels, output_path=output_path)
