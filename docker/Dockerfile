FROM python:3.12-slim

# Install core audio/video packages & manim dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    sox \
    libsox-fmt-all \
    libpango1.0-dev \
    libcairo2-dev \
    pkg-config \
    build-essential \
    fonts-noto-cjk \
    fonts-noto-color-emoji \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root vscode user with UID 1000
RUN useradd -m -s /bin/bash -u 1000 vscode

WORKDIR /workspace

# Install common Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt 2>/dev/null || true
RUN pip install --no-cache-dir manim edge-tts gspread google-auth rich textual pytest pytest-mock requests

USER vscode
CMD ["python3", "monitor.py", "--status"]
