#!/usr/bin/env python3
"""
post_to_threads.py
yukiさんのThreadsアカウントへの自動投稿スクリプト（Threads API）

事前準備:
  pip install requests

必要な環境変数:
  THREADS_ACCESS_TOKEN   長期アクセストークン
  THREADS_USER_ID        投稿先ThreadsアカウントのユーザーID（数値）

重要な制約:
  - 画像/動画はインターネット上の「公開URL」である必要があります（ローカルファイルは不可）
  - テキストは500文字まで
  - カルーセルは最大10件

使い方:
  # テキストのみ
  python3 post_to_threads.py --text "こんにちは"

  # 画像1枚
  python3 post_to_threads.py --text "本日の1枚" --image-url "https://example.com/photo.jpg"

  # カルーセル（画像を複数）
  python3 post_to_threads.py --text "本日の3枚" --image-url "https://example.com/1.jpg" "https://example.com/2.jpg"

  # キャプションをファイルから読み込み
  python3 post_to_threads.py --text-file caption.txt --image-url "https://example.com/photo.jpg"
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
# 応答が返ってこず固まってしまうことがあるため、通信を強制的にIPv4で行うようにする。
def _allowed_gai_family():
    return socket.AF_INET


urllib3_cn.allowed_gai_family = _allowed_gai_family

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("post_to_threads")

API_VERSION = "v1.0"
HOST = "https://graph.threads.net"

REQUIRED_ENV_VARS = ["THREADS_ACCESS_TOKEN", "THREADS_USER_ID"]


def load_credentials():
    missing = [v for v in REQUIRED_ENV_VARS if not os.environ.get(v)]
    if missing:
        log.error("環境変数が不足しています: %s", ", ".join(missing))
        sys.exit(1)
    return os.environ["THREADS_ACCESS_TOKEN"], os.environ["THREADS_USER_ID"]


def create_container(access_token, user_id, text=None, image_url=None, video_url=None,
                      is_carousel_item=False):
    url = f"{HOST}/{API_VERSION}/{user_id}/threads"
    payload = {"access_token": access_token}
    if image_url:
        payload["media_type"] = "IMAGE"
        payload["image_url"] = image_url
    elif video_url:
        payload["media_type"] = "VIDEO"
        payload["video_url"] = video_url
    else:
        payload["media_type"] = "TEXT"
    if text:
        payload["text"] = text
    if is_carousel_item:
        payload["is_carousel_item"] = "true"

    resp = requests.post(url, data=payload, timeout=60)
    data = resp.json()
    if resp.status_code != 200:
        log.error("コンテナ作成に失敗しました: %s", data)
        sys.exit(1)
    log.info("コンテナ作成: %s", data["id"])
    return data["id"]


def create_carousel_container(access_token, user_id, text, child_ids):
    url = f"{HOST}/{API_VERSION}/{user_id}/threads"
    payload = {
        "access_token": access_token,
        "media_type": "CAROUSEL",
        "children": ",".join(child_ids),
    }
    if text:
        payload["text"] = text
    resp = requests.post(url, data=payload, timeout=60)
    data = resp.json()
    if resp.status_code != 200:
        log.error("カルーセルコンテナ作成に失敗しました: %s", data)
        sys.exit(1)
    log.info("カルーセルコンテナ作成: %s", data["id"])
    return data["id"]


def publish(access_token, user_id, creation_id, max_retries=5, retry_interval_sec=5):
    """公開する。作成直後は準備ができていないことがあるため、少し待ってリトライする。"""
    url = f"{HOST}/{API_VERSION}/{user_id}/threads_publish"
    for attempt in range(1, max_retries + 1):
        resp = requests.post(
            url, data={"access_token": access_token, "creation_id": creation_id}, timeout=60
        )
        data = resp.json()
        if resp.status_code == 200:
            log.info("投稿成功: post id = %s", data["id"])
            return data["id"]

        if attempt < max_retries:
            log.info("公開できませんでした。%s秒待って再試行します（%s/%s）: %s",
                      retry_interval_sec, attempt, max_retries, data)
            time.sleep(retry_interval_sec)
            continue

        log.error("公開に失敗しました: %s", data)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Threadsへ自動投稿する")
    parser.add_argument("--text", help="投稿本文")
    parser.add_argument("--text-file", help="投稿本文が書かれたテキストファイルのパス")
    parser.add_argument("--image-url", nargs="*", default=[], help="公開画像URL（複数指定でカルーセル）")
    parser.add_argument("--video-url", help="公開動画URL")
    args = parser.parse_args()

    text = args.text
    if args.text_file:
        with open(args.text_file, "r", encoding="utf-8") as f:
            text = f.read().strip()

    access_token, user_id = load_credentials()

    if args.video_url:
        container_id = create_container(access_token, user_id, text=text, video_url=args.video_url)
        publish(access_token, user_id, container_id)

    elif len(args.image_url) == 1:
        container_id = create_container(access_token, user_id, text=text, image_url=args.image_url[0])
        publish(access_token, user_id, container_id)

    elif len(args.image_url) > 1:
        child_ids = []
        for url in args.image_url:
            cid = create_container(access_token, user_id, image_url=url, is_carousel_item=True)
            child_ids.append(cid)
        carousel_id = create_carousel_container(access_token, user_id, text, child_ids)
        publish(access_token, user_id, carousel_id)

    elif text:
        container_id = create_container(access_token, user_id, text=text)
        publish(access_token, user_id, container_id)

    else:
        parser.error("--text（または --text-file）、--image-url、--video-url のいずれかを指定してください")


if __name__ == "__main__":
    main()
