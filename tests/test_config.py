"""测试 config 模块：路径解析、版本检测、目录定义完整性。"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wps_cleanup.config import (
    CLEANUP_ITEMS,
    Category,
    SafetyLevel,
    resolve_path,
    detect_wps_version,
)


class TestResolvePath:
    """路径解析测试。"""

    def test_expands_tilde(self):
        """~ 开头的路径应展开为 USERPROFILE。"""
        userprofile = r"C:\Users\testuser"
        with patch.dict(os.environ, {"USERPROFILE": userprofile}, clear=True):
            result = resolve_path(r"~\AppData\Roaming\Kingsoft\office6\backup")
            # 验证路径包含 userprofile 和后缀（不比较分隔符风格，跨平台兼容）
            assert result.lower().startswith(userprofile.lower())
            assert "Kingsoft" in result
            assert "office6" in result
            assert "backup" in result
            assert "AppData" in result

    def test_expands_tilde_fallback(self):
        """当 USERPROFILE 不存在时 fallback 到 expanduser。"""
        with patch.dict(os.environ, {}, clear=True):
            result = resolve_path(r"~\AppData\Roaming\Kingsoft")
            assert "Kingsoft" in result

    def test_unknown_path_unchanged(self):
        """不含特殊标记的路径应原样返回。"""
        result = resolve_path(r"C:\Program Files\WPS Office\Cache")
        assert result == r"C:\Program Files\WPS Office\Cache"

    def test_version_placeholder(self):
        """{version} 应被替换为检测到的版本号。"""
        with patch(
            "wps_cleanup.config.detect_wps_version",
            return_value="11.2.2.12345",
        ):
            result = resolve_path(
                r"~\AppData\Local\Kingsoft\WPS Office\{version}\office6\backup"
            )
            assert "11.2.2.12345" in result
            assert "{version}" not in result


class TestDetectWpsVersion:
    """WPS 版本检测测试。"""

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        """每次测试前清除 functools.cache，避免 mock 被缓存污染。"""
        detect_wps_version.cache_clear()

    def _mock_isdir_for_detect(self, base_path: str):
        """创建 isdir mock：让 base 路径和含版本数字的路径返回 True。"""
        def _isdir(path: str) -> bool:
            if path == base_path:
                return True
            if os.path.basename(path)[0].isdigit():
                return True
            return False
        return _isdir

    def test_detects_from_localappdata(self):
        """应从 LocalAppData/Kingsoft/WPS Office 下检测版本号。"""
        local = r"C:\Users\testuser\AppData\Local"
        base = os.path.join(local, "Kingsoft", "WPS Office")
        fake_entries = ["11.8.2.12345", "data", "updater"]

        isdir_mock = self._mock_isdir_for_detect(base)

        with patch.dict(os.environ, {"LOCALAPPDATA": local}):
            with patch("os.listdir", return_value=fake_entries):
                with patch("os.path.isdir", side_effect=isdir_mock):
                    result = detect_wps_version()
                    assert result == "11.8.2.12345"

    def test_fallback_when_no_version_dir(self):
        """没有版本号目录时返回默认版本。"""
        with patch("os.path.isdir", return_value=False):
            result = detect_wps_version()
            assert result == "11.2.2.12345"

    def test_fallback_when_no_localappdata(self):
        """LocalAppData 不存在时返回默认版本。"""
        with patch("os.environ.get", return_value=""):
            with patch("os.path.isdir", return_value=False):
                result = detect_wps_version()
                assert result == "11.2.2.12345"


class TestCleanupItems:
    """清理目录定义完整性测试。"""

    def test_total_items_count(self):
        """CLEANUP_ITEMS 应有 12 项。"""
        assert len(CLEANUP_ITEMS) == 12

    def test_all_categories_covered(self):
        """应覆盖 4 个类别。"""
        cats = {i.category for i in CLEANUP_ITEMS}
        assert cats == {
            Category.PLUGIN_CACHE,
            Category.LOCAL_BACKUP,
            Category.CLOUD_CACHE,
            Category.FEATURE_CACHE,
        }

    def test_safety_levels_present(self):
        """应包含两种安全等级。"""
        levels = {i.safety for i in CLEANUP_ITEMS}
        assert levels == {SafetyLevel.SAFE, SafetyLevel.CAUTION}

    def test_each_item_has_name_and_path(self):
        """每项应有名称和路径模板。"""
        for item in CLEANUP_ITEMS:
            assert item.name, f"Item missing name: {item}"
            assert item.path_template, f"Item missing path: {item.name}"
            assert item.category, f"Item missing category: {item.name}"
            assert item.safety, f"Item missing safety: {item.name}"

    def test_path_templates_no_literal_placeholder(self):
        """路径模板不应包含未替换的 [用户名] 等字面占位符。"""
        forbidden = ["[用户名]", "[版本号]", "<username>"]
        for item in CLEANUP_ITEMS:
            for token in forbidden:
                assert token not in item.path_template, (
                    f"'{item.name}' 路径含有未替换的占位符: {token}"
                )
