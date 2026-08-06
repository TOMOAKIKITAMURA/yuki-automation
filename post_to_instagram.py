#!/usr/bin/env python3
"""
post_to_instagram.py
yukiさんのInstagramアカウントへの自動投稿スクリプト（Instagram API with Instagram Login）

事前準備:
  pip install requests

必要な環境変数:
  IG_ACCESS_TOKEN   長期アクセストークン（60日間有効。exchange_token.pyで取得）
  IG_USER_ID        投稿先InstagramアカウントのユーザーID（数値）

重要な制約:
  - 画像/動画はインターネット上の「公開URL」である必要があります（Instagram側がそのURLを
    取得しにいくため）。ローカルファイルを直接アップロードすることはできません。
  - 画像はJPEGのみサポート
  - 画像/動画の縦横比は 4:5（縦長の最大）〜 1.91:1（横長の最大）の範囲である必要があります。
    範囲外だと "The aspect ratio is not supported" エラーになります。
  - 投稿上限は24時間で100件（カルーセルは1件扱い）

使い方:
  # 画像1枚
  python3 post_to_instagram.py --caption "本日のコーデ" --image-url "https://example.com/photo.jpg"

  # 動画（リール）
  python3 post_to_instagram.py --caption "今日のvlog" --video-url "https://example.com/video.mp4" --reels

  # カルーセル（画像/動画を複数、最大10件）
  python3 post_to_instagram.py --caption "本日の3枚" --image-url "https://example.com/1.jpg" "https://example.com/2.jpg" "https://example.com/3.jpg"

  # キャプションをファイルから読み込み
  python3 post_to_instagram.py --caption-file caption.txt --image-url "https://example.com/photo.jpg"
"""

import os
import sys
import time
import socket
import argparse
import logging

import requests
import urllib3.util.connection as urllib3_cn

# GitHub Actionsのようなクラウド実行環境では、IPv6での接続がうまく通らず、
# タイムアウトするまで（今回のケースでは180秒）応答が返ってこず固まってしまうことがある。
# これを避けるため、通信を強制的にIPv4で行うようにする。
def _allowed_gai_family():
    return socket.AF_INET


urllib3_cn.allowed_gai_family = _allowed_gai_family

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("post_to_instagram")

API_VERSION = "v24.0"
HOST = "https://graph.instagram.com"

REQUIRED_ENV_VARS = ["IG_ACCESS_TOKEN", "IG_USER_ID"]


def load_credentials():
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        log.error("環境変数が不足しています: %s", ", ".join(missing))
        sys.exit(1)
    return os.environ["IG_ACCESS_TOKEN"], os.environ["IG_USER_ID"]


def create_container(access_token, ig_user_id, caption=None, image_url=None, video_url=None,
                      media_type=None, is_carousel_item=False):
    url = f"{HOST}/{API_VERSION}/{ig_user_id}/media"
    payload = {"access_token": access_token}
    if caption:
        payload["caption"] = caption
    if image_url:
        payload["image_url"] = image_url
    if video_url:
        payload["video_url"] = video_url
    if media_type:
        payload["media_type"] = media_type
    if is_carousel_item:
        payload["is_carousel_item"] = "true"

    resp = requests.post(url, data=payload, timeout=60)
    data = resp.json()
    if resp.status_code != 200:
        log.error("コンテナ作成に失敗しました: %s", data)
        sys.exit(1)
    log.info("コンテナ作成: %s", data["id"])
    return data["id"]


def create_carousel_container(access_token, ig_user_id, caption, child_ids):
    url = f"{HOST}/{API_VERSION}/{ig_user_id}/media"
    payload = {
        "access_token": access_token,
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
    }
    if caption:
        payload["caption"] = caption
    resp = requests.post(url, data=payload, timeout=60)
    data = resp.json()
    if resp.status_code != 200:
        log.error("カルーセルコンテナ作成に失敗しました: %s", data)
        sys.exit(1)
    log.info("カルーセルコンテナ作成: %s", data["id"])
    return data["id"]


def wait_until_ready(access_token, container_id, timeout_sec=300, interval_sec=10):
    """コンテナがFINISHEDになるまで待つ（動画は時間がかかるが、画像でも数秒かかることがある）"""
    url = f"{HOST}/{API_VERSION}/{container_id}"
    elapsed = 0
    while elapsed < timeout_sec:
        resp = requests.get(url, params={"fields": "status_code", "access_token": access_token}, timeout=30)
        data = resp.json()
        status = data.get("status_code")
        log.info("コンテナステータス: %s", status)
        if status == "FINISHED":
            return True
        if status in ("ERROR", "EXPIRED"):
            log.error("コンテナ処理に失敗しました: %s", data)
            sys.exit(1)
        time.sleep(interval_sec)
        elapsed += interval_sec
    log.error("タイムアウトしました。ステータス確認を続けてください: %s", container_id)
    sys.exit(1)


def publish(access_token, ig_user_id, creation_id, max_retries=5, retry_interval_sec=5):
    """公開する。作成直後は「Media ID is not available」(code 9007)になることがあるため、
    その場合は少し待ってリトライする（画像でも数秒の処理時間が必要な場合がある）。"""
    url = f"{HOST}/{API_VERSION}/{ig_user_id}/media_publish"
    for attempt in range(1, max_retries + 1):
        resp = requests.post(url, data={"access_token": access_token, "creation_id": creation_id}, timeout=60)
        data = resp.json()
        if resp.status_code == 200:
            log.info("投稿成功: media id = %s", data["id"])
            return data["id"]

        error_code = data.get("error", {}).get("code")
        if error_code == 9007 and attempt < max_retries:
            log.info("メディアがまだ準備できていません。%s秒待って再試行します（%s/%s）", retry_interval_sec, attempt, max_retries)
            time.sleep(retry_interval_sec)
            continue

        log.error("公開に失敗しました: %s", data)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Instagramへ自動投稿する")
    parser.add_argument("--caption", help="キャプション本文")
    parser.add_argument("--caption-file", help="キャプションが書かれたテキストファイルのパス")
    parser.add_argument("--image-url", nargs="*", default=[], help="公開画像URL（複数指定でカルーセル）")
    parser.add_argument("--video-url", help="公開動画URL")
    parser.add_argument("--reels", action="store_true", help="動画をリールとして投稿する")
    args = parser.parse_args()

    caption = args.caption
    if args.caption_file:
        with open(args.caption_file, "r", encoding="utf-8") as f:
            caption = f.read().strip()

    access_token, ig_user_id = load_credentials()

    if args.video_url:
        media_type = "REELS" if args.reels else "VIDEO"
        container_id = create_container(
            access_token, ig_user_id, caption=caption, video_url=args.video_url, media_type=media_type
        )
        wait_until_ready(access_token, container_id)
        publish(access_token, ig_user_id, container_id)

    elif len(args.image_url) == 1:
        container_id = create_container(access_token, ig_user_id, caption=caption, image_url=args.image_url[0])
        publish(access_token, ig_user_id, container_id)

    elif len(args.image_url) > 1:
        child_ids = []
        for url in args.image_url:
            cid = create_container(access_token, ig_user_id, image_url=url, is_carousel_item=True)
            child_ids.append(cid)
        carousel_id = create_carousel_container(access_token, ig_user_id, caption, child_ids)
        publish(access_token, ig_user_id, carousel_id)

    else:
        parser.error("--image-url か --video-url のどちらかを指定してください")


if __name__ == "__main__":
    main()
