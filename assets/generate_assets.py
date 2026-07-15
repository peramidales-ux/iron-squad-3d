#!/usr/bin/env python3
"""Generate game assets: textures, audio, and models for Iron Squad"""
import struct, zlib, math, random, os, wave, json

BASE = os.path.dirname(os.path.abspath(__file__))

# ================================================================
#  PNG GENERATOR (no dependencies)
# ================================================================
def create_png(width, height, pixels_func, filepath):
    """Create PNG from pixel function. pixels_func(x,y) -> (r,g,b)"""
    def chunk(chunk_type, data):
        c = chunk_type + data
        return struct.pack('>I', len(data)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)

    raw = b''
    for y in range(height):
        raw += b'\x00'
        for x in range(width):
            r, g, b = pixels_func(x, y)
            raw += bytes([max(0,min(255,int(r))), max(0,min(255,int(g))), max(0,min(255,int(b)))])

    ihdr = struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0)
    idat = zlib.compress(raw, 6)

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', ihdr))
        f.write(chunk(b'IDAT', idat))
        f.write(chunk(b'IEND', b''))
    return os.path.getsize(filepath)

# ================================================================
#  WAV GENERATOR
# ================================================================
def create_wav(filepath, sample_rate, duration, gen_func):
    """Create WAV from generator function. gen_func(t) -> sample [-1,1]"""
    n_samples = int(sample_rate * duration)
    raw = b''
    for i in range(n_samples):
        t = i / sample_rate
        val = max(-1.0, min(1.0, gen_func(t)))
        raw += struct.pack('<h', int(val * 32767))

    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'wb') as f:
        data_size = len(raw)
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + data_size))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<I', 16))
        f.write(struct.pack('<HHIIHH', 1, 1, sample_rate, sample_rate * 2, 2, 16))
        f.write(b'data')
        f.write(struct.pack('<I', data_size))
        f.write(raw)
    return os.path.getsize(filepath)

# ================================================================
#  TEXTURE GENERATORS
# ================================================================
def noise2d(x, y, seed=0):
    n = int(x) + int(y) * 57 + int(seed) * 131
    n = (n << 13) ^ n
    return 1.0 - ((n * (n * n * 15731 + 789221) + 1376312589) & 0x7fffffff) / 1073741824.0

def fbm(x, y, octaves=4, seed=0):
    val = 0
    amp = 0.5
    for i in range(octaves):
        val += amp * noise2d(x * (2**i), y * (2**i), seed + i * 100)
        amp *= 0.5
    return val

def gen_concrete(x, y):
    n = fbm(x * 0.05, y * 0.05, 5, 42) * 0.3
    base = 140 + n * 60
    return (base, base - 5, base - 10)

def gen_sand(x, y):
    n = fbm(x * 0.03, y * 0.03, 4, 123) * 0.4
    base = 194 + n * 40
    return (base, base - 20, base - 50)

def gen_metal(x, y):
    n = fbm(x * 0.08, y * 0.02, 3, 77) * 0.3
    base = 100 + n * 40
    spec = max(0, n * 2)
    return (base + spec * 30, base + spec * 25, base + spec * 20)

def gen_wood(x, y):
    grain = math.sin(y * 0.3 + fbm(x * 0.1, y * 0.01, 3, 55) * 5) * 20
    base = 120 + grain
    return (base + 20, base - 10, base - 40)

