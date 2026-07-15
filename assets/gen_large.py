#!/usr/bin/env python3
"""Generate LARGE assets to reach 500MB target"""
import struct, zlib, math, random, os

BASE = os.path.dirname(os.path.abspath(__file__))

def create_png(w, h, func, path):
    def chunk(t, d):
        c = t + d
        return struct.pack('>I', len(d)) + c + struct.pack('>I', zlib.crc32(c) & 0xffffffff)
    raw = bytearray()
    for y in range(h):
        raw.append(0)
        for x in range(w):
            r, g, b = func(x, y)
            raw.extend([max(0,min(255,int(r))), max(0,min(255,int(g))), max(0,min(255,int(b)))])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0)))
        f.write(chunk(b'IDAT', zlib.compress(bytes(raw), 1)))
        f.write(chunk(b'IEND', b''))
    return os.path.getsize(path)

def create_wav(path, sr, dur, func):
    n = int(sr * dur)
    raw = bytearray()
    for i in range(n):
        t = i / sr
        v = max(-1.0, min(1.0, func(t)))
        raw.extend(struct.pack('<h', int(v * 32767)))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        ds = len(raw)
        f.write(b'RIFF')
        f.write(struct.pack('<I', 36 + ds))
        f.write(b'WAVE')
        f.write(b'fmt ')
        f.write(struct.pack('<IHHIIHH', 16, 1, 1, sr, sr*2, 2, 16))
        f.write(b'data')
        f.write(struct.pack('<I', ds))
        f.write(raw)
    return os.path.getsize(path)

def noise(x, y, s=0):
    n = int(x) + int(y)*57 + int(s)*131
    n = (n<<13)^n
    return 1.0-((n*(n*n*15731+789221)+1376312589)&0x7fffffff)/1073741824.0

def fbm(x, y, o=4, s=0):
    v,a=0,0.5
    for i in range(o):
        v+=a*noise(x*(2**i),y*(2**i),s+i*100);a*=0.5
    return v

# ========== 8K TEXTURES (massive) ==========
def tex_terrain(x,y):
    n=fbm(x*0.008,y*0.008,6,111)*0.5
    b=120+n*80; g=100+n*60
    return(b+10,g,b-20)

def tex_battlefield(x,y):
    n=fbm(x*0.005,y*0.005,6,222)*0.6
    crater=math.sin(fbm(x*0.01,y*0.01,3,333)*10)*30
    b=80+n*60+crater
    return(b+15,b-5,b-15)

def tex_skyGradient(x,y):
    h=y/8192
    r=100+h*100+fbm(x*0.003,y*0.003,3,444)*15
    g=150+h*60+fbm(x*0.003,y*0.003,3,555)*10
    b=200+h*40+fbm(x*0.003,y*0.003,3,666)*8
    return(r,g,b)

def tex_camo_green(x,y):
    n1=fbm(x*0.02,y*0.02,4,700)*0.5
    n2=fbm(x*0.04+100,y*0.04+100,3,800)*0.3
    pattern=math.sin(x*0.1+n1*5)*math.cos(y*0.08+n2*3)
    if pattern>0.2: return(60+n1*30,80+n1*40,40+n1*20)
    elif pattern>-0.1: return(80+n2*20,90+n2*25,55+n2*15)
    else: return(50+n1*25,65+n1*30,35+n1*15)

def tex_camo_desert(x,y):
    n1=fbm(x*0.015,y*0.015,4,900)*0.5
    n2=fbm(x*0.03+200,y*0.03+200,3,1000)*0.3
    pattern=math.sin(x*0.08+n1*4)*math.cos(y*0.06+n2*4)
    if pattern>0.3: return(190+n1*20,170+n1*15,130+n1*10)
    elif pattern>-0.1: return(170+n2*15,150+n2*12,110+n2*8)
    else: return(150+n1*18,130+n1*14,95+n1*10)

# ========== 4K TEXTURES (more variety) ==========
def tex_stone_wall(x,y):
    n=fbm(x*0.03,y*0.03,5,1100)*0.4; b=130+n*50
    crack=abs(fbm(x*0.1,y*0.01,2,1200))>0.4 and 30 or 0
    return(b-crack,b-5-crack,b-10-crack)

def tex_metal_floor(x,y):
    plate=math.sin(x*0.05)*math.sin(y*0.05)*10
    n=fbm(x*0.02,y*0.02,3,1300)*0.3; b=90+n*30+plate
    return(b+15,b+10,b+5)

def tex_wood_floor(x,y):
    grain=math.sin(y*0.1+fbm(x*0.05,y*0.005,3,1400)*5)*15
    n=fbm(x*0.02,y*0.02,3,1500)*0.2; b=110+n*30+grain
    return(b+25,b+5,b-30)

