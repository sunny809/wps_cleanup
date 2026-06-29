"""扫描 WPS 缓存/备份目录，统计文件数量和大小。"""

import os
from typing import Dict, List, Optional, Tuple

from .config import CLEANUP_ITEMS, CleanupItem, resolve_path


def scan_item(item: CleanupItem, version: str = "") -> Optional[dict]:
    """扫描单个可清理项，返回其状态信息。

    Returns:
        dict with keys:
            - item: CleanupItem 对象
            - resolved_path: 解析后的绝对路径
            - exists: 路径是否存在
            - file_count: 文件数
            - total_size: 总大小（字节）
            - size_str: 人类可读大小
            - error: 错误信息（如有）
    """
    resolved = resolve_path(item.path_template, version)
    result = {
        "item": item,
        "resolved_path": resolved,
        "exists": False,
        "file_count": 0,
        "total_size": 0,
        "error": None,
    }

    if not os.path.exists(resolved):
        return result

    result["exists"] = True
    total_size = 0
    file_count = 0

    try:
        if os.path.isfile(resolved):
            file_count = 1
            total_size = os.path.getsize(resolved)
        else:
            for dirpath, dirnames, filenames in os.walk(resolved):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    try:
                        # Skip symlinks to avoid issues
                        if os.path.islink(fp):
                            continue
                        total_size += os.path.getsize(fp)
                        file_count += 1
                    except (OSError, PermissionError):
                        continue
    except (OSError, PermissionError) as e:
        result["error"] = str(e)

    result["file_count"] = file_count
    result["total_size"] = total_size
    return result


def scan_all(version: str = "") -> List[dict]:
    """扫描所有可清理项。"""
    return [scan_item(item, version) for item in CLEANUP_ITEMS]


def get_category_summary(results: List[dict]) -> Dict[str, Tuple[int, int]]:
    """按类别汇总文件数和大小。"""
    summary = {}
    for r in results:
        cat = r["item"].category.value
        if cat not in summary:
            summary[cat] = [0, 0]
        if r["exists"]:
            summary[cat][0] += r["file_count"]
            summary[cat][1] += r["total_size"]
    return {k: (v[0], v[1]) for k, v in summary.items()}


def get_total_cleanable(results: List[dict]) -> Tuple[int, int]:
    """统计所有存在的可清理项的总文件数和大小。"""
    total_files = sum(r["file_count"] for r in results if r["exists"])
    total_size = sum(r["total_size"] for r in results if r["exists"])
    return total_files, total_size