from pathlib import Path
import struct, zlib

W, H = 1000, 720
BG = (247, 248, 250)
INK = (35, 42, 52)
ACCENT = (64, 110, 230)
SKIN = (220, 174, 135)
SHIRT = (90, 145, 235)
SHORTS = (50, 58, 70)
MAT = (225, 230, 238)
GREEN = (80, 170, 120)


def canvas():
    return [[BG for _ in range(W)] for _ in range(H)]


def setpx(p, x, y, c):
    if 0 <= x < W and 0 <= y < H:
        p[y][x] = c


def line(p, x0, y0, x1, y1, c=INK, width=5):
    dx = abs(x1-x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1-y0); sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        for ox in range(-width//2, width//2+1):
            for oy in range(-width//2, width//2+1):
                setpx(p, x0+ox, y0+oy, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2*err
        if e2 >= dy:
            err += dy; x0 += sx
        if e2 <= dx:
            err += dx; y0 += sy


def rect(p, x0, y0, x1, y1, c):
    for y in range(max(0,y0), min(H,y1)):
        for x in range(max(0,x0), min(W,x1)):
            p[y][x] = c


def disk(p, cx, cy, r, c):
    rr = r*r
    for y in range(cy-r, cy+r+1):
        for x in range(cx-r, cx+r+1):
            if (x-cx)*(x-cx)+(y-cy)*(y-cy) <= rr:
                setpx(p, x, y, c)


def person_standing(p, cx, cy):
    disk(p, cx, cy-170, 28, SKIN)
    line(p, cx, cy-140, cx, cy-30, SHIRT, 38)
    line(p, cx, cy-120, cx-65, cy-55, SKIN, 18)
    line(p, cx, cy-120, cx+65, cy-55, SKIN, 18)
    line(p, cx-14, cy-30, cx-38, cy+95, SHORTS, 22)
    line(p, cx+14, cy-30, cx+38, cy+95, SHORTS, 22)


def person_squat(p, cx, cy):
    disk(p, cx, cy-145, 27, SKIN)
    line(p, cx, cy-118, cx-8, cy-35, SHIRT, 38)
    line(p, cx-8, cy-80, cx-80, cy-72, SKIN, 18)
    line(p, cx-8, cy-80, cx+80, cy-72, SKIN, 18)
    line(p, cx-8, cy-35, cx-78, cy+15, SHORTS, 24)
    line(p, cx-78, cy+15, cx-132, cy+85, SHORTS, 24)
    line(p, cx-8, cy-35, cx+78, cy+15, SHORTS, 24)
    line(p, cx+78, cy+15, cx+132, cy+85, SHORTS, 24)
    line(p, cx-145, cy+88, cx-105, cy+88, INK, 7)
    line(p, cx+105, cy+88, cx+145, cy+88, INK, 7)


def person_plank(p, cx, cy):
    disk(p, cx-175, cy-55, 24, SKIN)
    line(p, cx-145, cy-35, cx+110, cy+15, SHIRT, 34)
    line(p, cx+95, cy+10, cx+210, cy+48, SHORTS, 28)
    line(p, cx-100, cy-20, cx-145, cy+95, SKIN, 18)
    line(p, cx-20, cy-5, cx-45, cy+95, SKIN, 18)
    line(p, cx+205, cy+45, cx+250, cy+78, INK, 12)


def save_png(path, p):
    raw = bytearray()
    for row in p:
        raw.append(0)
        for r,g,b in row:
            raw.extend((r,g,b))
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag+data) & 0xffffffff)
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)) + chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b'')
    path.write_bytes(png)


out = Path(__file__).parent / 'media'
out.mkdir(parents=True, exist_ok=True)

# Welcome
p = canvas()
rect(p, 80, 560, 920, 590, MAT)
person_standing(p, 500, 455)
disk(p, 500, 120, 42, ACCENT)
line(p, 470, 120, 492, 145, BG, 8)
line(p, 492, 145, 535, 92, BG, 8)
save_png(out/'welcome.png', p)

# Squat
p = canvas()
rect(p, 70, 565, 930, 595, MAT)
person_squat(p, 500, 450)
line(p, 260, 540, 740, 540, GREEN, 7)
save_png(out/'squat.png', p)

# Rest
p = canvas()
rect(p, 80, 560, 920, 590, MAT)
person_standing(p, 500, 455)
disk(p, 745, 190, 52, GREEN)
line(p, 745, 158, 745, 194, BG, 8)
line(p, 745, 194, 772, 210, BG, 8)
save_png(out/'rest.png', p)

# High plank
p = canvas()
rect(p, 70, 545, 930, 585, MAT)
person_plank(p, 470, 430)
line(p, 285, 376, 685, 455, GREEN, 6)
save_png(out/'high-plank.png', p)

for f in sorted(out.glob('*.png')):
    print(f)
