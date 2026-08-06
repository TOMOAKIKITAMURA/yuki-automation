#!/usr/bin/env python3
"""
post_instagram_daily.py
photos/ フォルダの写真を順番に1枚選び、アスペクト比を自動補正してアップロードし、
キャプションを生成してInstagramへ自動投稿する。

投稿済みの位置は instagram_state.json に記録し、次回はその続きから投稿する
（フォルダの最後まで行ったら最初に戻る）。

必要な環境変数:
  ANTHROPIC_API_KEY, IG_ACCESS_TOKEN, IG_USER_ID

事前準備:
  photos/ フォルダに投稿したい画像(.jpg, .jpeg, .png)を入れておくこと
"""

import os
import sys
import json
import subprocess
import tempfile

from image_utils import fix_aspect_ratio, upload_to_catbox

PHOTOS_DIR = "photos"
STATE_FILE = "instagram_state.json"


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_index": -1}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def main():
    if not os.path.isdir(PHOTOS_DIR):
        print(f"{PHOTOS_DIR}/ フォルダが見つかりません。", file=sys.stderr)
        sys.exit(1)

    photos = sorted(
        f for f in os.listdir(PHOTOS_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    if not photos:
        print(f"{PHOTOS_DIR}/ に画像がありません。写真を追加してください。", file=sys.stderr)
        sys.exit(1)

    state = load_state()
    index = (state.get("last_index", -1) + 1) % len(photos)
    photo_path = os.path.join(PHOTOS_DIR, photos[index])
    print(f"選択された写真: {photo_path} ({index + 1}/{len(photos)})")

    with tempfile.TemporaryDirectory() as tmp:
        fixed_path = os.path.join(tmp, "fixed.jpg")
        fix_aspect_ratio(photo_path, fixed_path)
        image_url = upload_to_catbox(fixed_path)
        print(f"公開URL: {image_url}")

    caption_result = subprocess.run(
        ["python3", "generate_ig_caption.py"],
        capture_output=True, text=True, check=True,
    )
    caption = caption_result.stdout.strip()
    print("--- 生成されたキャプション ---")
    print(caption)

    caption_file = "ig_caption.txt"
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(caption)

    subprocess.run(
        [
            "python3", "post_to_instagram.py",
            "--caption-file", caption_file,
            "--image-url", image_url,
        ],
        check=True,
    )

    state["last_index"] = index
    save_state(state)
    print("状態を更新しました:", state)


if __name__ == "__main__":
    main()
