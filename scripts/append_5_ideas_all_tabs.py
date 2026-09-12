#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Appends 5 fresh, linguistically verified ideas for each of the remaining quiz tabs:
- vocabCN (tab: 'vocabCN') -> rows 36, 37, 38, 39, 40
- vocabVN (tab: 'vocabVN') -> rows 32, 33, 34, 35, 36
- multilevels (tab: 'multilevels') -> rows 25, 26, 27, 28, 29

Tab 'pinyin' already has 5 new ideas (52, 53, 54, 55, 56) verified!
All rows are set to 'Pending' and strictly enforced to 21px row height.
"""

import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta

QUIZ_ROOT = str(Path(__file__).resolve().parent.parent)
if QUIZ_ROOT not in sys.path:
    sys.path.insert(0, QUIZ_ROOT)

def get_vietnam_now_str() -> str:
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y-%m-%d %H:%M:%S")

def extract_meta_text(meta_res):
    if isinstance(meta_res, dict) and "sheet_cell_text" in meta_res:
        return meta_res["sheet_cell_text"]
    return str(meta_res)

def run():
    print("🚀 === BẮT ĐẦU THÊM 5 IDEAS CHO CÁC TAB CÒN LẠI TRONG QUIZ ===")
    
    print("\n▶ [1/4] Tab 'pinyin': Đã có đủ 5 ideas (#52 - #56) -> Bỏ qua để tránh trùng lặp.")

    # -------------------------------------------------------------------------
    # TAB 2: VOCABCN (tab: 'vocabCN')
    # -------------------------------------------------------------------------
    print("\n▶ [2/4] Thêm 5 ideas cho Tab 'vocabCN'...")
    sys.path.insert(0, os.path.join(QUIZ_ROOT, "vocabCNquiz"))
    from vocabCNquiz.src.gsheet_manager import GSheetManager as VocabCNGSheetManager
    from vocabCNquiz.src.metadata_generator import save_and_upload_metadata as vocabcn_meta
    
    vocabcn_mgr = VocabCNGSheetManager()
    vocabcn_ideas = [
        {
            "id": 36, "topic": "Động Vật Quanh Ta", "level": "HSK 1",
            "words": [
                ("猫", "māo", "Con mèo"), ("狗", "gǒu", "Con chó"),
                ("鸟", "niǎo", "Con chim"), ("鱼", "yú", "Con cá"),
                ("羊", "yáng", "Con cừu / Con dê")
            ]
        },
        {
            "id": 37, "topic": "Màu Sắc Cuộc Sống", "level": "HSK 2",
            "words": [
                ("红色", "hóng sè", "Màu đỏ"), ("黄色", "huáng sè", "Màu vàng"),
                ("蓝色", "lán sè", "Màu xanh lam"), ("白色", "bái sè", "Màu trắng"),
                ("黑色", "hēi sè", "Màu đen")
            ]
        },
        {
            "id": 38, "topic": "Phương Hướng & Vị Trí", "level": "HSK 2",
            "words": [
                ("前面", "qián mian", "Phía trước"), ("后面", "hòu mian", "Phía sau"),
                ("左边", "zuǒ bian", "Bên trái"), ("右边", "yòu bian", "Bên phải"),
                ("中间", "zhōng jiān", "Ở giữa")
            ]
        },
        {
            "id": 39, "topic": "Văn Phòng Phẩm & Thiết Bị", "level": "HSK 3",
            "words": [
                ("铅笔", "qiān bǐ", "Bút chì"), ("电脑", "diàn nǎo", "Máy vi tính"),
                ("打印机", "dǎ yìn jī", "Máy in"), ("文件", "wén jiàn", "Tài liệu"),
                ("笔记本", "bǐ jì běn", "Sổ tay / Laptop")
            ]
        },
        {
            "id": 40, "topic": "Mua Sắm & Thanh Toán", "level": "HSK 2",
            "words": [
                ("打折", "dǎ zhé", "Giảm giá"), ("刷卡", "shuā kǎ", "Quẹt thẻ"),
                ("现金", "xiàn jīn", "Tiền mặt"), ("找钱", "zhǎo qián", "Trả tiền thừa"),
                ("发票", "fā piào", "Hóa đơn")
            ]
        }
    ]
    
    for item in vocabcn_ideas:
        rid = f"#{item['id']}"
        w_meta = [{"hanzi": w[0], "pinyin": w[1], "meaning": w[2]} for w in item["words"]]
        meta_res = vocabcn_meta(batch_id=str(item["id"]), topic=item["topic"], level=item["level"], words=w_meta)
        meta_txt = extract_meta_text(meta_res)
        w_cols = [f"{w[0]} | {w[1]} | {w[2]}" for w in item["words"]]
        now_str = get_vietnam_now_str()
        row_data = [
            rid, item["topic"], item["level"], "Pending"
        ] + w_cols + [
            meta_txt, "", "", "", "",
            now_str,
            f"Tự động sinh bởi Gemini Flash ({now_str} GMT+7)"
        ]
        vocabcn_mgr.worksheet.append_row(row_data)
        print(f"  ✓ Đã thêm Row {rid} ({item['topic']}) vào tab 'vocabCN'")

    # -------------------------------------------------------------------------
    # TAB 3: VOCABVN (tab: 'vocabVN')
    # -------------------------------------------------------------------------
    print("\n▶ [3/4] Thêm 5 ideas cho Tab 'vocabVN'...")
    sys.path.insert(0, os.path.join(QUIZ_ROOT, "vocabVNquiz"))
    from vocabVNquiz.src.gsheet_manager import GSheetManager as VocabVNGSheetManager
    from vocabVNquiz.src.metadata_generator import save_and_upload_metadata as vocabvn_meta
    
    vocabvn_mgr = VocabVNGSheetManager()
    vocabvn_ideas = [
        {
            "id": 32, "topic": "Gia Vị & Nấu Ăn", "level": "HSK 2",
            "words": [
                ("盐", "yán", "Muối"), ("糖", "táng", "Đường"),
                ("油", "yóu", "Dầu ăn"), ("酱油", "jiàng yóu", "Nước tương / Xì dầu"),
                ("醋", "cù", "Giấm")
            ]
        },
        {
            "id": 33, "topic": "Các Môn Thể Thao", "level": "HSK 2",
            "words": [
                ("踢足球", "tī zú qiú", "Đá bóng"), ("打篮球", "dǎ lán qiú", "Chơi bóng rổ"),
                ("打羽毛球", "dǎ yǔ máo qiú", "Đánh cầu lông"), ("游泳", "yóu yǒng", "Bơi lội"),
                ("跑步", "pǎo bù", "Chạy bộ")
            ]
        },
        {
            "id": 34, "topic": "Thời Tiết Bốn Mùa", "level": "HSK 2",
            "words": [
                ("春天", "chūn tiān", "Mùa xuân"), ("夏天", "xià tiān", "Mùa hè"),
                ("秋天", "qiū tiān", "Mùa thu"), ("冬天", "dōng tiān", "Mùa đông"),
                ("刮风", "guā fēng", "Gió thổi")
            ]
        },
        {
            "id": 35, "topic": "Cảm Xúc & Tính Cách", "level": "HSK 3",
            "words": [
                ("难过", "nán guò", "Buồn bã"), ("着急", "zháo jí", "Nóng vội / Sốt ruột"),
                ("认真", "rèn zhēn", "Nghiêm túc / Chăm chỉ"), ("聪明", "cōng míng", "Thông minh"),
                ("幽默", "yōu mò", "Hài hước")
            ]
        },
        {
            "id": 36, "topic": "Du Lịch & Khám Phá", "level": "HSK 3",
            "words": [
                ("行李箱", "xíng li xiāng", "Va-li hành lý"), ("照相机", "zhào xiàng jī", "Máy ảnh"),
                ("护照", "hù zhào", "Hộ chiếu"), ("宾馆", "bīn guǎn", "Khách sạn"),
                ("风景", "fēng jǐng", "Phong cảnh")
            ]
        }
    ]
    
    for item in vocabvn_ideas:
        rid = f"#{item['id']}"
        w_meta = [{"hanzi": w[0], "pinyin": w[1], "meaning": w[2]} for w in item["words"]]
        meta_res = vocabvn_meta(batch_id=str(item["id"]), topic=item["topic"], level=item["level"], words=w_meta)
        meta_txt = extract_meta_text(meta_res)
        w_cols = [f"{w[0]} | {w[1]} | {w[2]}" for w in item["words"]]
        now_str = get_vietnam_now_str()
        row_data = [
            rid, item["topic"], item["level"], "Pending"
        ] + w_cols + [
            meta_txt, "", "", "", "",
            now_str,
            f"Tự động sinh bởi Gemini Flash ({now_str} GMT+7)"
        ]
        vocabvn_mgr.worksheet.append_row(row_data)
        print(f"  ✓ Đã thêm Row {rid} ({item['topic']}) vào tab 'vocabVN'")

    # -------------------------------------------------------------------------
    # TAB 4: MULTILEVELS (tab: 'multilevels')
    # -------------------------------------------------------------------------
    print("\n▶ [4/4] Thêm 5 ideas cho Tab 'multilevels'...")
    sys.path.insert(0, os.path.join(QUIZ_ROOT, "multilevelsquiz"))
    from multilevelsquiz.src.gsheet_manager import GSheetManager as MLGSheetManager
    from multilevelsquiz.src.metadata_generator import save_and_upload_metadata as ml_meta
    
    ml_mgr = MLGSheetManager()
    ml_ideas = [
        {
            "id": 25, "concept": "Đau đớn / Thương tâm", "hook": "5 Cấp Độ Đau Đớn Trong Tiếng Trung",
            "levels": [
                {"hsk_level": "HSK 1", "hanzi": "疼", "pinyin": "téng", "sino_vietnamese": "Đông", "vietnamese_meaning": "Đau nhức / Đau", "nuance_note": "Đau nhức thể chất thông thường.", "visual_action": "Xoa tay ôm chỗ đau."},
                {"hsk_level": "HSK 2", "hanzi": "痛苦", "pinyin": "tòng kǔ", "sino_vietnamese": "Thống khổ", "vietnamese_meaning": "Đau khổ / Thống khổ", "nuance_note": "Nỗi đau tinh thần hoặc giằng xé.", "visual_action": "Nhắm mắt nhăn mặt đau lòng."},
                {"hsk_level": "HSK 3", "hanzi": "难受", "pinyin": "nán shòu", "sino_vietnamese": "Nan thụ", "vietnamese_meaning": "Khó chịu / Day dứt", "nuance_note": "Khó chịu trong người hoặc tâm trạng không vui.", "visual_action": "Đặt tay lên ngực thở dài."},
                {"hsk_level": "HSK 4", "hanzi": "心痛", "pinyin": "xīn tòng", "sino_vietnamese": "Tâm thống", "vietnamese_meaning": "Đau lòng / Xót xa", "nuance_note": "Nỗi đau quặn thắt vì thương xót ai đó.", "visual_action": "Ôm ngực mắt rơm rớm lệ."},
                {"hsk_level": "HSK 5", "hanzi": "撕心裂肺", "pinyin": "sī xīn liè fèi", "sino_vietnamese": "Tê tâm liệt phế", "vietnamese_meaning": "Xé ruột xé gan / Đau đớn tột cùng", "nuance_note": "Thành ngữ chỉ nỗi đau đớn tột bậc không gì tả xiết.", "visual_action": "Gục đầu ôm mặt đau đớn vô bờ."}
            ]
        },
        {
            "id": 26, "concept": "Ngạc nhiên / Sửng sốt", "hook": "5 Cấp Độ Ngạc Nhiên Trong Tiếng Trung",
            "levels": [
                {"hsk_level": "HSK 1", "hanzi": "奇怪", "pinyin": "qí guài", "sino_vietnamese": "Kỳ quái", "vietnamese_meaning": "Kỳ lạ / Lạ lùng", "nuance_note": "Thấy điều bất thường, lạ mắt.", "visual_action": "Nghiêng đầu thắc mắc."},
                {"hsk_level": "HSK 2", "hanzi": "吃惊", "pinyin": "chī jīng", "sino_vietnamese": "Ngật kinh", "vietnamese_meaning": "Giật mình / Kinh ngạc", "nuance_note": "Bất ngờ trước việc xảy ra đột ngột.", "visual_action": "Mở to mắt che miệng giật mình."},
                {"hsk_level": "HSK 3", "hanzi": "惊讶", "pinyin": "jīng yà", "sino_vietnamese": "Kinh nhạ", "vietnamese_meaning": "Ngạc nhiên / Sửng sốt", "nuance_note": "Thái độ bất ngờ trước tin tức không ngờ tới.", "visual_action": "Mắt tròn xoe sững người."},
                {"hsk_level": "HSK 4", "hanzi": "震撼", "pinyin": "zhèn hàn", "sino_vietnamese": "Chấn hám", "vietnamese_meaning": "Chấn động / Kinh hoàng", "nuance_note": "Tác động mạnh mẽ làm lay động lòng người.", "visual_action": "Lùi bước sững sờ choáng ngợp."},
                {"hsk_level": "HSK 5", "hanzi": "目瞪口呆", "pinyin": "mù dèng kǒu dāi", "sino_vietnamese": "Mục trừng khẩu ngốc", "vietnamese_meaning": "Há hốc mồm kinh ngạc / Đờ đẫn", "nuance_note": "Thành ngữ mắt mở trừng trừng mồm há hốc vì quá kinh ngạc.", "visual_action": "Mắt chữ A miệng chữ O bất động."}
            ]
        },
        {
            "id": 27, "concept": "Cô đơn / Lẻ loi", "hook": "5 Cấp Độ Cô Đơn Trong Tiếng Trung",
            "levels": [
                {"hsk_level": "HSK 1", "hanzi": "一个人", "pinyin": "yí gè rén", "sino_vietnamese": "Nhất cá nhân", "vietnamese_meaning": "Một mình / Đơn độc", "nuance_note": "Chỉ trạng thái ở một mình về mặt số lượng.", "visual_action": "Ngồi một mình lẻ loi."},
                {"hsk_level": "HSK 2", "hanzi": "孤单", "pinyin": "gū dān", "sino_vietnamese": "Cô đơn", "vietnamese_meaning": "Cô đơn / Lẻ bóng", "nuance_note": "Cảm giác không có bạn bè bên cạnh.", "visual_action": "Cúi đầu nhìn bóng mình."},
                {"hsk_level": "HSK 3", "hanzi": "寂寞", "pinyin": "jì mò", "sino_vietnamese": "Tịch mịch", "vietnamese_meaning": "Trống vắng / Cô quạnh", "nuance_note": "Nỗi cô đơn sâu kín trong nội tâm.", "visual_action": "Nhìn ra cửa sổ mưa rơi."},
                {"hsk_level": "HSK 4", "hanzi": "冷清", "pinyin": "lěng qīng", "sino_vietnamese": "Lãnh thanh", "vietnamese_meaning": "Vắng vẻ / Đìu hiu", "nuance_note": "Khung cảnh quạnh quẽ không một bóng người.", "visual_action": "Đứng giữa phố vắng một mình."},
                {"hsk_level": "HSK 5", "hanzi": "形单影只", "pinyin": "xíng dān yǐng zhī", "sino_vietnamese": "Hình đơn ảnh chích", "vietnamese_meaning": "Hình đơn bóng chiếc / Lẻ loi trơ trọi", "nuance_note": "Thành ngữ chỉ người chỉ có cái bóng làm bạn, vô cùng cô đơn.", "visual_action": "Bước đi dưới trăng chỉ có bóng theo cùng."}
            ]
        },
        {
            "id": 28, "concept": "Rộng lượng / Bao dung", "hook": "5 Cấp Độ Bao Dung Trong Tiếng Trung",
            "levels": [
                {"hsk_level": "HSK 1", "hanzi": "大方", "pinyin": "dà fang", "sino_vietnamese": "Đại phương", "vietnamese_meaning": "Hào phóng / Rộng rãi", "nuance_note": "Không keo kiệt tiền bạc hay đồ đạc.", "visual_action": "Vui vẻ xòe tay chia sẻ quà."},
                {"hsk_level": "HSK 2", "hanzi": "热情", "pinyin": "rè qíng", "sino_vietnamese": "Nhiệt tình", "vietnamese_meaning": "Nhiệt tình / Cởi mở", "nuance_note": "Sẵn lòng đối xử tốt và giúp đỡ người khác.", "visual_action": "Mỉm cười thân thiện đón tiếp."},
                {"hsk_level": "HSK 3", "hanzi": "宽容", "pinyin": "kuān róng", "sino_vietnamese": "Khoan dung", "vietnamese_meaning": "Bao dung / Rộng lòng", "nuance_note": "Tha thứ cho lỗi lầm của người khác.", "visual_action": "Gật đầu vỗ vai thứ tha."},
                {"hsk_level": "HSK 4", "hanzi": "豁达", "pinyin": "huò dá", "sino_vietnamese": "Hoát đạt", "vietnamese_meaning": "Khoáng đạt / Cởi mở", "nuance_note": "Tâm hồn phóng khoáng, không chấp nhặt chuyện nhỏ.", "visual_action": "Cười lớn vung tay nhẹ nhõm."},
                {"hsk_level": "HSK 5", "hanzi": "宽宏大量", "pinyin": "kuān hóng dà liàng", "sino_vietnamese": "Khoan hồng đại lượng", "vietnamese_meaning": "Đại lượng bao dung / Bụng dạ mênh mông", "nuance_note": "Thành ngữ chỉ tấm lòng khoan dung như biển lớn đối đãi mọi người.", "visual_action": "Chắp tay cười hiền từ khoan dung."}
            ]
        },
        {
            "id": 29, "concept": "Cẩn thận / Tỉ mỉ", "hook": "5 Cấp Độ Cẩn Thận Trong Tiếng Trung",
            "levels": [
                {"hsk_level": "HSK 1", "hanzi": "小心", "pinyin": "xiǎo xīn", "sino_vietnamese": "Tiểu tâm", "vietnamese_meaning": "Cẩn thận / Coi chừng", "nuance_note": "Chú ý đề phòng nguy hiểm hàng ngày.", "visual_action": "Đưa tay che chắn cẩn thận."},
                {"hsk_level": "HSK 2", "hanzi": "认真", "pinyin": "rèn zhēn", "sino_vietnamese": "Nhận chân", "vietnamese_meaning": "Nghiêm túc / Chăm chú", "nuance_note": "Làm việc có trách nhiệm, chu đáo.", "visual_action": "Chăm chú nhìn tài liệu ghi chép."},
                {"hsk_level": "HSK 3", "hanzi": "细心", "pinyin": "xì xīn", "sino_vietnamese": "Tế tâm", "vietnamese_meaning": "Tỉ mỉ / Chu đáo", "nuance_note": "Chú ý đến từng chi tiết nhỏ nhất.", "visual_action": "Dùng kính lúp soi xét từng ly."},
                {"hsk_level": "HSK 4", "hanzi": "谨慎", "pinyin": "jǐn shèn", "sino_vietnamese": "Cẩn thận", "vietnamese_meaning": "Thận trọng / Dè dặt", "nuance_note": "Hành sự kín kẽ, tránh rủi ro sơ suất.", "visual_action": "Bước đi chậm rãi nhìn trước ngó sau."},
                {"hsk_level": "HSK 5", "hanzi": "一丝不苟", "pinyin": "yī sī bù gǒu", "sino_vietnamese": "Nhất ti bất cẩu", "vietnamese_meaning": "Kỹ lưỡng từng li từng tí / Không hề cẩu thả", "nuance_note": "Thành ngữ làm việc chuẩn xác tuyệt đối đến từng sợi tơ sợi tóc.", "visual_action": "Căn chỉnh từng milimet chính xác tuyệt đối."}
            ]
        }
    ]
    
    for item in ml_ideas:
        rid = f"#{item['id']}"
        topic_title = f"1 Nghĩa 5 Cấp • {item['concept']}"
        meta_res = ml_meta(
            batch_id=str(item["id"]),
            concept_name_vi=item["concept"],
            levels=item["levels"],
            hook_title=item["hook"],
            cta_text="Comment mốc điểm bạn vượt qua nhé!"
        )
        meta_txt = extract_meta_text(meta_res)
        w_cols = [f"{lvl['hanzi']} | {lvl['pinyin']} | {lvl['sino_vietnamese']} | {lvl['vietnamese_meaning']} | {lvl['nuance_note']} | {lvl['visual_action']}" for lvl in item["levels"]]
        now_str = get_vietnam_now_str()
        row_data = [
            rid, topic_title, "HSK 1-5", "Pending"
        ] + w_cols + [
            meta_txt, "", "", "", "",
            now_str,
            f"Tự động sinh bởi Gemini Flash ({now_str} GMT+7)"
        ]
        ml_mgr.worksheet.append_row(row_data)
        print(f"  ✓ Đã thêm Row {rid} ({topic_title}) vào tab 'multilevels'")

    # -------------------------------------------------------------------------
    # ENFORCE STRICT 21PX ROW HEIGHT INVARIANT
    # -------------------------------------------------------------------------
    print("\n📏 [Khóa cứng 21px] Thực thi RowHeightEnforcer trên toàn bộ 4 tabs...")
    from scripts.enforce_row_height_21px import RowHeightEnforcer
    enforcer = RowHeightEnforcer()
    enforcer.enforce_all()
    print("🎉 TẤT CẢ 4 TABS ĐÃ ĐƯỢC THÊM 5 IDEAS & KHÓA ĐỘ CAO 21PX THÀNH CÔNG!")

if __name__ == "__main__":
    run()
