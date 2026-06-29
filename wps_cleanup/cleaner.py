"""执行清理操作：删除文件、移至回收站，并记录清理明细。"""

import os
import shutil
import sys
from dataclasses import dataclass, field
from typing import Callable, List, Optional


@dataclass
class CleanResult:
    """单次清理操作的结果，包含被删文件明细。"""
    name: str                     # 显示名称（如 "插件缓存目录"）
    resolved_path: str            # 被清理的目录/文件路径
    success: bool                 # 是否成功
    deleted_files: int            # 删除的文件总数
    deleted_size: int             # 释放的总字节数
    deleted_file_paths: List[str] = field(default_factory=list)  # 逐个被删文件的路径
    error: Optional[str] = None   # 错误信息
    category: str = ""            # 所属类别名称（便于报告分组）
    safety: str = ""              # 安全等级


def _collect_file_paths(root_path: str, max_items: int = 2000) -> List[str]:
    """递归收集路径下的所有文件路径，避免扫描时重复遍历。

    Args:
        root_path: 要扫描的目录或文件路径。
        max_items: 最多收集多少条，超出则截断并附加提示。

    Returns:
        文件路径列表。
    """
    if not os.path.exists(root_path):
        return []

    paths = []
    if os.path.isfile(root_path):
        paths.append(root_path)
    else:
        for dirpath, dirnames, filenames in os.walk(root_path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    if os.path.islink(fp):
                        continue
                    paths.append(fp)
                    if len(paths) >= max_items:
                        paths.append(f"… 及更多文件（超出显示上限 {max_items} 条）")
                        return paths
                except (OSError, PermissionError):
                    continue
    return paths


def _delete_path(path: str) -> bool:
    """删除单个文件或目录，返回是否成功。"""
    try:
        if os.path.isfile(path) or os.path.islink(path):
            os.remove(path)
        else:
            shutil.rmtree(path, ignore_errors=False)
        return True
    except (OSError, PermissionError):
        return False


def clean_item(
    resolved_path: str,
    item_name: str,
    category: str = "",
    safety: str = "",
    use_recycle_bin: bool = True,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> CleanResult:
    """清理单个路径，记录被删文件明细。

    Args:
        resolved_path: 已解析的绝对路径。
        item_name: 显示名称。
        category: 类别名称。
        safety: 安全等级。
        use_recycle_bin: 是否移入回收站（否则永久删除）。
        progress_callback: 进度回调，接收状态字符串。

    Returns:
        CleanResult 对象，包含 deleted_file_paths 明细。
    """
    result = CleanResult(
        name=item_name,
        resolved_path=resolved_path,
        category=category,
        safety=safety,
        success=False,
        deleted_files=0,
        deleted_size=0,
    )

    if not os.path.exists(resolved_path):
        result.success = True
        return result

    # 先收集所有文件路径（用于报告）
    file_paths = _collect_file_paths(resolved_path)
    total_size = 0
    for fp in file_paths:
        if os.path.isfile(fp) and not fp.startswith("…"):
            try:
                total_size += os.path.getsize(fp)
            except (OSError, PermissionError):
                continue
    file_count = len([p for p in file_paths if not p.startswith("…")])

    if progress_callback:
        from .utils import format_size
        progress_callback(f"正在清理 {item_name} ({file_count} 个文件, {format_size(total_size)})...")

    # 执行删除
    try:
        if use_recycle_bin and sys.platform == "win32":
            from .utils import send_to_recycle_bin
            moved = send_to_recycle_bin([resolved_path])
            if moved:
                result.success = True
                result.deleted_files = file_count
                result.deleted_size = total_size
                result.deleted_file_paths = file_paths
                return result
            # fall through to manual delete

        # 逐个删除（永删模式）
        deleted_paths = []
        # 如果是目录，从最深层的文件开始删
        if os.path.isfile(resolved_path):
            if _delete_path(resolved_path):
                deleted_paths = [resolved_path]
        else:
            for dirpath, dirnames, filenames in os.walk(resolved_path, topdown=False):
                for f in filenames:
                    fp = os.path.join(dirpath, f)
                    if _delete_path(fp):
                        deleted_paths.append(fp)
                for d in dirnames:
                    dp = os.path.join(dirpath, d)
                    try:
                        os.rmdir(dp)
                    except OSError:
                        pass
            try:
                os.rmdir(resolved_path)
            except OSError:
                pass

        result.success = True
        result.deleted_files = file_count
        result.deleted_size = total_size
        result.deleted_file_paths = file_paths

    except (OSError, PermissionError) as e:
        result.error = f"删除失败: {e}"

    return result


def clean_selected(
    items_to_clean: List[dict],
    use_recycle_bin: bool = True,
    skip_if_wps_running: bool = True,
    progress_callback: Optional[Callable[[str], None]] = None,
) -> List[CleanResult]:
    """批量清理选中的项。

    Args:
        items_to_clean: scanner 返回的结果 dict 列表。
        use_recycle_bin: 是否使用回收站。
        skip_if_wps_running: WPS 运行时跳过（避免文件占用）。
        progress_callback: 进度回调。

    Returns:
        清理结果列表，每一项包含 deleted_file_paths 明细。
    """
    if skip_if_wps_running:
        running = _check_wps_running()
        if running:
            if progress_callback:
                procs = ", ".join(running)
                progress_callback(f"⚠️ WPS 进程正在运行 ({procs})，请先关闭 WPS 再清理")
            return []

    results = []
    for i, item_data in enumerate(items_to_clean):
        if not item_data["exists"]:
            continue

        item = item_data["item"]
        result = clean_item(
            resolved_path=item_data["resolved_path"],
            item_name=item.name,
            category=item.category.value,
            safety=item.safety.value,
            use_recycle_bin=use_recycle_bin,
            progress_callback=progress_callback,
        )
        results.append(result)

        if progress_callback:
            total = len(items_to_clean)
            done = i + 1
            progress_callback(f"[{done}/{total}] 完成: {item.name}")

    return results


def _check_wps_running() -> List[str]:
    """检查 WPS 进程（内部函数，避免跨模块依赖）。"""
    import subprocess
    wps_names = [
        "wps.exe", "wpsconfig.exe", "wpsupdate.exe",
        "wpsoffice.exe", "et.exe", "wpp.exe",
        "wpscenter.exe", "wpsnotify.exe",
    ]
    running = []
    try:
        output = subprocess.check_output(
            "tasklist /FO CSV /NH", shell=True, text=True
        )
        for line in output.splitlines():
            parts = line.strip().strip('"').split('","')
            if parts and parts[0].lower() in wps_names:
                running.append(parts[0])
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return running
