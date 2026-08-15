import math
import struct
import wave
import os

SAMPLE_RATE = 44100

def write_wav(filepath, samples):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with wave.open(filepath, 'w') as f:
        f.setnchannels(1)
        f.setsampwidth(2) # 16-bit
        f.setframerate(SAMPLE_RATE)
        packed_data = bytearray()
        for sample in samples:
            s = max(-1.0, min(1.0, sample))
            int_val = int(s * 32767)
            packed_data.extend(struct.pack('<h', int_val))
        f.writeframes(packed_data)

def gen_click():
    duration = 0.04
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-i / (SAMPLE_RATE * 0.006))
        freq = 700.0 - 400.0 * (t / duration)
        sine = math.sin(2 * math.pi * freq * t)
        noise = 0.05 * ((i % 7) / 3.5 - 1.0)
        samples.append(env * (0.15 * sine + noise))
    return samples

def gen_hover():
    duration = 0.025
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-i / (SAMPLE_RATE * 0.004))
        freq = 550.0 + 150.0 * (t / duration)
        sine = math.sin(2 * math.pi * freq * t)
        samples.append(env * 0.04 * sine)
    return samples

def gen_open():
    duration = 0.12
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.sin(math.pi * (t / duration))
        freq = 480.0 + 320.0 * (t / duration)
        sine1 = math.sin(2 * math.pi * freq * t)
        sine2 = 0.4 * math.sin(2 * math.pi * (freq * 1.4) * t)
        samples.append(env * 0.08 * (sine1 + sine2))
    return samples

def gen_close():
    duration = 0.12
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.sin(math.pi * (t / duration))
        freq = 700.0 - 320.0 * (t / duration)
        sine1 = math.sin(2 * math.pi * freq * t)
        sine2 = 0.4 * math.sin(2 * math.pi * (freq * 0.75) * t)
        samples.append(env * 0.08 * (sine1 + sine2))
    return samples

def gen_toggle():
    duration = 0.05
    num_samples = int(SAMPLE_RATE * duration)
    samples = []
    for i in range(num_samples):
        t = i / SAMPLE_RATE
        env = math.exp(-i / (SAMPLE_RATE * 0.01))
        freq = 350.0 if t < duration / 2 else 600.0
        sine = math.sin(2 * math.pi * freq * t)
        samples.append(env * 0.08 * sine)
    return samples


if __name__ == "__main__":
    audio_dir = os.path.join(os.path.dirname(__file__), "audio")
    write_wav(os.path.join(audio_dir, "sfx_click.wav"), gen_click())
    write_wav(os.path.join(audio_dir, "sfx_hover.wav"), gen_hover())
    write_wav(os.path.join(audio_dir, "sfx_open.wav"), gen_open())
    write_wav(os.path.join(audio_dir, "sfx_close.wav"), gen_close())
    write_wav(os.path.join(audio_dir, "sfx_toggle.wav"), gen_toggle())
    print("UI Audio files generated successfully in:", audio_dir)
