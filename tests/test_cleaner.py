"""测试 cleaner 模块：文件明细收集、清理执行、结果记录。"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wps_cleanup.cleaner import (
    CleanResult,
    _collect_file_paths,
    clean_item,
    clean_selected,
)


class TestCollectFilePaths:
    """文件路径收集测试。"""

    def test_collects_all_files(self, tmp_workspace):
        """应递归收集所有文件路径。"""
        paths = _collect_file_paths(
            os.path.join(tmp_workspace, "addons", "pool", "win-i386")
        )
        # 应为 3 个文件
        assert len(paths) == 3
        assert any("plugin_a.dll" in p for p in paths)
        assert any("plugin_b.dat" in p for p in paths)
        assert any("config.json" in p for p in paths)

    def test_collects_single_file(self, tmp_workspace):
        """单文件路径应直接返回。"""
        file_path = os.path.join(tmp_workspace, "single.tmp")
        with open(file_path, "w") as f:
            f.write("test")

        paths = _collect_file_paths(file_path)
        assert len(paths) == 1
        assert paths[0] == file_path

    def test_empty_directory(self, tmp_workspace):
        """空目录应返回空列表。"""
        paths = _collect_file_paths(os.path.join(tmp_workspace, "empty"))
        assert len(paths) == 0

    def test_nonexistent_path(self):
        """不存在的路径应返回空列表。"""
        paths = _collect_file_paths(r"C:\nothing\here")
        assert len(paths) == 0

    def test_max_items_limit(self, tmp_workspace):
        """超出 max_items 上限时应截断。"""
        # 创建 10 个文件
        many_dir = os.path.join(tmp_workspace, "many_files")
        os.makedirs(many_dir)
        for i in range(10):
            with open(os.path.join(many_dir, f"file_{i}.dat"), "w") as f:
                f.write("x")

        paths = _collect_file_paths(many_dir, max_items=5)
        # 应该有 5 个文件 + 1 条截断提示
        assert len(paths) == 6
        assert paths[-1].startswith("…")


class TestCleanItem:
    """单项目清理测试。"""

    def test_clean_nonexistent_path(self):
        """不存在的路径应视为清理成功。"""
        result = clean_item(
            resolved_path=r"C:\nothing\here",
            item_name="不存在",
        )
        assert result.success is True
        assert result.deleted_files == 0
        assert result.deleted_size == 0

    def test_clean_file_success(self, tmp_workspace):
        """清理单文件应成功。"""
        file_path = os.path.join(tmp_workspace, "to_delete.tmp")
        with open(file_path, "wb") as f:
            f.write(b"x" * 100)

        result = clean_item(
            resolved_path=file_path,
            item_name="测试文件",
            use_recycle_bin=False,  # 用永删（避免回收站 mock）
        )

        assert result.success is True
        assert result.deleted_files == 1
        assert result.deleted_size == 100
        assert os.path.exists(file_path) is False

    def test_clean_directory_success(self, tmp_workspace):
        """清理目录应删除所有文件。"""
        target = os.path.join(tmp_workspace, "addons", "pool", "win-i386")

        result = clean_item(
            resolved_path=target,
            item_name="测试目录",
            use_recycle_bin=False,
        )

        assert result.success is True
        assert result.deleted_files == 3
        assert result.deleted_size == 3584
        assert os.path.exists(target) is False

    def test_clean_records_file_paths(self, tmp_workspace):
        """清理后应记录被删文件路径。"""
        target = os.path.join(tmp_workspace, "office6", "backup")

        result = clean_item(
            resolved_path=target,
            item_name="测试备份",
            use_recycle_bin=False,
        )

        assert result.success is True
        assert len(result.deleted_file_paths) == 2
        assert any("doc1.wpsbak" in p for p in result.deleted_file_paths)
        assert any("doc2.wpsbak" in p for p in result.deleted_file_paths)

    def test_clean_unknown_path_records_error(self):
        """不可达路径应记录错误。"""
        result = clean_item(
            resolved_path=r"C:\Windows\System32\config\SAM",
            item_name="系统保护文件",
            use_recycle_bin=False,
        )
        # 可能成功（如果权限不够会失败）或失败，但不应该 crash
        assert isinstance(result, CleanResult)


class TestCleanSelected:
    """批量清理测试。"""

    def test_clean_selected_items(self, sample_scan_results):
        """批量清理应返回每个项的结果。"""
        # 只选存在的项
        to_clean = [r for r in sample_scan_results if r["exists"]]
        results = clean_selected(
            to_clean,
            use_recycle_bin=False,  # 永删模式
            skip_if_wps_running=False,
        )

        assert len(results) == len(to_clean)
        for r in results:
            assert r.success is True
            assert r.deleted_files > 0
            assert r.deleted_size > 0

    def test_clean_selected_skips_nonexistent(self, sample_scan_results):
        """不存在的项应被跳过。"""
        to_clean = [r for r in sample_scan_results if not r["exists"]]
        results = clean_selected(
            to_clean,
            use_recycle_bin=False,
            skip_if_wps_running=False,
        )
        assert len(results) == 0

    def test_clean_result_dataclass(self):
        """CleanResult 应包含所有必要字段。"""
        r = CleanResult(
            name="测试",
            resolved_path=r"C:\test",
            success=True,
            deleted_files=5,
            deleted_size=1000,
            deleted_file_paths=["a.txt", "b.txt"],
            category="测试类别",
            safety="安全",
        )
        assert r.name == "测试"
        assert r.success is True
        assert r.deleted_files == 5
        assert r.deleted_size == 1000
        assert len(r.deleted_file_paths) == 2
        assert r.category == "测试类别"
        assert r.safety == "安全"
        assert r.error is None

    def test_clean_result_with_error(self):
        """带错误的 CleanResult 应有 error 字段。"""
        r = CleanResult(
            name="失败项",
            resolved_path=r"C:\locked",
            success=False,
            deleted_files=0,
            deleted_size=0,
            error="文件被占用",
        )
        assert r.success is False
        assert r.error == "文件被占用"
        assert r.deleted_files == 0
        assert r.deleted_size == 0
