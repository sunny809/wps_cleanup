"""
清理报告模块。

在清理完成后生成详细报告，包含：
  - 按类别分组的清理摘要
  - 每项清理的详细文件列表
  - 总计释放空间、删除文件数
  - 支持导出为文本文件
"""

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional

from .cleaner import CleanResult
from .utils import format_size


@dataclass
class CategorySummary:
    """按类别汇总。"""
    name: str
    item_count: int
    file_count: int
    total_size: int
    errors: int

    @property
    def size_str(self) -> str:
        return format_size(self.total_size)


@dataclass
class CleanReport:
    """完整的清理报告。"""
    timestamp: str                          # 清理时间
    total_items: int                        # 清理了多少项
    total_files: int                        # 清理了多少文件
    total_size: int                         # 释放了多少空间
    results: List[CleanResult]              # 每项明细
    category_summaries: List[CategorySummary] = field(default_factory=list)
    duration_seconds: float = 0.0

    @property
    def size_str(self) -> str:
        return format_size(self.total_size)

    @property
    def success_count(self) -> int:
        return sum(1 for r in self.results if r.success)

    @property
    def fail_count(self) -> int:
        return sum(1 for r in self.results if r.error)

    def has_details(self) -> bool:
        """是否有文件级明细。"""
        return any(len(r.deleted_file_paths) > 0 for r in self.results)


def build_report(results: List[CleanResult], duration: float = 0.0) -> CleanReport:
    """从清理结果构建报告。"""
    total_files = sum(r.deleted_files for r in results if r.success)
    total_size = sum(r.deleted_size for r in results if r.success)

    # 按类别汇总
    cat_map: Dict[str, dict] = {}
    for r in results:
        cat = r.category or "未分类"
        if cat not in cat_map:
            cat_map[cat] = {"item_count": 0, "file_count": 0, "total_size": 0, "errors": 0}
        cat_map[cat]["item_count"] += 1
        if r.success:
            cat_map[cat]["file_count"] += r.deleted_files
            cat_map[cat]["total_size"] += r.deleted_size
        if r.error:
            cat_map[cat]["errors"] += 1

    cat_summaries = [
        CategorySummary(name=name, **data)
        for name, data in cat_map.items()
    ]

    return CleanReport(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        total_items=len(results),
        total_files=total_files,
        total_size=total_size,
        results=results,
        category_summaries=cat_summaries,
        duration_seconds=duration,
    )


def report_to_text(report: CleanReport, include_file_list: bool = False) -> str:
    """将报告格式化为纯文本。"""
    lines = []
    sep = "=" * 58

    lines.append(sep)
    lines.append("  WPS Office 磁盘清理报告")
    lines.append(sep)
    lines.append(f"  清理时间: {report.timestamp}")
    lines.append(f"  耗时: {report.duration_seconds:.1f} 秒")
    lines.append("")
    lines.append(f"  ✅ 成功: {report.success_count} 项")
    if report.fail_count:
        lines.append(f"  ❌ 失败: {report.fail_count} 项")
    lines.append(f"  📄 删除文件: {report.total_files} 个")
    lines.append(f"  💾 释放空间: {report.size_str}")
    lines.append("")

    # 按类别汇总
    lines.append("  ── 按类别汇总 ──")
    for cs in report.category_summaries:
        err_str = f"  ⚠ {cs.errors} 项失败" if cs.errors else ""
        lines.append(
            f"    {cs.name}: {cs.item_count} 项, "
            f"{cs.file_count} 个文件, {cs.size_str}{err_str}"
        )
    lines.append("")

    # 每项明细
    lines.append("  ── 清理明细 ──")
    for r in report.results:
        if r.success:
            size_str = format_size(r.deleted_size)
            icon = "✅"
            lines.append(f"    {icon} {r.name}")
            lines.append(f"       路径: {r.resolved_path}")
            lines.append(f"       文件: {r.deleted_files} 个, 释放 {size_str}")
        elif r.error:
            lines.append(f"    ❌ {r.name}")
            lines.append(f"       路径: {r.resolved_path}")
            lines.append(f"       错误: {r.error}")

        # 文件级明细
        if include_file_list and r.deleted_file_paths:
            # 最多显示 30 条
            show_paths = r.deleted_file_paths[:30]
            truncated = len(r.deleted_file_paths) > 30
            for fp in show_paths:
                lines.append(f"         • {fp}")
            if truncated:
                lines.append(f"         … 及 {len(r.deleted_file_paths) - 30} 个文件")
        lines.append("")

    lines.append(sep)
    return "\n".join(lines)


def report_to_json(report: CleanReport) -> str:
    """将报告导出为 JSON。"""
    data = {
        "timestamp": report.timestamp,
        "total_items": report.total_items,
        "total_files": report.total_files,
        "total_size": report.total_size,
        "total_size_str": report.size_str,
        "success_count": report.success_count,
        "fail_count": report.fail_count,
        "duration_seconds": report.duration_seconds,
        "category_summaries": [
            {
                "name": cs.name,
                "item_count": cs.item_count,
                "file_count": cs.file_count,
                "total_size": cs.total_size,
                "total_size_str": cs.size_str,
                "errors": cs.errors,
            }
            for cs in report.category_summaries
        ],
        "items": [
            {
                "name": r.name,
                "path": r.resolved_path,
                "success": r.success,
                "deleted_files": r.deleted_files,
                "deleted_size": r.deleted_size,
                "error": r.error,
                "category": r.category,
                "safety": r.safety,
                "deleted_files_list": r.deleted_file_paths[:100]
                if r.deleted_file_paths else [],
            }
            for r in report.results
        ],
    }
    return json.dumps(data, ensure_ascii=False, indent=2)


def _get_documents_dir() -> str:
    """获取用户的「文档」目录，兼容中英文 Windows。"""
    import sys as _sys
    if _sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            # FOLDERID_Documents = {FDD39AD0-066F-46EF-AD0D-EF7386ADDF13}
            GUID = ctypes.create_unicode_buffer(64)
            guid_str = "{FDD39AD0-066F-46EF-AD0D-EF7386ADDF13}"
            ctypes.windll.ole32.CLSIDFromString(guid_str, GUID)
            buf = ctypes.c_wchar_p()
            # SHGetKnownFolderPath(REFKNOWNFOLDERID, DWORD, HANDLE, PWSTR*)
            ctypes.windll.shell32.SHGetKnownFolderPath(
                ctypes.byref(GUID), 0, None, ctypes.byref(buf)
            )
            result = buf.value
            ctypes.windll.ole32.CoTaskMemFree(buf)
            if result:
                return result
        except Exception:
            pass
    # fallback：尝试 "Documents" 和 "文档"
    user = os.environ.get("USERPROFILE", os.path.expanduser("~"))
    for name in ("Documents", "文档"):
        p = os.path.join(user, name)
        if os.path.isdir(p):
            return p
    return os.path.join(user, "Documents")  # last resort


def save_report(
    report: CleanReport,
    directory: Optional[str] = None,
    as_json: bool = False,
) -> str:
    """将报告保存到文件，返回文件路径。"""
    if directory is None:
        directory = os.path.join(
            _get_documents_dir(),
            "WPSCleanup",
        )
    os.makedirs(directory, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = ".json" if as_json else ".txt"
    filename = f"wps_cleanup_report_{ts}{ext}"
    filepath = os.path.join(directory, filename)

    content = report_to_json(report) if as_json else report_to_text(report, include_file_list=True)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filepath
