from pathlib import Path
import struct, zlib

W, H = 900, 600
BG = (255, 255, 255)
FG = (22, 48, 76)
ACCENT = (36, 97, 176)

pixels = [[BG for _ in range(W)] for _ in range(H)]

def setpx(x, y, c=FG):
    if 0 <= x < W and 0 <= y < H:
        pixels[y][x] = c

def line(x0, y0, x1, y1, c=FG, width=5):
    dx = abs(x1-x0); sx = 1 if x0 < x1 else -1
    dy = -abs(y1-y0); sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        for ox in range(-width//2, width//2+1):
            for oy in range(-width//2, width//2+1): setpx(x0+ox, y0+oy, c)
        if x0 == x1 and y0 == y1: break
        e2 = 2*err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy

def circle(cx, cy, r, c=ACCENT):
    for y in range(cy-r, cy+r+1):
        for x in range(cx-r, cx+r+1):
            if (x-cx)**2 + (y-cy)**2 <= r*r: setpx(x,y,c)

def arrow(a, b):
    x0,y0=a; x1,y1=b
    line(x0,y0,x1,y1,FG,7)
    import math
    ang=math.atan2(y1-y0,x1-x0)
    for d in (2.55,-2.55):
        line(x1,y1,int(x1+24*math.cos(ang+d)),int(y1+24*math.sin(ang+d)),FG,7)

# simplified Heian Shodan embusen focused on direction changes
pts=[(170,500),(170,390),(300,390),(170,390),(170,260),(170,110),(450,110),(730,110),(730,260),(730,390),(600,390),(730,390),(730,500),(450,500),(170,500)]
for a,b in zip(pts,pts[1:]): arrow(a,b)
for p in pts: circle(*p,12)

# small orientation marks
line(450,80,450,45,ACCENT,5); arrow((450,80),(450,45))

raw = bytearray()
for row in pixels:
    raw.append(0)
    for r,g,b in row: raw.extend((r,g,b))

def chunk(tag, data):
    return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)

png = b'\x89PNG\r\n\x1a\n'
png += chunk(b'IHDR', struct.pack('>IIBBBBB',W,H,8,2,0,0,0))
png += chunk(b'IDAT', zlib.compress(bytes(raw),9))
png += chunk(b'IEND', b'')

out = Path(__file__).parent / 'media' / 'heian-shodan-flow.png'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes(png)
print(out)
