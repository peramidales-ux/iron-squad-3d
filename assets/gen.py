#!/usr/bin/env python3
"""Fast asset generator for Iron Squad - textures + audio"""
import struct, zlib, math, random, os, hashlib

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

# Texture generators
def tex_concrete(x,y):
    n=fbm(x*0.02,y*0.02,5,42)*0.3; b=140+n*60
    return(b,b-5,b-10)
def tex_sand(x,y):
    n=fbm(x*0.015,y*0.015,4,123)*0.4; b=194+n*40
    return(b,b-20,b-50)
def tex_metal(x,y):
    n=fbm(x*0.04,y*0.01,3,77)*0.3; b=100+n*40; s=max(0,n*2)
    return(b+s*30,b+s*25,b+s*20)
def tex_wood(x,y):
    g=math.sin(y*0.15+fbm(x*0.05,y*0.005,3,55)*5)*20; b=120+g
    return(b+20,b-10,b-40)
def tex_brick(x,y):
    bx2=(x+(y//16)%2*16)%32; by=y%16
    if bx2<1 or by<1: return(180,175,165)
    n=fbm(x*0.05,y*0.05,2,33)*15; return(160+n,80+n*0.5,60+n*0.3)
def tex_dirt(x,y):
    n=fbm(x*0.02,y*0.02,5,99)*0.5; b=100+n*50
    return(b+20,b-10,b-30)
def tex_grass(x,y):
    n=fbm(x*0.03,y*0.03,4,200)*0.4; g=100+n*60
    return(g*0.4,g,g*0.3)
def tex_water(x,y):
    t=fbm(x*0.01,y*0.01,3,300)
    return(40+t*20,80+t*30,160+t*40)
def tex_asphalt(x,y):
    n=fbm(x*0.035,y*0.035,5,444)*0.25; b=60+n*30
    return(b,b,b+2)

# Audio generators
def snd_gunshot(t,f=200,d=0.08):
    if t>d*3: return 0
    return(math.exp(-t/d))*(random.uniform(-1,1)*0.5+math.sin(2*math.pi*f*t)*0.5)*0.7
def snd_explosion(t):
    if t>1: return 0
    return math.exp(-t*3)*(random.uniform(-1,1)*0.6+math.sin(2*math.pi*40*t)*0.5)*0.8
def snd_footstep(t):
    if t>0.15: return 0
    return math.exp(-t*30)*(random.uniform(-1,1)*0.3+math.sin(2*math.pi*100*t)*0.7)*0.4
def snd_ambient(t):
    return(math.sin(2*math.pi*0.1*t)*0.1+math.sin(2*math.pi*0.15*t)*0.08+math.sin(2*math.pi*0.07*t)*0.05)*0.3
def snd_music(t,bpm=128):
    b=t*bpm/60; kick=max(0,math.sin(2*math.pi*60*t)*math.exp(-(b%1)*8))*0.4
    hh=random.uniform(-1,1)*0.1*max(0,math.exp(-(b%0.5)*20)) if(b%0.5)<0.05 else 0
    bass=math.sin(2*math.pi*55*t)*0.15*(0.5+0.5*math.sin(2*math.pi*0.25*t))
    return max(-1,min(1,kick+hh+bass))

def main():
    total=0; sr=44100
    tex_dir=os.path.join(BASE,'textures')
    aud_dir=os.path.join(BASE,'audio')
    os.makedirs(tex_dir,exist_ok=True)
    os.makedirs(aud_dir,exist_ok=True)

    print("=== Generating 4K Textures ===")
    for name,func in [('concrete',tex_concrete),('sand',tex_sand),('metal',tex_metal),
                       ('wood',tex_wood),('brick',tex_brick),('dirt',tex_dirt),
                       ('grass',tex_grass),('water',tex_water),('asphalt',tex_asphalt)]:
        sz=create_png(2048,2048,func,os.path.join(tex_dir,f'{name}_diff.png'))
        total+=sz; print(f"  {name}_diff.png: {sz//1024}KB")

    # Normal maps (smaller)
    print("\n=== Generating Normal Maps ===")
    for name,func in [('concrete',tex_concrete),('sand',tex_sand),('metal',tex_metal),
                       ('wood',tex_wood),('brick',tex_brick),('dirt',tex_dirt),
                       ('grass',tex_grass),('water',tex_water),('asphalt',tex_asphalt)]:
        def nm(x,y,f=func):
            e=2; h0=sum(f(x,y)); hx=sum(f(x+e,y)); hy=sum(f(x,y+e))
            return(int(128+(h0-hx)/(e*3)*128),int(128+(h0-hy)/(e*3)*128),255)
        sz=create_png(1024,1024,nm,os.path.join(tex_dir,f'{name}_nrm.png'))
        total+=sz; print(f"  {name}_nrm.png: {sz//1024}KB")

    print("\n=== Generating Audio ===")
    guns=[('rifle.wav',0.08,200),('smg.wav',0.06,300),('pistol.wav',0.05,400),
          ('deagle.wav',0.1,150),('awp.wav',0.15,80),('shotgun.wav',0.12,120),
          ('sniper.wav',0.12,100),('mg.wav',0.07,250)]
    for n,d,f in guns:
        sz=create_wav(os.path.join(aud_dir,n),sr,0.5,lambda t,dd=d,ff=f:snd_gunshot(t,ff,dd))
        total+=sz; print(f"  {n}: {sz//1024}KB")

    effects=[('explosion.wav',1.5,snd_explosion),('hit.wav',0.2,lambda t:snd_gunshot(t,800,0.03)),
             ('reload.wav',0.8,lambda t:snd_footstep(t)*2),('footstep.wav',0.3,snd_footstep),
             ('death.wav',1.0,lambda t:snd_explosion(t)*0.5),
             ('headshot.wav',0.3,lambda t:snd_gunshot(t,1200,0.02)),
             ('round_start.wav',2.0,lambda t:math.sin(2*math.pi*440*t)*max(0,1-t)*0.3),
             ('round_end.wav',2.0,lambda t:math.sin(2*math.pi*330*t)*max(0,1-t*0.5)*0.3),
             ('buy.wav',0.3,lambda t:math.sin(2*math.pi*600*t)*max(0,1-t*4)*0.2),
             ('bomb_plant.wav',3.0,lambda t:math.sin(2*math.pi*200*t)*max(0,1-t*0.3)*0.3 if t<1 else math.sin(2*math.pi*400*(t-1))*max(0,1-(t-1)*0.5)*0.3),
             ('ambient_wind.wav',5.0,snd_ambient),
             ('ambient_battle.wav',5.0,lambda t:snd_ambient(t)+random.uniform(-0.05,0.05))]
    for n,d,f in effects:
        sz=create_wav(os.path.join(aud_dir,n),sr,d,f)
        total+=sz; print(f"  {n}: {sz//1024}KB")

    print("\n=== Generating Music ===")
    mus_dir=os.path.join(aud_dir,'music'); os.makedirs(mus_dir,exist_ok=True)
    music=[('menu_theme.wav',30,lambda t:math.sin(2*math.pi*[261,293,329,349,392,440,493,523][int(t*2)%8]*t)*0.1+math.sin(2*math.pi*130.81*t)*0.05*(0.5+0.5*math.sin(2*math.pi*0.2*t))),
           ('combat_1.wav',30,snd_music),('combat_2.wav',30,lambda t:snd_music(t,140)),
           ('victory.wav',10,lambda t:math.sin(2*math.pi*523.25*t)*max(0,1-t*0.1)*0.3*(0.5+0.5*math.sin(2*math.pi*2*t))),
           ('defeat.wav',10,lambda t:math.sin(2*math.pi*220*t)*max(0,1-t*0.1)*0.3)]
    for n,d,f in music:
        sz=create_wav(os.path.join(mus_dir,n),sr,d,f)
        total+=sz; print(f"  {n}: {sz//1024}KB")

    print(f"\n=== TOTAL: {total//1024//1024}MB ({total//1024}KB) ===")

if __name__=='__main__':
    main()
