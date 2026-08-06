#!/usr/bin/env python3
"""
post_pr.py
指定したフォルダの画像とキャプションを使って、InstagramとXに同時にPR投稿する。
商品タイアップ(PR)投稿を今後も使い回せるように、汎用的な一発投稿スクリプトとして作成。

フォルダの中身（例: pr_posts/2026-08-06-amel-blouse/）:
  photo1.jpg, photo2.jpg, ... (画像。1〜10枚、Instagramはカルーセルに、Xは最大4枚まで使われる)
  caption_ig.txt (Instagram用キャプション)
  caption_x.txt  (X用キャプション。280文字以内を目安に)

必要な環境変数:
  IG_ACCESS_TOKEN, IG_USER_ID (Instagram投稿用)
  X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_SECRET (X投稿用)

使い方:
  python3 post_pr.py --folder pr_posts/2026-08-06-amel-blouse
"""

import os
import sys
import glob
import argparse
import subprocess
from urllib.parse import quote

# GITHUB_REPOSITORYはGitHub Actions実行時に自動で設定される環境変数（例: "owner/repo"）
GITHUB_REPOSITORY = os.environ.get("GITHUB_REPOSITORY", "TOMOAKIKITAMURA/yuki-automation")


def main():
    parser = argparse.ArgumentParser(description="指定フォルダの画像・キャプションでInstagramとXに投稿する")
    parser.add_argument("--folder", required=True, help="画像とキャプションが入っているフォルダのパス")
    args = parser.parse_args()

    folder = args.folder
    if not os.path.isdir(folder):
        print(f"{folder} フォルダが見つかりません。", file=sys.stderr)
        sys.exit(1)

    images = sorted(
        f for f in glob.glob(os.path.join(folder, "*"))
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
    if not images:
        print(f"{folder} に画像がありません。", file=sys.stderr)
        sys.exit(1)

    caption_ig = os.path.join(folder, "caption_ig.txt")
    caption_x = os.path.join(folder, "caption_x.txt")

    if not os.path.exists(caption_ig):
        print(f"{caption_ig} が見つかりません。", file=sys.stderr)
        sys.exit(1)
    if not os.path.exists(caption_x):
        print(f"{caption_x} が見つかりません。", file=sys.stderr)
        sys.exit(1)

    # --- Instagram: raw.githubusercontent.com経由の公開URLを使う ---
    # (このリポジトリは公開設定にしているので、コミット済みのファイルはそのままURLでアクセスできる)
    # ファイル名に日本語やスペースが含まれていても正しいURLになるよう、quote()でエンコードする
    image_urls = [
        f"https://raw.githubusercontent.com/{GITHUB_REPOSITORY}/main/" + quote(img)
        for img in images
    ]
    print("=== Instagramに投稿します ===")
    print(image_urls)
    subprocess.run(
        [
            "python3", "-u", "post_to_instagram.py",
            "--caption-file", caption_ig,
            "--image-url", *image_urls,
        ],
        check=True, timeout=180,
    )

    # --- X: ローカルファイルをそのまま渡せる（最大4枚まで） ---
    print("=== Xに投稿します ===")
    x_images = images[:4]
    print(x_images)
    subprocess.run(
        [
            "python3", "-u", "post_to_x.py",
            "--text-file", caption_x,
            "--media", *x_images,
        ],
        check=True, timeout=120,
    )

    print("完了しました。")


if __name__ == "__main__":
    main()
