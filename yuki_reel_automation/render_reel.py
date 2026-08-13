import argparse, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

W,H,FPS = 1080,1920,30

def font_path():
    for p in [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
    ]:
        if Path(p).exists():
            return p
    return None

def fit(src, dst):
    im = Image.open(src).convert("RGB")
    sw,sh = im.size
    r = max(W/sw, H/sh)
    nw,nh = round(sw*r), round(sh*r)
    im = im.resize((nw,nh), Image.LANCZOS)
    l,t = (nw-W)//2,(nh-H)//2
    im.crop((l,t,l+W,t+H)).save(dst, quality=95)

def overlay(text, dst, style):
    im = Image.new("RGBA",(W,H),(0,0,0,0))
    d = ImageDraw.Draw(im)
    fp = font_path()
    fs = int(style.get("font_size",66))
    f = ImageFont.truetype(fp, fs) if fp else ImageFont.load_default()
    x,y = int(W*0.08), int(H*0.70)
    fill = tuple(style.get("color",[245,241,232,255]))
    gap = int(fs*0.35)
    for line in text.split("\n"):
        d.text((x,y), line, font=f, fill=fill)
        y += fs + gap
    im.save(dst)

def run(cmd):
    subprocess.run(cmd, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output", default="yuki_reel.mp4")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as td:
        parts=[]
        for i,c in enumerate(cfg["clips"],1):
            img=Path(td)/f"{i:02d}.jpg"
            ov=Path(td)/f"{i:02d}.png"
            out=Path(td)/f"{i:02d}.mp4"
            fit(c["image"], img)
            overlay(c.get("text",""), ov, cfg.get("text_style",{}))
            dur=float(c.get("duration",3))
            frames=max(1,round(dur*FPS))
            zoom=c.get("zoom","in")
            z="1.0" if zoom=="none" else ("max(1.0,1.06-on*0.0007)" if zoom=="out" else "min(1.06,1+on*0.0007)")
            filt=f"[0:v]zoompan=z='{z}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={FPS}[bg];[1:v]format=rgba[ov];[bg][ov]overlay=0:0[v]"
            run(["ffmpeg","-y","-loop","1","-i",str(img),"-loop","1","-i",str(ov),"-filter_complex",filt,"-map","[v]","-t",str(dur),"-r",str(FPS),"-pix_fmt","yuv420p","-c:v","libx264",str(out)])
            parts.append(out)

        concat=Path(td)/"concat.txt"
        concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in parts), encoding="utf-8")
        silent=Path(td)/"silent.mp4"
        run(["ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),"-c","copy",str(silent)])

        bgm=cfg.get("bgm","")
        if bgm and Path(bgm).exists():
            run(["ffmpeg","-y","-i",str(silent),"-stream_loop","-1","-i",bgm,"-filter_complex",f"[1:a]volume={cfg.get('bgm_volume',0.18)}[a]","-map","0:v","-map","[a]","-shortest","-c:v","copy","-c:a","aac",a.output])
        else:
            Path(a.output).write_bytes(silent.read_bytes())

if __name__=="__main__":
    main()
