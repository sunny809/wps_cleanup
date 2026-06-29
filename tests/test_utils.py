"""测试 utils 模块：文件大小格式化、工具函数。"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wps_cleanup.utils import format_size


class TestFormatSize:
    """文件大小格式化测试。"""

    @pytest.mark.parametrize(
        "bytes_in, expected",
        [
            (0, "0 B"),
            (1, "1.00 B"),
            (512, "512.00 B"),
            (1024, "1.00 KB"),
            (1536, "1.50 KB"),
            (1024 * 1024, "1.00 MB"),
            (1024 * 1024 * 5, "5.00 MB"),
            (1024 * 1024 * 1024, "1.00 GB"),
            (1024 * 1024 * 1024 * 2, "2.00 GB"),
            # 边界值
            (1023, "1023.00 B"),
            (1025, "1.00 KB"),
            # 大数值
            (1024 ** 4, "1.00 TB"),
        ],
    )
    def test_format_size(self, bytes_in, expected):
        """应正确格式化各种大小。"""
        assert format_size(bytes_in) == expected

    def test_format_size_large_numbers(self):
        """超大数字不应报错。"""
        size = 1024 ** 5  # 1 PB
        result = format_size(size)
        assert isinstance(result, str)
        assert "PB" in result or "TB" in result

    def test_twopointfive_mb(self):
        """2.5 MB 应正确显示。"""
        size = int(2.5 * 1024 * 1024)
        result = format_size(size)
        assert "2.50 MB" in result or "2.5" in result

    def test_rounding_edge(self):
        """舍入应合理。"""
        # 1 KB 少 1 字节 → 应当仍显示 1.00 KB 或 1023.00 B
        size = 1023
        result = format_size(size)
        assert "B" in result

        # 1 KB 多 1 字节 → 1.00 KB
        size = 1025
        result = format_size(size)
        assert "KB" in result


class TestCheckWpsRunning:
    """WPS 进程检测测试（mock tasklist）。"""

    def test_wps_running(self):
        """当 tasklist 返回 WPS 进程时应检测到。"""
        with patch("subprocess.check_output") as mock:
            mock.return_value = (
                '"wps.exe","1234","Console","1","5,000 K"\n'
                '"et.exe","5678","Console","1","8,000 K"\n'
            )
            from wps_cleanup.utils import check_wps_running
            running = check_wps_running()
            assert "wps.exe" in running
            assert "et.exe" in running

    def test_no_wps_running(self):
        """没有 WPS 进程时应返回空列表。"""
        with patch("subprocess.check_output") as mock:
            mock.return_value = (
                '"notepad.exe","1234","Console","1","5,000 K"\n'
                '"chrome.exe","5678","Console","1","20,000 K"\n'
            )
            from wps_cleanup.utils import check_wps_running
            running = check_wps_running()
            assert len(running) == 0

    def test_tasklist_fails_gracefully(self):
        """tasklist 命令失败时应返回空列表。"""
        with patch("subprocess.check_output", side_effect=FileNotFoundError):
            from wps_cleanup.utils import check_wps_running
            running = check_wps_running()
            assert running == []


class TestUserPaths:
    """用户路径获取测试。"""

    def test_get_user_profile(self):
        """应返回 USERPROFILE 或 fallback 值。"""
        from wps_cleanup.utils import get_user_profile
        profile = get_user_profile()
        assert isinstance(profile, str)
        assert len(profile) > 0

    def test_get_local_appdata(self):
        """应返回 LOCALAPPDATA 或 fallback 值。"""
        from wps_cleanup.utils import get_local_appdata
        path = get_local_appdata()
        assert isinstance(path, str)
        assert "Local" in path or "AppData" in path or len(path) > 0

    def test_get_roaming_appdata(self):
        """应返回 APPDATA 或 fallback 值。"""
        from wps_cleanup.utils import get_roaming_appdata
        path = get_roaming_appdata()
        assert isinstance(path, str)
        assert "Roaming" in path or "AppData" in path or len(path) > 0
