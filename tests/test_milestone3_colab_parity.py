import os
import sys
import json
import yaml
import importlib
import pytest

try:
    import nbformat
except ImportError:
    nbformat = None

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

REQUIRED_16_PACKAGES = [
    "manim",
    "edge-tts",
    "opencv-python-headless",
    "opencc-python-reimplemented",
    "gspread",
    "google-api-python-client",
    "google-auth",
    "google-auth-oauthlib",
    "pypinyin",
    "requests",
    "rich",
    "scipy",
    "numpy",
    "Pillow",
    "pydub",
    "pyyaml",
]

MODULE_MAP = {
    "manim": "manim",
    "edge_tts": "edge-tts",
    "cv2": "opencv-python-headless",
    "opencc": "opencc-python-reimplemented",
    "gspread": "gspread",
    "googleapiclient": "google-api-python-client",
    "google.auth": "google-auth",
    "google_auth_oauthlib": "google-auth-oauthlib",
    "pypinyin": "pypinyin",
    "requests": "requests",
    "rich": "rich",
    "scipy": "scipy",
    "numpy": "numpy",
    "PIL": "Pillow",
    "pydub": "pydub",
    "yaml": "pyyaml",
}


def test_all_16_python_packages_importable():
    """Verify that all 16 reference Python packages are installed and importable."""
    for mod_name, pkg_name in MODULE_MAP.items():
        try:
            mod = importlib.import_module(mod_name)
            assert mod is not None, f"Module {mod_name} ({pkg_name}) imported as None"
        except ImportError as e:
            pytest.fail(f"Required package {pkg_name} (module: {mod_name}) failed to import: {e}")


def test_workflow_01_ideation_dependencies():
    """Verify 01_quiz_ideation_and_scripting.yml has valid YAML, schedule, and rich in pip install."""
    wf_path = os.path.join(PROJECT_ROOT, ".github", "workflows", "01_quiz_ideation_and_scripting.yml")
    assert os.path.exists(wf_path), f"Workflow file not found: {wf_path}"

    with open(wf_path, "r", encoding="utf-8") as f:
        content = f.read()
        parsed = yaml.safe_load(content)

    assert parsed.get("name") is not None
    assert "rich" in content, "Workflow 01 missing 'rich' in pip install step"
    assert "pypinyin" in content, "Workflow 01 missing 'pypinyin'"
    assert "gspread" in content, "Workflow 01 missing 'gspread'"
    assert "pyyaml" in content, "Workflow 01 missing 'pyyaml'"

    # Schedule trigger check: 00:00 GMT+7 -> 17:00 UTC
    on_block = parsed.get("on") or parsed.get(True)
    cron_expr = on_block["schedule"][0]["cron"]
    assert cron_expr == "0 17 * * *", f"Expected cron '0 17 * * *', got '{cron_expr}'"


def test_workflow_02_video_rendering_dependencies():
    """Verify 02_quiz_video_rendering_and_qc.yml has valid YAML, system packages, and all 16 dependencies."""
    wf_path = os.path.join(PROJECT_ROOT, ".github", "workflows", "02_quiz_video_rendering_and_qc.yml")
    assert os.path.exists(wf_path), f"Workflow file not found: {wf_path}"

    with open(wf_path, "r", encoding="utf-8") as f:
        content = f.read()
        parsed = yaml.safe_load(content)

    assert parsed.get("name") is not None
    assert "fonts-noto-color-emoji" in content, "Workflow 02 missing fonts-noto-color-emoji in apt-get"

    # Verify all 16 dependencies are installed in pip install step
    for pkg in REQUIRED_16_PACKAGES:
        assert pkg in content, f"Workflow 02 missing package '{pkg}' in pip install step"

    # Schedule trigger check: runs every 4h offset
    on_block = parsed.get("on") or parsed.get(True)
    cron_expr = on_block["schedule"][0]["cron"]
    assert cron_expr == "30 18,22,2,6,10,14 * * *", f"Expected cron '30 18,22,2,6,10,14 * * *', got '{cron_expr}'"