def gen_brick(x, y):
    bx = x % 32
    by = y % 16
    offset = (y // 16) % 2 * 16
    bx2 = (x + offset) % 32
    if bx2 < 1 or by < 1:
        return (180, 175, 165)
    n = fbm(x * 0.1, y * 0.1, 2, 33) * 15
    return (160 + n, 80 + n * 0.5, 60 + n * 0.3)

def gen_dirt(x, y):
    n = fbm(x * 0.04, y * 0.04, 5, 99) * 0.5
    base = 100 + n * 50
    return (base + 20, base - 10, base - 30)

def gen_grass(x, y):
    n = fbm(x * 0.06, y * 0.06, 4, 200) * 0.4
    g = 100 + n * 60
    return (g * 0.4, g, g * 0.3)

def gen_water(x, y):
    t = fbm(x * 0.02, y * 0.02, 3, 300)
    return (40 + t * 20, 80 + t * 30, 160 + t * 40)

def gen_asphalt(x, y):
    n = fbm(x * 0.07, y * 0.07, 5, 444) * 0.25
    base = 60 + n * 30
    return (base, base, base + 2)

def gen_normal_map(base_func, x, y):
    eps = 2
    h0 = sum(base_func(x, y))
    hx = sum(base_func(x + eps, y))
    hy = sum(base_func(x, y + eps))
    nx = (h0 - hx) / (eps * 3)
    ny = (h0 - hy) / (eps * 3)
    return (int(128 + nx * 128), int(128 + ny * 128), 255)

# ================================================================
#  AUDIO GENERATORS
# ================================================================
def gen_gunshot(t, freq=200, decay=0.08):
    if t > decay * 3: return 0
    env = math.exp(-t / decay)
    noise = random.uniform(-1, 1) * 0.5
    tone = math.sin(2 * math.pi * freq * t) * 0.5
    return (noise + tone) * env * 0.7

def gen_explosion(t):
    if t > 1.0: return 0
    env = math.exp(-t * 3)
    noise = random.uniform(-1, 1)
    low = math.sin(2 * math.pi * 40 * t) * 0.5
    return (noise * 0.6 + low) * env * 0.8

def gen_footstep(t):
    if t > 0.15: return 0
    env = math.exp(-t * 30)
    noise = random.uniform(-1, 1) * 0.3
    tone = math.sin(2 * math.pi * 100 * t) * 0.7
    return (noise + tone) * env * 0.4

def gen_ambient(t):
    return (math.sin(2 * math.pi * 0.1 * t) * 0.1 +
            math.sin(2 * math.pi * 0.15 * t) * 0.08 +
            math.sin(2 * math.pi * 0.07 * t) * 0.05) * 0.3

def gen_music_loop(t, bpm=128):
    beat = t * bpm / 60
    kick = max(0, math.sin(2 * math.pi * 60 * t) * math.exp(-(beat % 1) * 8)) * 0.4
    hihat = (random.uniform(-1, 1) * 0.1 * max(0, math.exp(-(beat % 0.5) * 20))) if (beat % 0.5) < 0.05 else 0
    bass = math.sin(2 * math.pi * 55 * t) * 0.15 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.25 * t))
    pad = math.sin(2 * math.pi * 220 * t) * 0.03 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.1 * t))
    return max(-1, min(1, kick + hihat + bass + pad))

def gen_menu_music(t):
    melody_notes = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
    note_idx = int(t * 2) % len(melody_notes)
    freq = melody_notes[note_idx]
    melody = math.sin(2 * math.pi * freq * t) * 0.1
    pad = math.sin(2 * math.pi * 130.81 * t) * 0.05 * (0.5 + 0.5 * math.sin(2 * math.pi * 0.2 * t))
    amb = math.sin(2 * math.pi * 0.05 * t) * 0.02
    return max(-1, min(1, melody + pad + amb))

