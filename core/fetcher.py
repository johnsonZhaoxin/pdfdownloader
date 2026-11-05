# -*- coding: utf-8 -*-
"""网页抓取 + PDF 链接解析。

策略：
1. BeautifulSoup 扫描所有 <a href>，命中 pdf / download_file.php 的保留；
2. 正则兜底，覆盖 JS 内嵌、纯文本链接；
3. download_file.php?files=<url> 这类中转链接，解出内层 pdf 直链；
4. 相对链接转绝对；
5. 按 config.ALLOWED_KEYWORDS 过滤文件名；
6. Dropbox 共享链接把 dl=0 改为 dl=1 以直链下载。
"""
import os
import re
import time
from urllib.parse import urlparse, urljoin, unquote, parse_qs

import requests
from bs4 import BeautifulSoup

from config import (
    DEFAULT_HEADERS, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF,
    ALLOWED_KEYWORDS,
)

PDF_REGEX = re.compile(
    r'https?://[^\s"\'<>]+?\.pdf(?:\?[^\s"\'<>]*)?', re.IGNORECASE)


class FetchError(Exception):
    pass


def _request(url, referer=None):
    headers = dict(DEFAULT_HEADERS)
    if referer:
        headers["Referer"] = referer
    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            last_exc = e
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF * attempt)
    raise FetchError(f"请求失败: {url} -> {last_exc}")


def get_html(url):
    return _request(url).text


def _normalize_link(href, base_url):
    if not href:
        return None
    href = href.strip()
    if href.startswith("//"):
        href = urlparse(base_url).scheme + ":" + href
    elif not href.lower().startswith(("http://", "https://")):
        href = urljoin(base_url, href)
    if "dropbox.com" in href and "dl=0" in href:
        href = href.replace("dl=0", "dl=1")
    return href


def _is_pdf_link(href):
    if not href:
        return False
    low = href.lower()
    return ".pdf" in low or ("download_file.php" in low and "pdf" in low)


def _resolve_real_pdf_url(url):
    """【新增】把 download_file.php?files=<url> 解成内层 pdf 直链。

    日志已经证明内层直链可下载，而 download_file.php 反而 404，
    所以统一替换成内层直链，去重后同一文件只留一条。
    """
    parsed = urlparse(url)
    if "download_file.php" in parsed.path:
        qs = parse_qs(parsed.query)
        if "files" in qs:
            inner = unquote(qs["files"][0])
            if inner.lower().startswith(("http://", "https://")):
                return inner
    return url


def _stem_parts(url):
    """取 URL 最后一段的文件名（去掉扩展名），按下划线分段。"""
    name = os.path.basename(unquote(urlparse(url).path))
    stem, _ = os.path.splitext(name)
    return [p for p in stem.split("_") if p]


def _matches_keywords(url, keywords):
    """【新增】文件名分段里命中任一关键词即保留。"""
    if not keywords:
        return True
    parts = [p.lower() for p in _stem_parts(url)]
    return any(k.lower() in parts for k in keywords)


def get_pdf_links(url):
    """返回页面中所有符合白名单的 PDF 下载链接（去重、保序）。"""
    html = get_html(url)
    soup = BeautifulSoup(html, "html.parser")
    found = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if _is_pdf_link(href):
            abs_url = _normalize_link(href, url)
            if abs_url:
                found.append(_resolve_real_pdf_url(abs_url))

    for m in PDF_REGEX.finditer(html):
        raw = _normalize_link(m.group(0), url)
        if raw:
            found.append(_resolve_real_pdf_url(raw))

    seen, result = set(), []
    for u in found:
        if not u or u in seen:
            continue
        seen.add(u)
        # 【新增】按文件名白名单过滤
        if not _matches_keywords(u, ALLOWED_KEYWORDS):
            continue
        result.append(u)
    return result