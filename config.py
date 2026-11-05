# -*- coding: utf-8 -*-
"""集中配置：UA、超时、重试、归档规则、路径。"""
import os

# ---------- 网络 ----------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {"User-Agent": USER_AGENT}

REQUEST_TIMEOUT = 30      # 秒
MAX_RETRIES = 3
RETRY_BACKOFF = 1.0       # 第 n 次重试等待 n*BACKOFF 秒
DOWNLOAD_DELAY = 0.5      # 每个文件之间节流，避免被封

# papacambridge 等站点对 Referer 敏感
PAPACAMBRIDGE_REFERER = "https://pastpapers.papacambridge.com/"

# ---------- 文件 ----------
# 这些字符在 Windows 文件名中非法，需要替换
INVALID_FILENAME_CHARS = r'[\\/:*?"<>|\r\n\t]'

# 按试卷类型归档的子目录名
ARCHIVE_KINDS = ("ms", "qp")

# 默认下载目录
DEFAULT_DOWNLOAD_DIR = os.path.join(os.getcwd(), "downloads")

# 只下载文件名"下划线分段"里包含这些关键词的文件（大小写不敏感）
# 例如 9702_m26_er.pdf -> 分段 ['9702','m26','er'] -> 命中 'er'
#      9702_m26_ci_33.pdf -> 分段 ['9702','m26','ci','33'] -> 不命中，过滤掉
# 设为空元组 () 表示不过滤
ALLOWED_KEYWORDS = ("er", "gt", "ms", "qp","ci")