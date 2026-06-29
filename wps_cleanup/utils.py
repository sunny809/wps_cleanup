"""工具函数：WPS 进程检测、文件大小格式化等。"""

import os
import subprocess
from typing import List, Optional


def check_wps_running() -> List[str]:
    """检查是否有 WPS 相关进程正在运行。

    Returns:
        正在运行的 WPS 进程名列表，若无则返回空列表。
    """
    wps_process_names = [
        "wps.exe",
        "wpsconfig.exe",
        "wpsupdate.exe",
        "wpsoffice.exe",
        "et.exe",       # 表格
        "wpp.exe",      # 演示
        "wpscenter.exe",
        "wpsnotify.exe",
    ]
    running = []
    try:
        output = subprocess.check_output(
            "tasklist /FO CSV /NH", shell=True, text=True
        )
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            # tasklist CSV 格式: "Name","PID","Session","Session#","Mem Usage"
            # 提取第一个引号字段作为进程名
            if line.startswith('"'):
                end = line.find('"', 1)
                if end > 0:
                    name = line[1:end].lower()
                    if name in wps_process_names:
                        if name not in running:
                            running.append(name)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return running


def format_size(size_bytes: int) -> str:
    """将字节数转换为人类可读的格式。使用整数除法避免 float 溢出。"""
    if size_bytes == 0:
        return "0 B"
    units = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    size = size_bytes
    while size >= 1024 and i < len(units) - 1:
        size //= 1024
        i += 1
    # 用指数计算最后的浮点值，避免中间 float 溢出
    size_f = size_bytes / (1024 ** i)
    return f"{size_f:.2f} {units[i]}"


def get_user_profile() -> str:
    """获取当前用户的 USERPROFILE 路径。"""
    return os.environ.get("USERPROFILE", os.path.expanduser("~"))


def get_local_appdata() -> str:
    """获取 LocalAppData 路径。"""
    return os.environ.get("LOCALAPPDATA", os.path.join(get_user_profile(), "AppData", "Local"))


def get_roaming_appdata() -> str:
    """获取 RoamingAppData 路径。"""
    return os.environ.get("APPDATA", os.path.join(get_user_profile(), "AppData", "Roaming"))


def send_to_recycle_bin(paths: List[str]) -> bool:
    """尝试将文件/文件夹发送到回收站（而非永久删除）。

    使用 Windows 的 shell32.dll SHEmptyRecycleBin / IFileOperation API。
    如果失败，回退到 os.remove/shutil.rmtree。
    """
    import ctypes
    from ctypes import wintypes

    try:
        # Try using IFileOperation (Windows Vista+)
        # Fallback: use shell32.SHFileOperation
        class SHFILEOPSTRUCTW(ctypes.Structure):
            _fields_ = [
                ("hwnd", wintypes.HWND),
                ("wFunc", ctypes.c_uint),
                ("pFrom", wintypes.LPCWSTR),
                ("pTo", wintypes.LPCWSTR),
                ("fFlags", ctypes.c_ushort),
                ("fAborted", wintypes.BOOL),
                ("hNameMaps", wintypes.LPVOID),
                ("sProgress", wintypes.LPCWSTR),
            ]

        FO_DELETE = 3
        FOF_ALLOWUNDO = 0x40
        FOF_NOCONFIRMATION = 0x10
        FOF_SILENT = 0x04

        # Build double-null-terminated list
        path_str = "\0".join(paths) + "\0\0"

        operation = SHFILEOPSTRUCTW(
            hwnd=0,
            wFunc=FO_DELETE,
            pFrom=path_str,
            pTo=None,
            fFlags=FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT,
            fAborted=False,
            hNameMaps=None,
            sProgress=None,
        )

        result = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(operation))
        return result == 0
    except Exception:
        return False