def test_workflow_03_and_04_valid_yaml():
    """Verify 03_quiz_morning_audit.yml and 04_quiz_social_distribution.yml are valid YAML and contain rich."""
    for wf_name in ["03_quiz_morning_audit.yml", "04_quiz_social_distribution.yml"]:
        wf_path = os.path.join(PROJECT_ROOT, ".github", "workflows", wf_name)
        assert os.path.exists(wf_path), f"Workflow file not found: {wf_path}"

        with open(wf_path, "r", encoding="utf-8") as f:
            content = f.read()
            parsed = yaml.safe_load(content)

        assert parsed.get("name") is not None
        assert "rich" in content, f"Workflow {wf_name} missing 'rich' in pip install step"
        assert "scripts/enforce_row_height_21px.py" in content, f"Workflow {wf_name} missing 21px row height step"


def test_colab_notebook_existence_and_schema():
    """Verify scripts/render_quiz_colab.ipynb exists, is valid JSON, and passes nbformat schema validation."""
    nb_path = os.path.join(PROJECT_ROOT, "scripts", "render_quiz_colab.ipynb")
    assert os.path.exists(nb_path), f"Colab notebook not found at {nb_path}"

    with open(nb_path, "r", encoding="utf-8") as f:
        nb_dict = json.load(f)

    if nbformat is not None:
        # Validate with official nbformat validator
        nb_node = nbformat.from_dict(nb_dict)
        nbformat.validate(nb_node)
        cells = nb_node.cells
        nbformat_ver = nb_node.nbformat
    else:
        # Clean json-based fallback validation when nbformat is not installed
        assert "cells" in nb_dict, "Notebook missing 'cells' key"
        assert "metadata" in nb_dict, "Notebook missing 'metadata' key"
        assert "nbformat" in nb_dict, "Notebook missing 'nbformat' key"
        assert "nbformat_minor" in nb_dict, "Notebook missing 'nbformat_minor' key"
        nbformat_ver = nb_dict.get("nbformat")
        cells = nb_dict["cells"]

    assert nbformat_ver == 4
    assert len(cells) >= 8, f"Expected at least 8 cells, found {len(cells)}"

    # Check cell contents
    all_source = ""
    for c in cells:
        src = c.get("source", "") if isinstance(c, dict) else getattr(c, "source", "")
        if isinstance(src, list):
            all_source += " " + "".join(src)
        else:
            all_source += " " + str(src)

    # 1. System packages
    assert "fonts-noto-color-emoji" in all_source, "Notebook missing fonts-noto-color-emoji in system dependencies"
    assert "ffmpeg" in all_source, "Notebook missing ffmpeg"
    assert "libcairo2-dev" in all_source, "Notebook missing libcairo2-dev"
    assert "libpango1.0-dev" in all_source, "Notebook missing libpango1.0-dev"

    # 2. All 16 Python dependencies
    for pkg in REQUIRED_16_PACKAGES:
        assert pkg in all_source, f"Notebook missing required Python dependency: {pkg}"

    # 3. Interactive execution harness & 21px row height
    assert "run_render_dispatcher.py" in all_source, "Notebook missing run_render_dispatcher.py execution harness"
    assert "--local" in all_source, "Notebook execution harness missing --local flag"
    assert "enforce_row_height_21px.py" in all_source, "Notebook missing enforce_row_height_21px.py"
    assert "chmod 600" in all_source, "Notebook missing Zero-Leak Vault chmod 600 hardening"


def test_colab_worker_quiz_alignment():
    """Verify colab/colab_worker_quiz.py contains all 16 dependencies, emoji font, and 21px enforcement."""
    worker_path = os.path.join(PROJECT_ROOT, "colab", "colab_worker_quiz.py")
    assert os.path.exists(worker_path), f"Colab worker not found at {worker_path}"

    with open(worker_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Verify fonts-noto-color-emoji in system packages
    assert "fonts-noto-color-emoji" in content, "colab_worker_quiz.py missing fonts-noto-color-emoji in apt-get"

    # Verify all 16 dependencies in packages_map
    for mod, pkg in MODULE_MAP.items():
        assert f'"{pkg}"' in content or f"'{pkg}'" in content, (
            f"colab_worker_quiz.py packages_map missing package '{pkg}'"
        )

    # Verify post-execution row height enforcement
    assert "enforce_row_height_21px.py" in content, (
        "colab_worker_quiz.py missing post-execution enforce_row_height_21px.py call"
    )

    # Verify Zero-Leak Vault credential permission hardening (chmod 0o600)
    assert "0o600" in content and "chmod" in content, (
        "colab_worker_quiz.py missing os.chmod(target, 0o600) credential hardening"
    )

