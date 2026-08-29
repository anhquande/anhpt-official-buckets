from pathlib import Path
import math, struct, zlib

W, H = 1000, 720
BG = (250, 250, 248)
INK = (25, 38, 54)
GI = (242, 244, 246)
BELT = (20, 22, 24)
SKIN = (211, 165, 128)
ACCENT = (35, 104, 190)
GRID = (215, 220, 225)
pixels = [[BG for _ in range(W)] for _ in range(H)]

def setpx(x,y,c):
    if 0 <= x < W and 0 <= y < H: pixels[y][x]=c

def line(x0,y0,x1,y1,c=INK,width=4):
    dx=abs(x1-x0); sx=1 if x0<x1 else -1; dy=-abs(y1-y0); sy=1 if y0<y1 else -1; err=dx+dy
    while True:
        for ox in range(-width//2,width//2+1):
            for oy in range(-width//2,width//2+1): setpx(x0+ox,y0+oy,c)
        if x0==x1 and y0==y1: break
        e2=2*err
        if e2>=dy: err+=dy; x0+=sx
        if e2<=dx: err+=dx; y0+=sy

def disk(cx,cy,r,c):
    for y in range(cy-r,cy+r+1):
        for x in range(cx-r,cx+r+1):
            if (x-cx)**2+(y-cy)**2 <= r*r: setpx(x,y,c)

def rect(x0,y0,x1,y1,c):
    for y in range(y0,y1):
        for x in range(x0,x1): setpx(x,y,c)

def arrow(x0,y0,x1,y1):
    line(x0,y0,x1,y1,ACCENT,4); a=math.atan2(y1-y0,x1-x0)
    for d in (2.55,-2.55): line(x1,y1,int(x1+15*math.cos(a+d)),int(y1+15*math.sin(a+d)),ACCENT,4)

def person(cx,cy,pose,face=1):
    # stylised karate practitioner: head, gi torso, black belt, arms and zenkutsu-dachi legs
    disk(cx,cy-48,11,SKIN)
    # gi jacket
    for yy in range(cy-35,cy+8):
        half=max(12,20-(yy-(cy-35))//7)
        rect(cx-half,yy,cx+half,yy+1,GI)
    line(cx-18,cy-30,cx+15,cy+3,INK,2); line(cx+18,cy-30,cx-7,cy+4,INK,2)
    rect(cx-21,cy+1,cx+22,cy+7,BELT)
    # legs: wide front stance, direction alternates
    if face >= 0:
        line(cx-8,cy+8,cx-35,cy+48,GI,13); line(cx+8,cy+8,cx+42,cy+43,GI,13)
        line(cx-38,cy+50,cx-20,cy+50,INK,4); line(cx+38,cy+46,cx+53,cy+46,INK,4)
    else:
        line(cx+8,cy+8,cx+35,cy+48,GI,13); line(cx-8,cy+8,cx-42,cy+43,GI,13)
        line(cx+20,cy+50,cx+38,cy+50,INK,4); line(cx-53,cy+46,cx-38,cy+46,INK,4)
    # technique pose: block or punch; alternating side makes transitions visible
    if pose % 3 == 0: # gedan barai
        line(cx-12,cy-23,cx+10,cy-8,GI,11); line(cx+10,cy-8,cx+face*34,cy+20,GI,11)
        line(cx+12,cy-20,cx-8,cy-5,GI,10)
    elif pose % 3 == 1: # oi-zuki
        line(cx-12,cy-20,cx+face*48,cy-18,GI,11); disk(cx+face*50,cy-18,6,SKIN)
        line(cx+12,cy-20,cx-6,cy-5,GI,10)
    else: # age uke
        line(cx-10,cy-20,cx+face*18,cy-52,GI,11); line(cx+face*18,cy-52,cx+face*38,cy-48,GI,10)
        line(cx+10,cy-20,cx-7,cy-5,GI,10)

def number(n,cx,cy):
    # compact seven-segment digits, avoiding font dependencies in CI
    seg={0:'abcedf',1:'bc',2:'abdeg',3:'abcdg',4:'bcfg',5:'acdfg',6:'acdefg',7:'abc',8:'abcdefg',9:'abcdfg'}
    maps={'a':((0,0),(10,0)),'b':((10,0),(10,10)),'c':((10,10),(10,20)),'d':((0,20),(10,20)),'e':((0,10),(0,20)),'f':((0,0),(0,10)),'g':((0,10),(10,10))}
    s=str(n); start=cx-(len(s)*15)//2
    for i,ch in enumerate(s):
        for k in seg[int(ch)]:
            a,b=maps[k]; line(start+i*15+a[0],cy+a[1],start+i*15+b[0],cy+b[1],ACCENT,2)

# 20 movement panels: each has a human karate pose plus a direction arrow.
cols, rows = 5, 4
cw, ch = W//cols, 165
for n in range(1,21):
    col=(n-1)%cols; row=(n-1)//cols; x0=col*cw; y0=35+row*ch
    if col: line(x0,y0-25,x0,y0+ch-15,GRID,1)
    if row: line(x0,y0-25,x0+cw,y0-25,GRID,1)
    cx=x0+cw//2; cy=y0+75
    # turn orientation at major direction changes; otherwise alternate technique side
    face=-1 if n in (3,4,9,10,17,18) else 1
    person(cx,cy,n,face)
    number(n,x0+22,y0-15)
    # arrows communicate the transition without replacing the human demonstration
    if n in (3,9,17): arrow(cx+60,cy+5,cx+25,cy-20)
    elif n in (5,11,19): arrow(cx-60,cy+5,cx-25,cy-20)
    else: arrow(cx-55,cy+58,cx+55,cy+58)

# title underline / orientation cue
line(35,20,W-35,20,ACCENT,5)
arrow(W//2,H-22,W//2,H-60)

raw=bytearray()
for row in pixels:
    raw.append(0)
    for r,g,b in row: raw.extend((r,g,b))
def chunk(tag,data): return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
png=b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',W,H,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(bytes(raw),9))+chunk(b'IEND',b'')
out=Path(__file__).parent/'media'/'heian-shodan-flow.png'; out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(png); print(out)
