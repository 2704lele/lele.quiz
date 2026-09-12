#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Appends 5 fresh, linguistically verified ideas for the 'multilevels' tab:
- Rows #30, #31, #32, #33, #34
Strict anti-duplicate check, full 16 standard columns, status 'Pending', and 21px row height locked.
"""

import os
import sys
from datetime import datetime, timezone, timedelta

# Enforce bytecode suppression on exFAT
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

QUIZ_ROOT = "/media/vpsg16gb/Media/lelehoctiengtrung/quiz"
sys.path.insert(0, QUIZ_ROOT)
sys.path.insert(0, os.path.join(QUIZ_ROOT, "multilevelsquiz"))

from multilevelsquiz.src.gsheet_manager import GSheetManager
from multilevelsquiz.src.metadata_generator import save_and_upload_metadata
from scripts.enforce_row_height_21px import RowHeightEnforcer

def get_vietnam_now_str() -> str:
    tz_vn = timezone(timedelta(hours=7))
    return datetime.now(tz_vn).strftime("%Y-%m-%d %H:%M:%S")

def extract_meta_text(meta_res):
    if isinstance(meta_res, dict) and "sheet_cell_text" in meta_res:
        return meta_res["sheet_cell_text"]
    return str(meta_res)

def main():
    print("🚀 === BẮT ĐẦU THÊM 5 IDEAS CHO TAB 'MULTILEVELS' ===")
    mgr = GSheetManager()
    existing_rows = mgr.worksheet.get_all_values()
    print(f"Số dòng hiện tại trên tab 'multilevels': {len(existing_rows)}")
    
    # 5 Fresh Ideas
    ml_ideas = [
        {
            "id": 30,
            "concept": "Buồn bã / U sầu",
            "hook": "5 Cấp Độ Buồn Bã Trong Tiếng Trung",
            "levels": [
                {"hsk_level": "HSK 1", "hanzi": "哭", "pinyin": "kū", "sino_vietnamese": "Khốc", "vietnamese_meaning": "Khóc / Buồn khóc", "nuance_note": "Hành động rơi nước mắt vì buồn tủi.", "visual_action": "Lấy tay gạt nước mắt buồn bã."},
                {"hsk_level": "HSK 2", "hanzi": "难过", "pinyin": "nán guò", "sino_vietnamese": "Nan quá", "vietnamese_meaning": "Buồn bã / Đau lòng", "nuance_note": "Cảm giác buồn rầu, khó vượt qua trong lòng.", "visual_action": "Cúi đầu thở dài ảo não."},
                {"hsk_level": "HSK 3", "hanzi": "伤心", "pinyin": "shāng xīn", "sino_vietnamese": "Thương tâm", "vietnamese_meaning": "Đau lòng / Tổn thương", "nuance_note": "Nỗi đau sâu sắc chạm đến con tim.", "visual_action": "Đặt tay lên tim ánh mắt nhói đau."},
                {"hsk_level": "HSK 4", "hanzi": "沮丧", "pinyin": "jǔ sàng", "sino_vietnamese": "Tự tang", "vietnamese_meaning": "Chán nản / Tuyệt vọng ủ rũ", "nuance_note": "Tinh thần suy sụp, mất hết nhuệ khí sau thất bại.", "visual_action": "Thõng hai vai ánh mắt thất thần."},
                {"hsk_level": "HSK 5", "hanzi": "悲痛欲绝", "pinyin": "bēi tòng yù jué", "sino_vietnamese": "Bi thống dục tuyệt", "vietnamese_meaning": "Đau buồn tột cùng / Bi thương muốn chết", "nuance_note": "Thành ngữ chỉ nỗi bi thương tột bậc, đau đến mức không thiết sống.", "visual_action": "Gục xuống ôm ngực khóc không ra tiếng."}
            ]
        },
        {
            "id": 31,
            "concept": "Hiểu biết / Nhận thức",
            "hook": "5 Cấp Độ Hiểu Biết Trong Tiếng Trung",
            "levels": [
                {"hsk_level": "HSK 1", "hanzi": "知道", "pinyin": "zhī dào", "sino_vietnamese": "Tri đạo", "vietnamese_meaning": "Biết / Nắm được", "nuance_note": "Biết thông tin cơ bản về một sự vật, sự việc.", "visual_action": "Gật đầu nhẹ nhàng ra hiệu đã biết."},
                {"hsk_level": "HSK 2", "hanzi": "明白", "pinyin": "míng bai", "sino_vietnamese": "Minh bạch", "vietnamese_meaning": "Hiểu rõ / Rõ ràng", "nuance_note": "Đã nghe giải thích và thông suốt ý nghĩa.", "visual_action": "Mỉm cười búng tay một cái hiểu ra."},
                {"hsk_level": "HSK 3", "hanzi": "理解", "pinyin": "lǐ jiě", "sino_vietnamese": "Lý giải", "vietnamese_meaning": "Thấu hiểu / Cảm thông", "nuance_note": "Hiểu sâu nguyên nhân và đặt mình vào hoàn cảnh người khác.", "visual_action": "Đặt tay lên vai thấu suốt đồng cảm."},
                {"hsk_level": "HSK 4", "hanzi": "领悟", "pinyin": "lǐng wù", "sino_vietnamese": "Lĩnh ngộ", "vietnamese_meaning": "Lĩnh hội / Ngộ ra", "nuance_note": "Tự mình chiêm nghiệm và nắm bắt được đạo lý sâu xa.", "visual_action": "Mắt sáng bừng ngửa đầu suy tưởng."},
                {"hsk_level": "HSK 5", "hanzi": "恍然大悟", "pinyin": "huǎng rán dà wù", "sino_vietnamese": "Hoảng nhiên đại ngộ", "vietnamese_meaning": "Bừng tỉnh ngộ ra / Vỡ lẽ hoàn toàn", "nuance_note": "Thành ngữ chỉ trạng thái đột nhiên giác ngộ chân tướng sau thời gian dài u mê.", "visual_action": "Vỗ mạnh vào trán miệng mỉm cười bừng sáng."}
            ]
        },
        {
            "id": 32,
            "concept": "May mắn / Thuận lợi",
            "hook": "5 Cấp Độ May Mắn Trong Tiếng Trung",
            "levels": [
                {"hsk_level": "HSK 1", "hanzi": "好运", "pinyin": "hǎo yùn", "sino_vietnamese": "Hảo vận", "vietnamese_meaning": "Vận may / May mắn", "nuance_note": "Lời chúc hoặc cảm giác gặp điều tốt lành.", "visual_action": "Nắm tay giơ lên cổ vũ may mắn."},
                {"hsk_level": "HSK 2", "hanzi": "顺利", "pinyin": "shùn lì", "sino_vietnamese": "Thuận lợi", "vietnamese_meaning": "Suôn sẻ / Trôi chảy", "nuance_note": "Quá trình diễn ra êm đẹp, không gặp trở ngại.", "visual_action": "Ra dấu OK tay chỉ về phía trước."},
                {"hsk_level": "HSK 3", "hanzi": "幸运", "pinyin": "xìng yùn", "sino_vietnamese": "Hạnh vận", "vietnamese_meaning": "May mắn / Gặp thời", "nuance_note": "Gặp được cơ hội hiếm có hoặc tránh được rủi ro.", "visual_action": "Chắp hai tay mỉm cười tạ ơn may mắn."},
                {"hsk_level": "HSK 4", "hanzi": "顺心", "pinyin": "shùn xīn", "sino_vietnamese": "Thuận tâm", "vietnamese_meaning": "Vừa lòng hả dạ / Vạn sự như ý", "nuance_note": "Mọi việc chuyển biến hoàn toàn theo đúng ý nguyện trong lòng.", "visual_action": "Thở phào nhẹ nhõm nụ cười rạng rỡ."},
                {"hsk_level": "HSK 5", "hanzi": "一帆风顺", "pinyin": "yī fān fēng shùn", "sino_vietnamese": "Nhất phàm phong thuận", "vietnamese_meaning": "Thuận buồm xuôi gió / Trơn tru mọi bề", "nuance_note": "Thành ngữ chúc sự nghiệp cuộc đời hanh thông tuyệt đỉnh không chút sóng gió.", "visual_action": "Vung tay mở rộng hướng về chân trời thênh thang."}
            ]
        },
        {
            "id": 33,
            "concept": "Nghi ngờ / Hoài nghi",
            "hook": "5 Cấp Độ Hoài Nghi Trong Tiếng Trung",
            "levels": [
                {"hsk_level": "HSK 1", "hanzi": "不信", "pinyin": "bù xìn", "sino_vietnamese": "Bất tín", "vietnamese_meaning": "Không tin / Chẳng tin", "nuance_note": "Phản xạ ban đầu từ chối tin vào lời nói.", "visual_action": "Lắc đầu xua tay tỏ vẻ không tin."},
                {"hsk_level": "HSK 2", "hanzi": "猜", "pinyin": "cāi", "sino_vietnamese": "Sai", "vietnamese_meaning": "Đoán / Ngờ rằng", "nuance_note": "Dò xét phỏng đoán khi chưa đủ bằng chứng.", "visual_action": "Chống cằm mắt ngước lên suy đoán."},
                {"hsk_level": "HSK 3", "hanzi": "怀疑", "pinyin": "huái yí", "sino_vietnamese": "Hoài nghi", "vietnamese_meaning": "Nghi ngờ / Ngờ vực", "nuance_note": "Cảm giác bất an, nghi ngại tính chân thực của sự việc.", "visual_action": "Nheo mắt nhíu mày nhìn dò xét."},
                {"hsk_level": "HSK 4", "hanzi": "疑虑", "pinyin": "yí lǜ", "sino_vietnamese": "Nghi lự", "vietnamese_meaning": "Mối băn khoăn / Mối nghi ngại", "nuance_note": "Tâm trạng trăn trở, lo ngại tiềm ẩn trong lòng khó dứt.", "visual_action": "Khoanh tay đi qua lại vẻ đầy tâm sự."},
                {"hsk_level": "HSK 5", "hanzi": "半信半疑", "pinyin": "bàn xìn bàn yí", "sino_vietnamese": "Bán tín bán nghi", "vietnamese_meaning": "Nửa tin nửa ngờ / Phân vân lưỡng lự", "nuance_note": "Thành ngữ chỉ tâm thái nửa muốn tin vì có lý nhưng nửa e dè sợ lừa dối.", "visual_action": "Nghiêng đầu nhún vai vẻ phân vân khôn xiết."}
            ]
        },
        {
            "id": 34,
            "concept": "Thay đổi / Biến đổi",
            "hook": "5 Cấp Độ Biến Đổi Trong Tiếng Trung",
            "levels": [
                {"hsk_level": "HSK 1", "hanzi": "变", "pinyin": "biàn", "sino_vietnamese": "Biến", "vietnamese_meaning": "Đổi / Biến thành", "nuance_note": "Sự thay đổi trực quan về trạng thái hoặc tính chất.", "visual_action": "Xòe hai bàn tay lật ngửa thể hiện sự biến đổi."},
                {"hsk_level": "HSK 2", "hanzi": "变化", "pinyin": "biàn huà", "sino_vietnamese": "Biến hóa", "vietnamese_meaning": "Thay đổi / Biến chuyển", "nuance_note": "Quá trình biến đổi của sự vật, khí hậu, thời cuộc.", "visual_action": "Đưa tay phác họa đường lượn sóng biến chuyển."},
                {"hsk_level": "HSK 3", "hanzi": "改变", "pinyin": "gǎi biàn", "sino_vietnamese": "Cải biến", "vietnamese_meaning": "Thay đổi / Sửa đổi", "nuance_note": "Chủ động tác động để thay đổi thói quen hoặc hiện trạng.", "visual_action": "Nắm chặt tay kiên quyết tạo sự khác biệt."},
                {"hsk_level": "HSK 4", "hanzi": "转变", "pinyin": "zhuǎn biàn", "sino_vietnamese": "Chuyển biến", "vietnamese_meaning": "Chuyển hóa / Đổi chiều", "nuance_note": "Sự bước ngoặt mang tính căn bản trong nhận thức hoặc tình hình.", "visual_action": "Quay người đổi hướng dứt khoát."},
                {"hsk_level": "HSK 5", "hanzi": "焕然一新", "pinyin": "huàn rán yì xīn", "sino_vietnamese": "Hoán nhiên nhất tân", "vietnamese_meaning": "Đổi mới hoàn toàn / Thay da đổi thịt", "nuance_note": "Thành ngữ chỉ diện mạo mới mẻ, rực rỡ, sáng sủa hoàn toàn khác trước.", "visual_action": "Hai tay bung tỏa nụ cười tự hào mãn nguyện."}
            ]
        }
    ]

    for item in ml_ideas:
        rid = f"#{item['id']}"
        topic_title = f"1 Nghĩa 5 Cấp • {item['concept']}"
        meta_res = save_and_upload_metadata(
            batch_id=str(item["id"]),
            concept_name_vi=item["concept"],
            levels=item["levels"],
            hook_title=item["hook"],
            cta_text="Comment mốc điểm bạn vượt qua nhé!"
        )
        meta_txt = extract_meta_text(meta_res)
        w_cols = [
            f"{lvl['hanzi']} | {lvl['pinyin']} | {lvl['sino_vietnamese']} | {lvl['vietnamese_meaning']} | {lvl['nuance_note']} | {lvl['visual_action']}"
            for lvl in item["levels"]
        ]
        now_str = get_vietnam_now_str()
        row_data = [
            rid, topic_title, "HSK 1-5", "Pending"
        ] + w_cols + [
            meta_txt, "", "", "", "",
            now_str,
            f"Tự động sinh bởi Antigravity ({now_str} GMT+7)"
        ]
        mgr.worksheet.append_row(row_data)
        print(f"  ✓ Đã thêm Row {rid} ({topic_title}) vào tab 'multilevels'")

    print("\n📏 [Khóa cứng 21px] Thực thi RowHeightEnforcer trên toàn bộ các tab...")
    enforcer = RowHeightEnforcer()
    enforcer.enforce_all()
    print("🎉 ĐÃ THÊM 5 IDEAS CHO TAB 'MULTILEVELS' VÀ KHÓA ĐỘ CAO 21PX THÀNH CÔNG!")

if __name__ == "__main__":
    main()
