#!/usr/bin/env python3
"""
WPS Office 磁盘清理工具。

支持扫描并清理 WPS Office 在 Windows 上的各种缓存、备份和临时文件。
提供图形界面，支持按类别查看和选择性地清理。

使用方式:
    python main.py
"""

import os
import sys

# 确保包路径正确
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wps_cleanup.app import WPSCleanupApp


def main():
    if sys.platform != "win32":
        print(
            "⚠️  此工具专为 Windows 系统设计，当前运行环境非 Windows。\n"
            "    部分路径解析和进程检测功能将不可用。"
        )
        answer = input("是否仍要继续？(y/N): ")
        if answer.lower() != "y":
            sys.exit(0)

    app = WPSCleanupApp()
    app.run()


if __name__ == "__main__":
    main()
