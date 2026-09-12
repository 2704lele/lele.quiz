import os
import asyncio
import subprocess
import numpy as np
import scipy.io.wavfile as wavfile
import logging
from src.config import config

logger = logging.getLogger("AudioGenerator")

def ensure_bell_sound() -> str:
    """Ensure a 100% pure crystal chime exists (ZERO vocal background)."""
    os.makedirs(config.assets_audio_dir, exist_ok=True)
    bell_mp3 = config.bell_audio_path
    wav_path = os.path.join(config.assets_audio_dir, "ding.wav")
    
    sample_rate = 44100
    duration = 0.85
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    signal = (
        1.0 * np.sin(2 * np.pi * 1318.51 * t) * np.exp(-3.8 * t) +
        0.7 * np.sin(2 * np.pi * 1975.53 * t) * np.exp(-5.0 * t) +
        0.4 * np.sin(2 * np.pi * 2637.02 * t) * np.exp(-6.8 * t) +
        0.2 * np.sin(2 * np.pi * 3951.07 * t) * np.exp(-8.5 * t)
    )
    signal = signal / np.max(np.abs(signal)) * 0.95
    audio_int16 = (signal * 32767).astype(np.int16)
    
    wavfile.write(wav_path, sample_rate, audio_int16)
    subprocess.run([
        "ffmpeg", "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        bell_mp3
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    
    ding_mp3 = os.path.join(config.assets_audio_dir, "ding.mp3")
    if os.path.abspath(bell_mp3) != os.path.abspath(ding_mp3):
        import shutil
        shutil.copy(bell_mp3, ding_mp3)
    root_bell = os.path.join(config.base_dir, "bell.mp3")
    if os.path.abspath(bell_mp3) != os.path.abspath(root_bell):
        import shutil
        shutil.copy(bell_mp3, root_bell)
    return bell_mp3

def ensure_tick_sound() -> str:
    """Ensure crisp, punchy countdown tick sound exists."""
    os.makedirs(config.assets_audio_dir, exist_ok=True)
    tick_mp3 = os.path.join(config.assets_audio_dir, "tick.mp3")
    wav_path = os.path.join(config.assets_audio_dir, "tick.wav")
    
    sample_rate = 44100
    duration = 0.12
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    click = np.sin(2 * np.pi * 3200 * t) * np.exp(-120 * t)
    body = 0.85 * np.sin(2 * np.pi * 980 * t) * np.exp(-45 * t) + 0.45 * np.sin(2 * np.pi * 1650 * t) * np.exp(-60 * t)
    tick = click + body
    tick = tick / np.max(np.abs(tick)) * 0.95
    audio_int16 = (tick * 32767).astype(np.int16)
    
    wavfile.write(wav_path, sample_rate, audio_int16)
    subprocess.run([
        "ffmpeg", "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        tick_mp3
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return tick_mp3

async def _generate_single_chinese_tts(hanzi: str, output_path: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "-20%"):
    import edge_tts
    communicate = edge_tts.Communicate(hanzi, voice, rate=rate)
    await communicate.save(output_path)

def generate_chinese_voice(hanzi: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "-20%", overwrite: bool = False) -> str:
    """Generate crystal clean, slower Chinese speech pronunciation for given Hanzi."""
    words_audio_dir = os.path.join(config.assets_audio_dir, "words")
    os.makedirs(words_audio_dir, exist_ok=True)
    
    safe_name = "".join([c for c in hanzi if c.isalnum() or c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"])
    if not safe_name:
        safe_name = f"word_{hash(hanzi)}"
    output_path = os.path.join(words_audio_dir, f"{safe_name}.mp3")
    
    if not overwrite and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path
        
    try:
        asyncio.run(_generate_single_chinese_tts(hanzi, output_path, voice, rate=rate))
        logger.info(f"Generated clean Chinese TTS ({rate}) for '{hanzi}' -> {output_path}")
    except Exception as e:
        logger.warning(f"Failed to generate TTS for '{hanzi}': {e}")
        return ""
        
    return output_path
