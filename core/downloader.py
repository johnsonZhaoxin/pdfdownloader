# -*- coding: utf-8 -*-
"""PDF 下载：超时、重试、去重、文件名合法化、papacambridge 特化。"""
import os
import re
import time
from urllib.parse import urlparse, unquote, parse_qs

import requests

from config import (
    DEFAULT_HEADERS, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF,
    DOWNLOAD_DELAY, INVALID_FILENAME_CHARS, PAPACAMBRIDGE_REFERER,
)


def filename_from_url(url):
    """从 URL 推导合法本地文件名。

    覆盖三种情况：
      - 普通:  .../0580_s20_qp_12.pdf
      - papacambridge: /download.php?url=https%3A%2F%2F...%2F0580-m20-er.pdf
      - 查询串: .../file.pdf?dl=1
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)

    if "url" in qs:                       # papacambridge 等中转
        inner = unquote(qs["url"][0])
        name = os.path.basename(urlparse(inner).path)
    else:
        name = os.path.basename(unquote(parsed.path))

    name = re.sub(INVALID_FILENAME_CHARS, "_", name).strip()
    if not name:
        name = "file.pdf"
    if not name.lower().endswith(".pdf"):
        name += ".pdf"
    return name


def _headers_for(url):
    headers = dict(DEFAULT_HEADERS)
    if "papacambridge.com" in url:
        headers["Referer"] = PAPACAMBRIDGE_REFERER
    return headers


def download_file(url, save_dir, overwrite=False, log=None):
    """下载单个文件；返回本地路径。已存在且非空则跳过。"""
    os.makedirs(save_dir, exist_ok=True)
    name = filename_from_url(url)
    target = os.path.join(save_dir, name)

    if not overwrite and os.path.exists(target) and os.path.getsize(target) > 0:
        if log:
            log(f"跳过（已存在）: {name}")
        return target

    headers = _headers_for(url)
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with requests.get(url, headers=headers, stream=True,
                              timeout=REQUEST_TIMEOUT) as r:
                r.raise_for_status()
                tmp = target + ".part"
                with open(tmp, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                os.replace(tmp, target)
            if log:
                log(f"下载完成: {name}")
            return target
        except requests.RequestException as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
    raise RuntimeError(f"下载失败: {url} -> {last_exc}")


def download_many(urls, save_dir, progress=None, log=None, overwrite=False):
    """批量下载；progress(done, total) 回调；返回 (成功路径列表, 失败列表)。"""
    ok, failed = [], []
    total = len(urls)
    for i, url in enumerate(urls, 1):
        try:
            ok.append(download_file(url, save_dir, overwrite=overwrite, log=log))
        except Exception as e:
            failed.append((url, str(e)))
            if log:
                log(f"失败: {url} ({e})")
        if progress:
            progress(i, total)
        if i < total and DOWNLOAD_DELAY > 0:
            time.sleep(DOWNLOAD_DELAY)
    return ok, failed