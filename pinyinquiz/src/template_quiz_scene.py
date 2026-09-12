from manim import *
import os
from src.config import config

# TikTok 9:16 Vertical Video (1080x1920)
config.pixel_width = 1080
config.pixel_height = 1920
config.frame_width = 9.0
config.frame_height = 16.0

VIETNAMESE_FONT = "Arial"
PINYIN_FONT = "Arial"
CHINESE_FONT = "Noto Sans SC"

class ModernPinyinQuizScene(Scene):
    def __init__(self, batch_data=None, **kwargs):
        super().__init__(**kwargs)
        self.batch_data = batch_data or {
            "id": "sample_modern",
            "topic": "HSK 1-2 • Từ Vựng Cơ Bản",
            "level": "HSK 1-2",
            "words": [
                {
                    "hanzi": "苹果",
                    "pinyin": "píng guǒ",
                    "hidden_pinyin": "p _ _ _   _ _ _",
                    "meaning": "Quả táo",
                    "pos": "(danh từ)",
                    "example_hz": "我想买两斤红苹果。",
                    "example_py": "Wǒ xiǎng mǎi liǎng jīn hóng píngguǒ.",
                    "example_vi": "Tôi muốn mua một cân táo đỏ."
                },
                {
                    "hanzi": "老师",
                    "pinyin": "lǎo shī",
                    "hidden_pinyin": "l _ _   _ _ _",
                    "meaning": "Giáo viên / Thầy cô",
                    "pos": "(danh từ)",
                    "example_hz": "李老师是一位好老师。",
                    "example_py": "Lǐ lǎoshī shì yí wèi hǎo lǎoshī.",
                    "example_vi": "Thầy Lý là một giáo viên giỏi."
                },
                {
                    "hanzi": "喜欢",
                    "pinyin": "xǐ huan",
                    "hidden_pinyin": "x _   _ _ _ _",
                    "meaning": "Thích / Yêu thích",
                    "pos": "(động từ)",
                    "example_hz": "我很喜欢学汉语。",
                    "example_py": "Wǒ hěn xǐhuan xué Hànyǔ.",
                    "example_vi": "Tôi rất thích học tiếng Trung."
                },
                {
                    "hanzi": "学校",
                    "pinyin": "xué xiào",
                    "hidden_pinyin": "x _ _   _ _ _ _",
                    "meaning": "Trường học",
                    "pos": "(danh từ)",
                    "example_hz": "我们的学校很大也很漂亮。",
                    "example_py": "Wǒmen de xuéxiào hěn dà yě hěn piàoliang.",
                    "example_vi": "Trường chúng tôi rất to và đẹp."
                },
                {
                    "hanzi": "朋友",
                    "pinyin": "péng you",
                    "hidden_pinyin": "p _ _ _   _ _ _",
                    "meaning": "Bạn bè",
                    "pos": "(danh từ)",
                    "example_hz": "他们都是我的好朋友。",
                    "example_py": "Tāmen dōu shì wǒ de hǎo péngyou.",
                    "example_vi": "Họ đều là những người bạn tốt của tôi."
                }
            ]
        }

    def construct(self):
        words = self.batch_data.get("words", [])
        total_words = len(words)
        topic_title = self.batch_data.get("topic", "HSK 1-2 • Từ Vựng")

        # 1. Background Image
        bg_path = os.path.join(config.base_dir, "assets/images/background.jpg")
        if os.path.exists(bg_path):
            bg_image = ImageMobject(bg_path)
            bg_image.set_height(config.frame_height)
            bg_image.set_width(config.frame_width)
            self.add(bg_image)
            
        dark_overlay = Rectangle(
            width=config.frame_width,
            height=config.frame_height,
            fill_color="#030712",
            fill_opacity=0.42,
            stroke_width=0
        )
        self.add(dark_overlay)

        # 2. Top Header Pill
        pill_text = Text(
            topic_title.upper(),
            font=VIETNAMESE_FONT,
            font_size=24,
            color="#082f49",
            weight=BOLD
        )
        pill_bg = RoundedRectangle(
            corner_radius=0.35,
            width=max(pill_text.width + 0.8, 3.4),
            height=0.68,
            fill_color="#38bdf8",
            fill_opacity=0.98,
            stroke_color="#7dd3fc",
            stroke_width=1.5
        ).move_to(UP * 6.7)
        pill_text.move_to(pill_bg.get_center())
        
        header_pill = VGroup(pill_bg, pill_text)

        # 3. Top Mode Box (THỬ ĐOÁN XEM! 🇻🇳 -> 🇨🇳)
        mode_card = RoundedRectangle(
            corner_radius=0.25,
            width=3.6,
            height=1.3,
            fill_color="#0b0f19",
            fill_opacity=0.88,
            stroke_color="#1e293b",
            stroke_width=1.5
        ).next_to(pill_bg, DOWN, buff=0.22)
        
        mode_title = Text(
            "THỬ ĐOÁN XEM!",
            font=VIETNAMESE_FONT,
            font_size=25,
            color="#fbbf24",
            weight=BOLD
        ).move_to(mode_card.get_top() + DOWN * 0.38)
        
        mode_sub = Text(
            "🇻🇳 ➔ 🇨🇳 (Pinyin)",
            font=VIETNAMESE_FONT,
            font_size=23,
            color=WHITE,
            weight=SEMIBOLD
        ).move_to(mode_card.get_bottom() + UP * 0.38)
        
        header_mode = VGroup(mode_card, mode_title, mode_sub)
        
        self.play(FadeIn(header_pill, shift=DOWN*0.3), FadeIn(header_mode, shift=DOWN*0.3), run_time=0.6)

        # 4. Bottom Footer Floating Card
        footer_card = RoundedRectangle(
            corner_radius=0.3,
            width=7.4,
            height=1.25,
            fill_color="#090d16",
            fill_opacity=0.88,
            stroke_color="#1e293b",
            stroke_width=1.5
        ).move_to(DOWN * 6.3)

        # Mascot Avatar
        avatar_path = os.path.join(config.base_dir, "assets/images/logo.png")
        if os.path.exists(avatar_path):
            avatar_img = ImageMobject(avatar_path).set_height(0.85)
            avatar_bg = RoundedRectangle(corner_radius=0.2, width=0.9, height=0.9, fill_color="#0284c7", fill_opacity=0.3, stroke_width=0)
            avatar_group = Group(avatar_bg, avatar_img).move_to(footer_card.get_left() + RIGHT * 0.75)
        else:
            avatar_group = Dot(radius=0.4, color=BLUE_D).move_to(footer_card.get_left() + RIGHT * 0.75)

        footer_title = Text("Học Tiếng Trung FREE", font=VIETNAMESE_FONT, font_size=26, color=WHITE, weight=BOLD)
        footer_sub = Text("cùng Lê Lệ Học Tiếng Trung", font=VIETNAMESE_FONT, font_size=22, color="#94a3b8")
        footer_text_group = VGroup(footer_title, footer_sub).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        footer_text_group.next_to(avatar_group, RIGHT, buff=0.3)

        footer_base = Group(footer_card, avatar_group, footer_text_group)
        self.play(FadeIn(footer_base, shift=UP*0.3), run_time=0.5)

        # 5. Words Loop
        for idx, w in enumerate(words, start=1):
            hanzi = w.get("hanzi", "")
            pinyin_full = w.get("pinyin", "")
            hidden_py = w.get("hidden_pinyin", "p _ _ _   _ _ _")
            meaning = w.get("meaning", "")
            pos = w.get("pos", "(từ vựng)")
            ex_hz = w.get("example_hz", "")
            ex_py = w.get("example_py", "")
            ex_vi = w.get("example_vi", "")

            # Word counter
            counter_text = Text(f"Từ {idx}/{total_words}", font=VIETNAMESE_FONT, font_size=26, color="#94a3b8", weight=SEMIBOLD)
            counter_text.move_to(footer_card.get_right() + LEFT * 0.9)
            self.play(FadeIn(counter_text, run_time=0.2))

            # Main Question Card
            center_card = RoundedRectangle(
                corner_radius=0.45,
                width=7.4,
                height=6.6,
                fill_color="#090d16",
                fill_opacity=0.88,
                stroke_color="#1e293b",
                stroke_width=1.5
            ).move_to(UP * 0.3)

            # Meaning Title
            meaning_text = Text(
                meaning,
                font=VIETNAMESE_FONT,
                font_size=50,
                color=WHITE,
                weight=BOLD
            ).move_to(center_card.get_top() + DOWN * 1.1)
            if meaning_text.width > 6.4:
                meaning_text.scale_to_fit_width(6.4)
            
            # Part of speech
            pos_text = Text(
                pos,
                font=VIETNAMESE_FONT,
                font_size=28,
                color="#94a3b8"
            ).next_to(meaning_text, DOWN, buff=0.25)
            if pos_text.width > 6.4:
                pos_text.scale_to_fit_width(6.4)

            # Hidden Pinyin
            hidden_text = Text(
                hidden_py,
                font=VIETNAMESE_FONT,
                font_size=58,
                color="#facc15",
                weight=BOLD
            ).next_to(pos_text, DOWN, buff=0.55)
            if hidden_text.width > 6.4:
                hidden_text.scale_to_fit_width(6.4)

            # Time Countdown
            time_label = Text("TIME", font=VIETNAMESE_FONT, font_size=30, color="#94a3b8", weight=BOLD)
            timer_num = Text("4", font=VIETNAMESE_FONT, font_size=54, color=WHITE, weight=BOLD)
            timer_group = VGroup(time_label, timer_num).arrange(RIGHT, buff=0.25).next_to(hidden_text, DOWN, buff=0.6)

            # Progress Bar
            bar_width = 5.4
            bar_track = RoundedRectangle(
                corner_radius=0.08,
                width=bar_width,
                height=0.16,
                fill_color="#1e293b",
                fill_opacity=0.8,
                stroke_width=0
            ).next_to(timer_group, DOWN, buff=0.35)

            active_bar = RoundedRectangle(
                corner_radius=0.08,
                width=bar_width,
                height=0.16,
                fill_color="#38bdf8",
                fill_opacity=1.0,
                stroke_width=0
            ).move_to(bar_track.get_center())

            quiz_mobjects = VGroup(center_card, meaning_text, pos_text, hidden_text, timer_group, bar_track, active_bar)
            self.play(FadeIn(quiz_mobjects, shift=UP*0.2), run_time=0.4)

            # Smooth Countdown 4..3..2..1
            total_seconds = 4
            for s in range(total_seconds - 1, 0, -1):
                fraction_left = s / total_seconds
                new_bar_width = max(bar_width * fraction_left, 0.01)
                
                # Active bar shrinking to left
                new_active_bar = RoundedRectangle(
                    corner_radius=0.08,
                    width=new_bar_width,
                    height=0.16,
                    fill_color="#38bdf8" if s > 1 else "#f43f5e",
                    fill_opacity=1.0,
                    stroke_width=0
                )
                new_active_bar.align_to(bar_track, LEFT)
                
                new_timer_num = Text(str(s), font=VIETNAMESE_FONT, font_size=54, color=WHITE if s > 1 else "#f43f5e", weight=BOLD)
                new_timer_num.move_to(timer_num.get_center())

                self.play(
                    Transform(active_bar, new_active_bar),
                    Transform(timer_num, new_timer_num),
                    run_time=0.9,
                    rate_func=linear
                )

            # Bell sound at 0s
            bell_file = os.path.join(config.base_dir, "assets/audio/ding.mp3")
            if not os.path.exists(bell_file):
                bell_file = config.bell_audio_path
            if os.path.exists(bell_file):
                try:
                    self.add_sound(bell_file)
                except Exception:
                    pass

            # FADE OUT TIMER
            self.play(FadeOut(timer_group), FadeOut(bar_track), FadeOut(active_bar), run_time=0.15)

            # REVEAL ANSWER
            answer_main = Text(
                f"{hanzi}  {pinyin_full}",
                font=CHINESE_FONT,
                font_size=60,
                color="#38bdf8",
                weight=BOLD
            ).move_to(hidden_text.get_center())
            if answer_main.width > 6.4:
                answer_main.scale_to_fit_width(6.4)

            pinyin_sub = Text(
                f"/{pinyin_full}/",
                font=VIETNAMESE_FONT,
                font_size=30,
                color="#94a3b8",
                slant=ITALIC
            ).next_to(answer_main, DOWN, buff=0.3)
            if pinyin_sub.width > 6.4:
                pinyin_sub.scale_to_fit_width(6.4)

            example_group = VGroup()
            if ex_hz:
                ex_hz_txt = Text(ex_hz, font=CHINESE_FONT, font_size=30, color=WHITE, weight=MEDIUM)
                ex_py_txt = Text(ex_py, font=VIETNAMESE_FONT, font_size=23, color="#cbd5e1")
                ex_vi_txt = Text(f"({ex_vi})", font=VIETNAMESE_FONT, font_size=23, color="#94a3b8")
                example_group = VGroup(ex_hz_txt, ex_py_txt, ex_vi_txt).arrange(DOWN, buff=0.12)
                if example_group.width > 6.4:
                    example_group.scale_to_fit_width(6.4)
                example_group.next_to(pinyin_sub, DOWN, buff=0.4)

            self.play(
                Transform(hidden_text, answer_main),
                FadeIn(pinyin_sub, shift=UP*0.1),
                FadeIn(example_group, shift=UP*0.1),
                run_time=0.45
            )

            # Sau tiếng chuông kết thúc 0.5 giây
            self.wait(0.75)

            # Clear card
            self.play(
                FadeOut(center_card),
                FadeOut(meaning_text),
                FadeOut(pos_text),
                FadeOut(hidden_text),
                FadeOut(pinyin_sub),
                FadeOut(example_group),
                FadeOut(counter_text),
                run_time=0.35
            )

        # End CTA
        end_card = RoundedRectangle(
            corner_radius=0.45,
            width=7.6,
            height=5.8,
            fill_color="#090d16",
            fill_opacity=0.92,
            stroke_color="#38bdf8",
            stroke_width=2.0
        ).move_to(UP * 0.3)

        logo_path = os.path.join(config.base_dir, "assets/images/logo.png")
        if os.path.exists(logo_path):
            logo_img = ImageMobject(logo_path).set_height(1.3)
            logo_bg = RoundedRectangle(
                corner_radius=0.3,
                width=1.45,
                height=1.45,
                fill_color="#0b1120",
                fill_opacity=1.0,
                stroke_color="#38bdf8",
                stroke_width=2.0
            )
            logo_badge = Group(logo_bg, logo_img)
        else:
            logo_badge = Dot(radius=0.6, color="#0284c7")

        end_title = Text("BẠN ĐOÁN ĐÚNG MẤY CÂU?", font=VIETNAMESE_FONT, font_size=34, color="#fbbf24", weight=BOLD)
        end_sub1 = Text("Comment số điểm của bạn bên dưới nha! 👇", font=VIETNAMESE_FONT, font_size=25, color=WHITE)
        end_sub2 = Text("Follow Lê Lệ Học Tiếng Trung", font=VIETNAMESE_FONT, font_size=25, color="#38bdf8", weight=BOLD)
        end_sub3 = Text("để luyện tập mỗi ngày! ✨", font=VIETNAMESE_FONT, font_size=24, color="#cbd5e1")
        
        end_text_group = VGroup(end_title, end_sub1, end_sub2, end_sub3).arrange(DOWN, buff=0.25)
        if end_text_group.width > 6.8:
            end_text_group.scale_to_fit_width(6.8)
            
        end_content = Group(logo_badge, end_text_group).arrange(DOWN, buff=0.35)
        end_content.move_to(end_card.get_center())
        
        self.play(FadeIn(end_card), FadeIn(end_content), run_time=0.5)
        self.wait(2.5)
        self.play(FadeOut(end_card), FadeOut(end_content), FadeOut(header_pill), FadeOut(header_mode), FadeOut(footer_base), run_time=0.5)
