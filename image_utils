"""
image_utils.py
Instagram投稿用の画像処理ユーティリティ。

- fix_aspect_ratio: Instagramが許容する縦横比(4:5〜1.91:1)に収まるよう、中央を基準に自動でクロップする
- upload_to_catbox: catbox.moeに画像をアップロードし、Instagram投稿に必要な「公開URL」を取得する
  （Instagram Graph APIはローカルファイルを直接受け付けず、公開URLの取得が必須のため）
"""

import subprocess

from PIL import Image

MIN_RATIO = 0.8    # 4:5（縦長の最大）
MAX_RATIO = 1.91   # 1.91:1（横長の最大）


def fix_aspect_ratio(input_path, output_path):
    img = Image.open(input_path).convert("RGB")
    w, h = img.size
    ratio = w / h

    if ratio < MIN_RATIO:
        # 縦長すぎる場合: 高さを詰めて縦横比を4:5に近づける
        new_h = int(w / MIN_RATIO)
        top = (h - new_h) // 2
        img = img.crop((0, top, w, top + new_h))
    elif ratio > MAX_RATIO:
        # 横長すぎる場合: 幅を詰めて縦横比を1.91:1に近づける
        new_w = int(h * MAX_RATIO)
        left = (w - new_w) // 2
        img = img.crop((left, 0, left + new_w, h))

    img.save(output_path, "JPEG", quality=90)
    return output_path


def upload_to_catbox(file_path):
    result = subprocess.run(
        [
            "curl", "-s",
            "-F", "reqtype=fileupload",
            "-F", f"fileToUpload=@{file_path}",
            "https://catbox.moe/user/api.php",
        ],
        capture_output=True, text=True, timeout=60,
    )
    url = result.stdout.strip()
    if not url.startswith("http"):
        raise RuntimeError(f"catbox.moeへのアップロードに失敗しました: {url}")
    return url