# ================================================================
#  GENERATE ALL ASSETS
# ================================================================
def main():
    total = 0
    tex_dir = os.path.join(BASE, 'textures')
    audio_dir = os.path.join(BASE, 'audio')
    os.makedirs(tex_dir, exist_ok=True)
    os.makedirs(audio_dir, exist_ok=True)

    print("=== Generating Textures (2048x2048) ===")
    textures = [
        ('concrete_wall.png', gen_concrete),
        ('sand_floor.png', gen_sand),
        ('metal_plate.png', gen_metal),
        ('wood_plank.png', gen_wood),
        ('brick_wall.png', gen_brick),
        ('dirt_ground.png', gen_dirt),
        ('grass.png', gen_grass),
        ('water.png', gen_water),
        ('asphalt.png', gen_asphalt),
    ]

    for name, func in textures:
        sz = create_png(2048, 2048, func, os.path.join(tex_dir, name))
        total += sz
        print(f"  {name}: {sz//1024}KB")
        # Normal map
        nm = create_png(1024, 1024, lambda x,y,f=func: gen_normal_map(f,x,y), os.path.join(tex_dir, f"nrm_{name}"))
        total += nm
        print(f"  nrm_{name}: {nm//1024}KB")

    # Skybox
    print("\n=== Generating Skybox ===")
    def gen_sky(x, y):
        h = y / 1024
        r = 135 + h * 80
        g = 180 + h * 50
        b = 220 + h * 30
        n = fbm(x * 0.01, y * 0.01, 3, 500) * 20
        return (r + n, g + n * 0.5, b + n * 0.3)
    for i, face in enumerate(['px','nx','py','ny','pz','nz']):
        sz = create_png(1024, 1024, gen_sky, os.path.join(tex_dir, f'sky_{face}.png'))
        total += sz
    print(f"  Skybox faces: 6x {sz//1024}KB")

    print("\n=== Generating Audio ===")
    sr = 44100

    # Gunshots
    guns = [
        ('rifle.wav', 0.08, 200), ('smg.wav', 0.06, 300),
        ('pistol.wav', 0.05, 400), ('deagle.wav', 0.1, 150),
        ('awp.wav', 0.15, 80), ('shotgun.wav', 0.12, 120),
        ('sniper.wav', 0.12, 100), ('mg.wav', 0.07, 250),
    ]
    for name, decay, freq in guns:
        sz = create_wav(os.path.join(audio_dir, name), sr, 0.5,
                       lambda t,d=decay,f=freq: gen_gunshot(t, f, d))
        total += sz
        print(f"  {name}: {sz//1024}KB")

    # Effects
    effects = [
        ('explosion.wav', 1.5, gen_explosion),
        ('hit.wav', 0.2, lambda t: gen_gunshot(t, 800, 0.03)),
        ('reload.wav', 0.8, lambda t: gen_footstep(t) * 2),
        ('footstep.wav', 0.3, gen_footstep),
        ('death.wav', 1.0, lambda t: gen_explosion(t) * 0.5),
        ('headshot.wav', 0.3, lambda t: gen_gunshot(t, 1200, 0.02)),
        ('round_start.wav', 2.0, lambda t: math.sin(2*math.pi*440*t)*max(0,1-t)*0.3),
        ('round_end.wav', 2.0, lambda t: math.sin(2*math.pi*330*t)*max(0,1-t*0.5)*0.3),
        ('buy.wav', 0.3, lambda t: math.sin(2*math.pi*600*t)*max(0,1-t*4)*0.2),
        ('bomb_plant.wav', 3.0, lambda t: (math.sin(2*math.pi*200*t)*max(0,1-t*0.3)*0.3 if t<1 else math.sin(2*math.pi*400*(t-1))*max(0,1-(t-1)*0.5)*0.3)),
        ('bomb_beep.wav', 0.5, lambda t: math.sin(2*math.pi*1000*t)*max(0,1-t*3)*0.3),
        ('ambient_wind.wav', 5.0, gen_ambient),
        ('ambient_battle.wav', 5.0, lambda t: gen_ambient(t) + random.uniform(-0.05,0.05)),
    ]
    for name, dur, func in effects:
        sz = create_wav(os.path.join(audio_dir, name), sr, dur, func)
        total += sz
        print(f"  {name}: {sz//1024}KB")

    # Music
    print("\n=== Generating Music ===")
    music_dir = os.path.join(audio_dir, 'music')
    os.makedirs(music_dir, exist_ok=True)

    music = [
        ('menu_theme.wav', 30, gen_menu_music),
        ('combat_1.wav', 30, gen_music_loop),
        ('combat_2.wav', 30, lambda t: gen_music_loop(t, 140)),
        ('victory.wav', 10, lambda t: math.sin(2*math.pi*523.25*t)*max(0,1-t*0.1)*0.3*(0.5+0.5*math.sin(2*math.pi*2*t))),
        ('defeat.wav', 10, lambda t: math.sin(2*math.pi*220*t)*max(0,1-t*0.1)*0.3),
    ]
    for name, dur, func in music:
        sz = create_wav(os.path.join(music_dir, name), sr, dur, func)
        total += sz
        print(f"  {name}: {sz//1024}KB")

    print(f"\n=== Total assets: {total//1024//1024}MB ({total//1024}KB) ===")
    return total

if __name__ == '__main__':
    main()
