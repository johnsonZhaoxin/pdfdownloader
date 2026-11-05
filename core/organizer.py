# -*- coding: utf-8 -*-
"""按文件名倒数第二段把 PDF 归档到 ms/ qp/ 子目录。"""
import os
import shutil

from config import ARCHIVE_KINDS


def organize_pdfs(base_dir, kinds=ARCHIVE_KINDS, log=None):
    """返回 {'moved': int, 'skipped': int}。"""
    if not os.path.isdir(base_dir):
        raise NotADirectoryError(base_dir)

    for kind in kinds:
        os.makedirs(os.path.join(base_dir, kind), exist_ok=True)

    moved, skipped = 0, 0
    for entry in os.listdir(base_dir):
        full = os.path.join(base_dir, entry)
        if not os.path.isfile(full):
            continue
        filename, ext = os.path.splitext(entry)
        if ext.lower() != ".pdf":
            continue

        parts = filename.split("_")
        if len(parts) < 2:
            skipped += 1
            continue

        kind = parts[-2]
        if kind not in kinds:
            skipped += 1
            continue

        dst = os.path.join(base_dir, kind, entry)
        if os.path.exists(dst):
            if log:
                log(f"目标已存在，跳过: {entry}")
            skipped += 1
            continue

        shutil.move(full, dst)
        moved += 1
        if log:
            log(f"归档: {entry} -> {kind}/")

    return {"moved": moved, "skipped": skipped}