"""
image_utils.py
Instagram投稿用の画像処理ユーティリティ。

- fix_aspect_ratio: Instagramが許容する縦横比(4:5〜1.91:1)に収まるよう、中央を基準に自動でクロップする
- upload_to_imgbb: imgbb.comに画像をアップロードし、Instagram投稿に必要な「公開URL」を取得する
  （Instagram Graph APIはローカルファイルを直接受け付けず、公開URLの取得が必須のため。
  catbox.moeはGitHub Actionsのようなデータセンターからのアップロードをブロックするため、
  APIキー方式のimgbb.comに変更した）
"""

import requests
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


def upload_to_imgbb(file_path, api_key):
    with open(file_path, "rb") as f:
        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            params={"key": api_key},
            files={"image": f},
            timeout=60,
        )
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"imgbbへのアップロードに失敗しました: {data}")
    return data["data"]["url"]
