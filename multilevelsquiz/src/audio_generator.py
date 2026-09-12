import os
import asyncio
import logging
import subprocess
import numpy as np
import scipy.io.wavfile as wavfile
try:
    from multilevelsquiz.src.config import config
except ImportError:
    from src.config import config

logger = logging.getLogger("AudioGenerator")

def ensure_tick_sound() -> str:
    """Ensure crisp, punchy countdown tick sound exists (Level 1)."""
    os.makedirs(config.assets_audio_dir, exist_ok=True)
    tick_mp3 = config.tick_audio_path
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

def ensure_swoosh_sound() -> str:
    """Ensure clean swoosh transition sound exists (Level 2)."""
    os.makedirs(config.assets_audio_dir, exist_ok=True)
    swoosh_mp3 = config.swoosh_audio_path
    wav_path = os.path.join(config.assets_audio_dir, "swoosh.wav")

    sample_rate = 44100
    duration = 0.4
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    freq = np.linspace(300, 1800, len(t))
    noise = np.random.normal(0, 0.3, len(t))
    env = np.sin(np.pi * (t / duration)) ** 2
    signal = (np.sin(2 * np.pi * freq * t) * 0.5 + noise * 0.5) * env
    signal = signal / np.max(np.abs(signal)) * 0.9
    audio_int16 = (signal * 32767).astype(np.int16)

    wavfile.write(wav_path, sample_rate, audio_int16)
    subprocess.run([
        "ffmpeg", "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        swoosh_mp3
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return swoosh_mp3

def ensure_ding_sound() -> str:
    """Ensure crystal clear ding chime sound exists (Level 3)."""
    os.makedirs(config.assets_audio_dir, exist_ok=True)
    ding_mp3 = config.ding_audio_path
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
        ding_mp3
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return ding_mp3

def ensure_tension_sound() -> str:
    """Ensure tension heartbeat / riser sound exists (Level 4)."""
    os.makedirs(config.assets_audio_dir, exist_ok=True)
    tension_mp3 = config.tension_audio_path
    wav_path = os.path.join(config.assets_audio_dir, "tension.wav")

    sample_rate = 44100
    duration = 0.6
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    f1 = 90
    f2 = 180
    pulse = np.sin(2 * np.pi * f1 * t) * np.exp(-12 * t) + 0.6 * np.sin(2 * np.pi * f2 * t) * np.exp(-15 * t)
    pulse = pulse / np.max(np.abs(pulse)) * 0.95
    audio_int16 = (pulse * 32767).astype(np.int16)

    wavfile.write(wav_path, sample_rate, audio_int16)
    subprocess.run([
        "ffmpeg", "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        tension_mp3
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return tension_mp3

def ensure_victory_sound() -> str:
    """Ensure epic victory/glow fanfare chime exists (Level 5 Boss)."""
    os.makedirs(config.assets_audio_dir, exist_ok=True)
    victory_mp3 = config.victory_audio_path
    wav_path = os.path.join(config.assets_audio_dir, "victory.wav")

    sample_rate = 44100
    duration = 1.4
    t = np.linspace(0, duration, int(sample_rate * duration), False)

    chord = (
        1.0 * np.sin(2 * np.pi * 523.25 * t) * np.exp(-2.2 * t) +   # C5
        0.8 * np.sin(2 * np.pi * 659.25 * t) * np.exp(-2.2 * t) +   # E5
        0.9 * np.sin(2 * np.pi * 783.99 * t) * np.exp(-2.0 * t) +   # G5
        0.7 * np.sin(2 * np.pi * 1046.50 * t) * np.exp(-1.8 * t)    # C6
    )
    chord = chord / np.max(np.abs(chord)) * 0.95
    audio_int16 = (chord * 32767).astype(np.int16)

    wavfile.write(wav_path, sample_rate, audio_int16)
    subprocess.run([
        "ffmpeg", "-y", "-i", wav_path,
        "-codec:a", "libmp3lame", "-qscale:a", "2",
        victory_mp3
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    glow_mp3 = config.glow_audio_path
    if os.path.abspath(victory_mp3) != os.path.abspath(glow_mp3):
        import shutil
        shutil.copy(victory_mp3, glow_mp3)
    return victory_mp3

def ensure_all_sound_effects():
    """Generate and verify all required sound effects."""
    ensure_tick_sound()
    ensure_swoosh_sound()
    ensure_ding_sound()
    ensure_tension_sound()
    ensure_victory_sound()

async def _generate_single_chinese_tts(hanzi: str, output_path: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "-15%"):
    import edge_tts
    communicate = edge_tts.Communicate(hanzi, voice, rate=rate)
    await communicate.save(output_path)

def generate_chinese_voice(hanzi: str, voice: str = "zh-CN-XiaoxiaoNeural", rate: str = "-15%", overwrite: bool = False) -> str:
    """Generate crystal clean Chinese speech pronunciation for given Hanzi."""
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
        logger.info(f"Generated clean Chinese TTS for '{hanzi}' -> {output_path}")
    except Exception as e:
        logger.warning(f"Failed to generate TTS for '{hanzi}': {e}")
        return ""

    return output_path

async def _generate_single_vietnamese_tts(text: str, output_path: str, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+0%"):
    import edge_tts
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)

def generate_vietnamese_voice(text: str, voice: str = "vi-VN-HoaiMyNeural", rate: str = "+0%", overwrite: bool = False) -> str:
    """Generate natural Vietnamese speech for CTA / Outro narration."""
    audio_dir = os.path.join(config.assets_audio_dir, "cta")
    os.makedirs(audio_dir, exist_ok=True)

    safe_name = f"cta_{abs(hash(text)) % 1000000}"
    output_path = os.path.join(audio_dir, f"{safe_name}.mp3")

    if not overwrite and os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
        return output_path

    try:
        asyncio.run(_generate_single_vietnamese_tts(text, output_path, voice, rate=rate))
        logger.info(f"Generated Vietnamese CTA voice -> {output_path}")
    except Exception as e:
        logger.warning(f"Failed to generate Vietnamese CTA TTS: {e}")
        return ""

    return output_path
