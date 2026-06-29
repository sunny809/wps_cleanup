"""
命令行模式入口，支持非交互式扫描和清理。
适用于脚本化运行或远程执行。

使用方式:
    python -m wps_cleanup.cli scan
    python -m wps_cleanup.cli clean --dry-run
    python -m wps_cleanup.cli clean --safe-only
"""

import argparse
import sys

from .cleaner import clean_selected
from .config import SafetyLevel, detect_wps_version
from .scanner import scan_all, get_total_cleanable
from .utils import check_wps_running, format_size


def cmd_scan(args):
    """扫描并输出结果。"""
    version = detect_wps_version()
    results = scan_all(version)

    print(f"WPS 版本: {version}")
    print()

    for r in results:
        item = r["item"]
        status = "✓" if r["exists"] else "—"
        size_str = format_size(r["total_size"]) if r["exists"] else ""
        safety = "安全" if item.safety == SafetyLevel.SAFE else "谨慎"
        if r["exists"]:
            detail = "存在  {} 个文件, {}".format(r["file_count"], size_str)
        else:
            detail = "不存在"
        print(
            "  [{}] {}\n"
            "         路径: {}\n"
            "         状态: {}\n"
            "         安全: {}".format(status, item.name, r["resolved_path"], detail, safety)
        )
        if r.get("error"):
            print(f"         错误: {r['error']}")
        print()

    total_files, total_size = get_total_cleanable(results)
    print(f"总计: {total_files} 个文件可清理, 共 {format_size(total_size)}")


def cmd_clean(args):
    """执行清理。"""
    # 检查 WPS 进程
    running = check_wps_running()
    if running:
        print(f"⚠️  WPS 进程正在运行: {', '.join(running)}")
        if not args.force:
            print("请先关闭 WPS 或使用 --force 强制清理")
            sys.exit(1)

    version = detect_wps_version()
    results = scan_all(version)

    # 筛选
    to_clean = []
    for r in results:
        if not r["exists"]:
            continue
        if args.safe_only and r["item"].safety != SafetyLevel.SAFE:
            continue
        to_clean.append(r)

    if not to_clean:
        print("没有需要清理的项目。")
        return

    # 统计
    total_files = sum(d["file_count"] for d in to_clean)
    total_size = sum(d["total_size"] for d in to_clean)

    print(f"将清理 {len(to_clean)} 个项目:")
    for d in to_clean:
        star = " " if d["item"].safety == SafetyLevel.SAFE else "⚠"
        print(f"  {star} {d['item'].name} ({format_size(d['total_size'])})")
    print(f"总计: {total_files} 个文件, {format_size(total_size)}")

    if args.dry_run:
        print("\n❖ 模拟运行模式，未执行实际删除。")
        return

    # 确认
    if not args.yes:
        ans = input("\n确认执行清理？(y/N): ")
        if ans.lower() != "y":
            print("已取消。")
            return

    # 执行
    results = clean_selected(
        to_clean,
        use_recycle_bin=not args.permanent,
        skip_if_wps_running=not args.force,
    )

    success = sum(1 for r in results if r.success)
    failed = sum(1 for r in results if r.error)
    deleted = sum(r.deleted_size for r in results)
    print(f"\n✅ 成功: {success} 项, 释放 {format_size(deleted)}")
    if failed:
        print(f"❌ 失败: {failed} 项")
        for r in results:
            if r.error:
                print(f"   • {r.name}: {r.error}")


def main():
    parser = argparse.ArgumentParser(
        description="WPS Office 磁盘清理工具 - 命令行模式"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # scan
    p_scan = sub.add_parser("scan", help="扫描 WPS 缓存目录")
    p_scan.set_defaults(func=cmd_scan)

    # clean
    p_clean = sub.add_parser("clean", help="执行清理")
    p_clean.add_argument(
        "--safe-only", action="store_true",
        help="仅清理标记为「可安全删除」的项目，跳过需要谨慎处理的"
    )
    p_clean.add_argument(
        "--dry-run", action="store_true",
        help="模拟运行，不实际删除"
    )
    p_clean.add_argument(
        "--force", action="store_true",
        help="即使 WPS 进程正在运行也执行清理"
    )
    p_clean.add_argument(
        "--permanent", action="store_true",
        help="永久删除（不移入回收站）"
    )
    p_clean.add_argument(
        "-y", "--yes", action="store_true",
        help="跳过确认提示"
    )
    p_clean.set_defaults(func=cmd_clean)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()