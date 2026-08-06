#!/usr/bin/env python3
"""
post_instagram_daily.py
photos/ フォルダの写真を順番に1枚選び、アスペクト比を自動補正して
このリポジトリ自体を使って公開URLを作り、キャプションを生成してInstagramへ自動投稿する。

画像の公開方法について:
  以前はimgbb.com等の外部画像ホスティングサービスを使っていたが、
  Instagram側のサーバーがそれらのURLから画像を取得できず投稿に失敗するケースがあったため、
  このGitHubリポジトリ自体(raw.githubusercontent.com)を画像の公開先として使うように変更した。
  毎回ユニークなファイル名で public/ フォルダにコミット・pushし、そのURLをInstagramに渡す。

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
import time
import glob
import subprocess

from image_utils import fix_aspect_ratio

PHOTOS_DIR = "photos"
PUBLIC_DIR = "public"
STATE_FILE = "instagram_state.json"

# GITHUB_REPOSITORYはGitHub Actions実行時に自動で設定される環境変数（例: "owner/repo"）
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "TOMOAKIKITAMURA/yuki-automation")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_index": -1}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def publish_image_to_repo(fixed_path):
    """加工済み画像をリポジトリのpublic/フォルダにユニークなファイル名でコミット・pushし、
    raw.githubusercontent.com経由の公開URLを返す。"""
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    # 古い画像を削除してリポジトリが肥大化しないようにする
    for old in glob.glob(os.path.join(PUBLIC_DIR, "*.jpg")):
        os.remove(old)

    filename = f"ig_{int(time.time())}.jpg"
    dest_path = os.path.join(PUBLIC_DIR, filename)
    with open(fixed_path, "rb") as src, open(dest_path, "wb") as dst:
        dst.write(src.read())

    subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=True)
    subprocess.run(
        ["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"],
        check=True,
    )
    subprocess.run(["git", "add", "-A", PUBLIC_DIR], check=True)
    subprocess.run(["git", "commit", "-m", f"Publish {filename} for Instagram"], check=True)
    subprocess.run(["git", "push"], check=True)

    url = f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/{PUBLIC_DIR}/{filename}"
    print(f"公開URL: {url}")
    return url


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

    fixed_path = "/tmp/ig_fixed.jpg"
    fix_aspect_ratio(photo_path, fixed_path)
    image_url = publish_image_to_repo(fixed_path)

    # pushしたファイルがInstagram側からすぐ取得できるよう少し待つ
    time.sleep(10)

    caption_result = subprocess.run(
        ["python3", "-u", "generate_ig_caption.py"],
        capture_output=True, text=True, check=True, timeout=90,
    )
    caption = caption_result.stdout.strip()
    print("--- 生成されたキャプション ---")
    print(caption)

    caption_file = "ig_caption.txt"
    with open(caption_file, "w", encoding="utf-8") as f:
        f.write(caption)

    subprocess.run(
        [
            "python3", "-u", "post_to_instagram.py",
            "--caption-file", caption_file,
            "--image-url", image_url,
        ],
        check=True, timeout=180,
    )

    state["last_index"] = index
    save_state(state)
    print("状態を更新しました:", state)


if __name__ == "__main__":
    main()
