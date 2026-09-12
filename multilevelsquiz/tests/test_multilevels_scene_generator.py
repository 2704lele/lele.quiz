import os
import sys
import pytest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from multilevelsquiz.src.scene_generator import generate_scene_code, create_scene_file
from multilevelsquiz.src.llm_client import FALLBACK_MULTILEVELS_BANK

def test_generate_scene_code():
    sample_batch = FALLBACK_MULTILEVELS_BANK[0]
    levels = sample_batch["levels"]
    concept = sample_batch["concept_name_vi"]
    hook = sample_batch["hook_title"]

    code = generate_scene_code(
        levels=levels,
        concept_name=concept,
        hook_title=hook,
        scene_name="TestScene",
        cta_text=sample_batch.get("cta_text", "")
    )

    assert "class TestScene(Scene):" in code
    assert "1 NGHĨA - 5 CẤP ĐỘ" in code
    assert "LEVEL_TITLES" in code
    assert "BẠN ĐANG Ở HSK NÀO?" in code
    assert "不高兴" in code
    assert "大发雷霆" in code

def test_create_scene_file(tmp_path):
    sample_batch = FALLBACK_MULTILEVELS_BANK[0]
    out_file = str(tmp_path / "test_scene.py")

    path = create_scene_file(
        levels=sample_batch["levels"],
        concept_name=sample_batch["concept_name_vi"],
        hook_title=sample_batch["hook_title"],
        output_py_path=out_file,
        scene_name="TestSceneFile"
    )

    assert os.path.exists(path)
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "class TestSceneFile(Scene):" in content
