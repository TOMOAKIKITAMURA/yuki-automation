import argparse, json, subprocess, tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

def sh(cmd):
    subprocess.run(cmd, check=True)

def find_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None

def cover_crop(src, dst, W, H):
    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    scale = max(W/sw, H/sh)
    nw, nh = round(sw*scale), round(sh*scale)
    im = im.resize((nw, nh), Image.LANCZOS)
    left = max(0, (nw-W)//2)
    top = max(0, (nh-H)//2)
    im.crop((left, top, left+W, top+H)).save(dst, quality=96)

def make_overlay(text, dst, style, W, H):
    img = Image.new("RGBA", (W,H), (0,0,0,0))
    draw = ImageDraw.Draw(img)

    fp = find_font()
    fs = int(style.get("font_size", 58))
    font = ImageFont.truetype(fp, fs) if fp else ImageFont.load_default()

    mx = int(style.get("margin_x", 78))
    mb = int(style.get("margin_bottom", 250))
    gap = int(style.get("line_gap", 18))
    fill = tuple(style.get("color", [246,242,234,255]))

    lines = (text or "").split("\n")
    heights=[]
    for ln in lines:
        bbox = draw.textbbox((0,0), ln, font=font)
        heights.append(max(fs, bbox[3]-bbox[1]))
    total = sum(heights) + gap*max(0,len(lines)-1)

    y = H - mb - total
    for ln,h in zip(lines,heights):
        if style.get("shadow", True):
            draw.text((mx+2,y+3), ln, font=font, fill=(0,0,0,95))
        draw.text((mx,y), ln, font=font, fill=fill)
        y += h+gap
    img.save(dst)

def motion_expr(kind):
    # subtle, irregular movements; intentionally restrained
    if kind == "push_in":
        return "z='min(1.045,1+on*0.00055)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if kind == "pull_out":
        return "z='max(1.0,1.045-on*0.00055)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
    if kind == "pan_right":
        return "z='1.025':x='(iw-iw/zoom)*on/(duration*30)':y='ih/2-(ih/zoom/2)'"
    if kind == "pan_left":
        return "z='1.025':x='(iw-iw/zoom)*(1-on/(duration*30))':y='ih/2-(ih/zoom/2)'"
    return "z='1.0':x='0':y='0'"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output", default="output/yuki_reel_v2.mp4")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    W = cfg.get("output",{}).get("width",1080)
    H = cfg.get("output",{}).get("height",1920)
    FPS = cfg.get("output",{}).get("fps",30)
    grain = int(cfg.get("grain",4))
    vignette = float(cfg.get("vignette",0.12))

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        pieces=[]

        for idx,clip in enumerate(cfg["clips"],1):
            still = td/f"{idx:02d}.jpg"
            ov = td/f"{idx:02d}.png"
            part = td/f"{idx:02d}.mp4"
            cover_crop(clip["image"], still, W, H)
            make_overlay(clip.get("text",""), ov, cfg.get("text_style",{}), W, H)

            dur=float(clip.get("duration",2.0))
            frames=max(1, round(dur*FPS))
            motion=clip.get("motion","hold")
            me = motion_expr(motion).replace("duration", str(dur))

            # Text appears a little after the image, fades in fast, fades out before cut.
            fade_in=0.12
            fade_out=max(fade_in+0.1, dur-0.18)

            fc = (
                f"[0:v]zoompan={me}:d={frames}:s={W}x{H}:fps={FPS},"
                f"noise=alls={grain}:allf=t+u,"
                f"vignette=PI/{max(2, int(1/vignette))}[bg];"
                f"[1:v]format=rgba,fade=t=in:st={fade_in}:d=0.18:alpha=1,"
                f"fade=t=out:st={fade_out}:d=0.16:alpha=1[txt];"
                f"[bg][txt]overlay=0:0:format=auto[v]"
            )

            sh([
                "ffmpeg","-y",
                "-loop","1","-i",str(still),
                "-loop","1","-i",str(ov),
                "-filter_complex",fc,
                "-map","[v]",
                "-t",str(dur),
                "-r",str(FPS),
                "-pix_fmt","yuv420p",
                "-c:v","libx264",
                "-preset","medium",
                "-crf","18",
                str(part)
            ])
            pieces.append(part)

        concat=td/"concat.txt"
        concat.write_text("\n".join(f"file '{p.as_posix()}'" for p in pieces), encoding="utf-8")

        sh([
            "ffmpeg","-y","-f","concat","-safe","0","-i",str(concat),
            "-c","copy",args.output
        ])

    print(args.output)

if __name__ == "__main__":
    main()
