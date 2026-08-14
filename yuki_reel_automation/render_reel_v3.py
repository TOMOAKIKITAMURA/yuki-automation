import argparse
import json
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def run(cmd):
    subprocess.run(cmd, check=True)


def find_font():
    candidates = [
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJKjp-Regular.otf",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W4.ttc",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return None


def cover_crop(src, dst, width, height):
    im = Image.open(src).convert("RGB")
    sw, sh = im.size
    scale = max(width / sw, height / sh)
    nw, nh = round(sw * scale), round(sh * scale)
    im = im.resize((nw, nh), Image.LANCZOS)
    left = max(0, (nw - width) // 2)
    top = max(0, (nh - height) // 2)
    im.crop((left, top, left + width, top + height)).save(dst, quality=96)


def text_block_size(draw, lines, font, line_gap):
    widths, heights = [], []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        widths.append(max(1, bbox[2] - bbox[0]))
        heights.append(max(1, bbox[3] - bbox[1]))
    total_h = sum(heights) + line_gap * max(0, len(lines) - 1)
    return max(widths or [1]), total_h, heights


def anchor_xy(position, block_w, block_h, width, height, mx, my):
    pos = position or "lower_left"

    if pos == "upper_left":
        return mx, my
    if pos == "upper_right":
        return width - mx - block_w, my
    if pos == "center_left":
        return mx, (height - block_h) // 2
    if pos == "center":
        return (width - block_w) // 2, (height - block_h) // 2
    if pos == "center_right":
        return width - mx - block_w, (height - block_h) // 2
    if pos == "lower_right":
        return width - mx - block_w, height - my - block_h

    return mx, height - my - block_h


def make_overlay(text, position, dst, style, width, height):
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if not text:
        img.save(dst)
        return

    draw = ImageDraw.Draw(img)
    fp = find_font()
    fs = int(style.get("font_size", 54))
    font = ImageFont.truetype(fp, fs) if fp else ImageFont.load_default()

    color = tuple(style.get("color", [246, 242, 234, 255]))
    shadow = tuple(style.get("shadow_color", [0, 0, 0, 90]))
    mx = int(style.get("margin_x", 78))
    my = int(style.get("margin_y", 170))
    gap = int(style.get("line_gap", 14))

    lines = text.split("\n")
    block_w, block_h, heights = text_block_size(draw, lines, font, gap)
    x, y = anchor_xy(position, block_w, block_h, width, height, mx, my)

    cy = y
    for line, h in zip(lines, heights):
        draw.text((x + 2, cy + 3), line, font=font, fill=shadow)
        draw.text((x, cy), line, font=font, fill=color)
        cy += h + gap

    img.save(dst)


def motion_filter(kind, duration, fps):
    frames = max(1, round(duration * fps))

    if kind == "push_in":
        return (
            f"zoompan=z='min(1.035,1+on*0.00045)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps={fps}"
        )

    if kind == "pull_out":
        return (
            f"zoompan=z='max(1.0,1.035-on*0.00045)':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps={fps}"
        )

    if kind == "pan_right":
        denom = max(1, frames - 1)
        return (
            f"zoompan=z='1.018':"
            f"x='(iw-iw/zoom)*on/{denom}':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps={fps}"
        )

    if kind == "pan_left":
        denom = max(1, frames - 1)
        return (
            f"zoompan=z='1.018':"
            f"x='(iw-iw/zoom)*(1-on/{denom})':"
            f"y='ih/2-(ih/zoom/2)':"
            f"d={frames}:s=1080x1920:fps={fps}"
        )

    return f"zoompan=z='1.0':x='0':y='0':d={frames}:s=1080x1920:fps={fps}"


def render_clip(clip, cfg, tmpdir, idx):
    width = int(cfg.get("output", {}).get("width", 1080))
    height = int(cfg.get("output", {}).get("height", 1920))
    fps = int(cfg.get("output", {}).get("fps", 30))
    duration = float(clip.get("duration", 2.0))
    grain = int(cfg.get("grain", 3))
    vignette = float(cfg.get("vignette", 0.08))

    still = tmpdir / f"{idx:02d}_still.jpg"
    overlay = tmpdir / f"{idx:02d}_overlay.png"
    output = tmpdir / f"{idx:02d}_clip.mp4"

    cover_crop(clip["image"], still, width, height)
    make_overlay(
        clip.get("text", ""),
        clip.get("text_position", "lower_left"),
        overlay,
        cfg.get("text_style", {}),
        width,
        height,
    )

    motion = motion_filter(clip.get("motion", "hold"), duration, fps)
    text_start = max(0.0, float(clip.get("text_start", 0.0)))
    text_end = max(text_start, float(clip.get("text_end", 0.0)))

    has_text = bool(clip.get("text", "").strip()) and text_end > text_start

    if has_text:
        fade_in_d = min(0.16, max(0.08, (text_end - text_start) / 5))
        fade_out_d = min(0.16, max(0.08, (text_end - text_start) / 5))
        fade_out_start = max(text_start + fade_in_d, text_end - fade_out_d)
        overlay_chain = (
            f"[1:v]format=rgba,"
            f"fade=t=in:st={text_start}:d={fade_in_d}:alpha=1,"
            f"fade=t=out:st={fade_out_start}:d={fade_out_d}:alpha=1[txt];"
            f"[bg][txt]overlay=0:0:enable='between(t,{text_start},{text_end})':format=auto[v]"
        )
    else:
        overlay_chain = "[0:v]null[v]"

    if has_text:
        fc = (
            f"[0:v]{motion},"
            f"noise=alls={grain}:allf=t+u,"
            f"vignette=PI/{max(10, int(1/max(vignette,0.01)))}[bg];"
            f"{overlay_chain}"
        )
        inputs = ["-loop", "1", "-i", str(still), "-loop", "1", "-i", str(overlay)]
    else:
        fc = (
            f"[0:v]{motion},"
            f"noise=alls={grain}:allf=t+u,"
            f"vignette=PI/{max(10, int(1/max(vignette,0.01)))}[v]"
        )
        inputs = ["-loop", "1", "-i", str(still)]

    run([
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", fc,
        "-map", "[v]",
        "-t", str(duration),
        "-r", str(fps),
        "-pix_fmt", "yuv420p",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        str(output),
    ])

    return output


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--output", default="output/yuki_reel_v3.mp4")
    args = ap.parse_args()

    cfg = json.loads(Path(args.config).read_text(encoding="utf-8"))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        tmpdir = Path(td)
        clips = []

        for idx, clip in enumerate(cfg["clips"], start=1):
            clips.append(render_clip(clip, cfg, tmpdir, idx))

        concat = tmpdir / "concat.txt"
        concat.write_text(
            "\n".join(f"file '{p.as_posix()}'" for p in clips),
            encoding="utf-8",
        )

        run([
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat),
            "-c", "copy",
            str(out),
        ])

    print(f"Done: {out}")


if __name__ == "__main__":
    main()