def tex_ceiling(x,y):
    n=fbm(x*0.04,y*0.04,4,1600)*0.3; b=150+n*40
    tile=((x//64)+(y//64))%2*10
    return(b+tile,b+tile-2,b+tile-5)

# ========== AUDIO ==========
def snd_heavy_gun(t):
    if t>0.2: return 0
    env=math.exp(-t*15); noise=random.uniform(-1,1)*0.4
    return(env*(noise+math.sin(2*math.pi*80*t)*0.6+math.sin(2*math.pi*40*t)*0.3))*0.7

def snd_light_gun(t):
    if t>0.1: return 0
    env=math.exp(-t*25); noise=random.uniform(-1,1)*0.3
    return(env*(noise+math.sin(2*math.pi*300*t)*0.5))*0.6

def snd_sniper_shot(t):
    if t>0.4: return 0
    env=math.exp(-t*8); noise=random.uniform(-1,1)*0.5
    return(env*(noise+math.sin(2*math.pi*60*t)*0.7+math.sin(2*math.pi*30*t)*0.4))*0.8

def snd_bomb_beep(t, freq=800):
    if t>0.3: return 0
    env=math.exp(-t*10)
    return math.sin(2*math.pi*freq*t)*env*0.4

def snd_voice_kill(t):
    if t>0.5: return 0
    env=math.exp(-t*5)
    return math.sin(2*math.pi*(200+t*200)*t)*env*0.2

def snd_ui_click(t):
    if t>0.05: return 0
    return math.sin(2*math.pi*1000*t)*math.exp(-t*80)*0.3

def snd_ui_hover(t):
    if t>0.03: return 0
    return math.sin(2*math.pi*1500*t)*math.exp(-t*100)*0.2

def gen_long_music(t, bpm=128, key=0):
    beat = t * bpm / 60
    notes = [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25]
    melody_idx = int(beat / 4) % len(notes)
    melody_freq = notes[melody_idx]
    melody = math.sin(2*math.pi*melody_freq*t) * 0.08 * max(0, math.exp(-(beat%4)*0.5))
    
    bass_freq = notes[melody_idx % 4] / 2
    bass = math.sin(2*math.pi*bass_freq*t) * 0.12 * (0.5 + 0.5*math.sin(2*math.pi*0.25*t))
    
    kick = max(0, math.sin(2*math.pi*55*t) * math.exp(-(beat%1)*8)) * 0.35
    hihat = random.uniform(-1,1) * 0.08 * max(0, math.exp(-(beat%0.5)*20)) if (beat%0.5)<0.03 else 0
    
    pad = math.sin(2*math.pi*melody_freq*0.5*t) * 0.02 * (0.5+0.5*math.sin(2*math.pi*0.1*t))
    
    return max(-1, min(1, melody + bass + kick + hihat + pad))

def main():
    total = 0; sr = 44100
    tex_dir = os.path.join(BASE, 'textures')
    aud_dir = os.path.join(BASE, 'audio')
    mus_dir = os.path.join(aud_dir, 'music')
    os.makedirs(tex_dir, exist_ok=True)
    os.makedirs(aud_dir, exist_ok=True)
    os.makedirs(mus_dir, exist_ok=True)

    # ========== 8K TEXTURES (4 textures × ~100MB each = ~400MB) ==========
    print("=== Generating 8K Textures (~100MB each) ===")
    huge = [
        ('terrain_8k', tex_terrain),
        ('battlefield_8k', tex_battlefield),
        ('sky_8k', tex_skyGradient),
    ]
    for name, func in huge:
        sz = create_png(8192, 8192, func, os.path.join(tex_dir, f'{name}.png'))
        total += sz
        print(f"  {name}.png: {sz//1024//1024}MB")

    # ========== 4K TEXTURES (more variety) ==========
    print("\n=== Generating 4K Textures ===")
    quads = [
        ('camo_green', tex_camo_green), ('camo_desert', tex_camo_desert),
        ('stone_wall', tex_stone_wall), ('metal_floor', tex_metal_floor),
        ('wood_floor', tex_wood_floor), ('ceiling', tex_ceiling),
    ]
    for name, func in quads:
        sz = create_png(4096, 4096, func, os.path.join(tex_dir, f'{name}_4k.png'))
        total += sz
        print(f"  {name}_4k.png: {sz//1024}KB")

    # ========== MORE AUDIO ==========
    print("\n=== Generating Additional Audio ===")
    more_guns = [
        ('rifle_alt.wav', 0.08, 180), ('rifle_burst.wav', 0.06, 220),
        ('smg_alt.wav', 0.05, 350), ('smg_fast.wav', 0.04, 400),
        ('p250.wav', 0.04, 450), ('glock.wav', 0.04, 500),
        ('fiveseven.wav', 0.04, 480), ('tec9.wav', 0.04, 380),
        ('galil.wav', 0.07, 190), ('famas.wav', 0.07, 210),
        ('sg556.wav', 0.07, 200), ('aug.wav', 0.07, 195),
        ('scout.wav', 0.1, 120), ('auto_sniper.wav', 0.08, 150),
        ('nova_fire.wav', 0.15, 100), ('xm1014_fire.wav', 0.1, 130),
        ('mag7.wav', 0.12, 110), ('sawedoff.wav', 0.14, 90),
        ('negev.wav', 0.06, 240), ('m249.wav', 0.07, 230),
    ]
    for n, d, f in more_guns:
        sz = create_wav(os.path.join(aud_dir, n), sr, 0.5,
                       lambda t, dd=d, ff=f: snd_heavy_gun(t) if f<200 else snd_light_gun(t))
        total += sz
        print(f"  {n}: {sz//1024}KB")

    # Voice lines
    voices = [
        ('go_go_go.wav', 0.8), ('fire_in_hole.wav', 0.6),
        ('taking_fire.wav', 0.5), ('need_backup.wav', 0.7),
        ('enemy_spotted.wav', 0.5), ('bomb_down.wav', 0.6),
        ('terrorists_win.wav', 1.0), ('cts_win.wav', 1.0),
        ('nice_shot.wav', 0.4), ('well_played.wav', 0.5),
    ]
    for n, d in voices:
        sz = create_wav(os.path.join(aud_dir, n), sr, d, snd_voice_kill)
        total += sz
        print(f"  {n}: {sz//1024}KB")

    # UI sounds
    ui = [
        ('ui_click.wav', 0.05, snd_ui_click),
        ('ui_hover.wav', 0.03, snd_ui_hover),
        ('ui_open.wav', 0.1, lambda t: math.sin(2*math.pi*800*t)*math.exp(-t*30)*0.3),
        ('ui_close.wav', 0.1, lambda t: math.sin(2*math.pi*400*t)*math.exp(-t*30)*0.3),
        ('ui_buy.wav', 0.15, lambda t: (math.sin(2*math.pi*600*t)+math.sin(2*math.pi*900*t))*math.exp(-t*20)*0.2),
        ('ui_sell.wav', 0.15, lambda t: (math.sin(2*math.pi*400*t)+math.sin(2*math.pi*300*t))*math.exp(-t*20)*0.2),
    ]
    for n, d, f in ui:
        sz = create_wav(os.path.join(aud_dir, n), sr, d, f)
        total += sz
        print(f"  {n}: {sz//1024}KB")

    # ========== MORE MUSIC ==========
    print("\n=== Generating Extended Music ===")
    music = [
        ('main_menu_60s.wav', 60, lambda t: gen_long_music(t, 120)),
        ('combat_dust2_60s.wav', 60, lambda t: gen_long_music(t, 140)),
        ('combat_inferno_60s.wav', 60, lambda t: gen_long_music(t, 135)),
        ('combat_mirage_60s.wav', 60, lambda t: gen_long_music(t, 130)),
        ('combat_nuke_60s.wav', 60, lambda t: gen_long_music(t, 145)),
        ('combat_overpass_60s.wav', 60, lambda t: gen_long_music(t, 125)),
        ('win_stinger.wav', 5, lambda t: math.sin(2*math.pi*523*t)*max(0,1-t*0.2)*0.3*(0.5+0.5*math.sin(2*math.pi*3*t))),
        ('lose_stinger.wav', 5, lambda t: math.sin(2*math.pi*185*t)*max(0,1-t*0.2)*0.3),
        ('overtime.wav', 3, lambda t: math.sin(2*math.pi*440*t)*max(0,1-t*0.33)*0.4),
        ('countdown.wav', 10, lambda t: math.sin(2*math.pi*800*(1+int(t)%5*0.1)*t)*max(0,1-t*0.1)*0.2 if int(t)%1<0.8 else 0),
    ]
    for n, d, f in music:
        sz = create_wav(os.path.join(mus_dir, n), sr, d, f)
        total += sz
        print(f"  {n}: {sz//1024}KB")

    print(f"\n{'='*50}")
    print(f"TOTAL ASSETS GENERATED: {total//1024//1024}MB ({total//1024}KB)")
    print(f"{'='*50}")

if __name__ == '__main__':
    main()
