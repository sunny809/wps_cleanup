"""测试 report 模块：报告构建、格式化、保存。"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from wps_cleanup.report import (
    build_report,
    report_to_text,
    report_to_json,
    save_report,
    CleanReport,
    CategorySummary,
)
from wps_cleanup.cleaner import CleanResult


class TestBuildReport:
    """报告构建测试。"""

    def test_build_report_with_results(self, sample_clean_results):
        """应从清理结果正确构建报告。"""
        report = build_report(sample_clean_results, duration=2.5)

        assert report.total_items == 3
        assert report.total_files == 5  # 3 + 2（失败项成功数为 0）
        assert report.total_size == 173584  # 3584 + 170000
        assert report.success_count == 2
        assert report.fail_count == 1
        assert report.duration_seconds == 2.5

    def test_build_report_empty(self):
        """空结果应构建空报告。"""
        report = build_report([], duration=0)
        assert report.total_items == 0
        assert report.total_files == 0
        assert report.total_size == 0
        assert report.success_count == 0
        assert report.fail_count == 0

    def test_category_summaries(self, sample_clean_results):
        """应按类别正确汇总。"""
        report = build_report(sample_clean_results)

        cat_names = [cs.name for cs in report.category_summaries]
        assert "插件与组件缓存" in cat_names
        assert "本地备份与自动恢复" in cat_names

        for cs in report.category_summaries:
            if cs.name == "本地备份与自动恢复":
                assert cs.file_count == 2
                assert cs.total_size == 170_000
                assert cs.errors == 0

    def test_has_details_flag(self, sample_clean_results):
        """当有文件路径明细时 has_details() 应返回 True。"""
        report = build_report(sample_clean_results)
        assert report.has_details() is True

    def test_empty_results_no_details(self):
        """空结果 has_details() 应返回 False。"""
        report = build_report([])
        assert report.has_details() is False


class TestReportFormatting:
    """报告格式化测试。"""

    def test_report_to_text_contains_key_info(self, sample_clean_results):
        """文本报告应包含关键信息。"""
        report = build_report(sample_clean_results)
        text = report_to_text(report)

        assert "WPS Office 磁盘清理报告" in text
        assert "✅ 成功: 2 项" in text
        assert "❌ 失败: 1 项" in text
        assert "插件缓存" in text
        assert "本地备份" in text
        assert "失败项" in text
        assert "文件被占用" in text

    def test_report_to_text_with_file_list(self, sample_clean_results):
        """文本报告包含文件列表时应列出各路径。"""
        report = build_report(sample_clean_results)
        text = report_to_text(report, include_file_list=True)

        assert "plugin_a.dll" in text
        assert "doc1.wpsbak" in text

    def test_report_to_json_structure(self, sample_clean_results):
        """JSON 报告应包含所有顶层字段。"""
        report = build_report(sample_clean_results)
        json_str = report_to_json(report)
        data = json.loads(json_str)

        assert data["timestamp"] == report.timestamp
        assert data["total_items"] == 3
        assert data["total_files"] == 5
        assert data["success_count"] == 2
        assert data["fail_count"] == 1

    def test_report_to_json_items(self, sample_clean_results):
        """JSON 报告应包含每项的详细信息。"""
        report = build_report(sample_clean_results)
        data = json.loads(report_to_json(report))

        assert len(data["items"]) == 3
        item_names = [i["name"] for i in data["items"]]
        assert "插件缓存" in item_names
        assert "本地备份" in item_names
        assert "失败项" in item_names

    def test_report_to_json_file_lists(self, sample_clean_results):
        """JSON 报告应包含被删文件列表。"""
        report = build_report(sample_clean_results)
        data = json.loads(report_to_json(report))

        for item in data["items"]:
            if item["success"]:
                assert len(item["deleted_files_list"]) > 0

    def test_category_summary_size_str(self):
        """CategorySummary 的 size_str 属性应可读。"""
        cs = CategorySummary(
            name="测试", item_count=2, file_count=10,
            total_size=2048, errors=0,
        )
        assert "2.00" in cs.size_str
        assert "KB" in cs.size_str


class TestSaveReport:
    """报告保存测试。"""

    def test_save_text_report(self, sample_clean_results, tmp_path):
        """应能将报告保存为文本文件。"""
        report = build_report(sample_clean_results)
        filepath = save_report(report, directory=str(tmp_path), as_json=False)

        assert os.path.exists(filepath)
        assert filepath.endswith(".txt")
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        assert "WPS Office 磁盘清理报告" in content

    def test_save_json_report(self, sample_clean_results, tmp_path):
        """应能将报告保存为 JSON 文件。"""
        report = build_report(sample_clean_results)
        filepath = save_report(report, directory=str(tmp_path), as_json=True)

        assert os.path.exists(filepath)
        assert filepath.endswith(".json")
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["total_items"] == 3

    def test_save_report_default_dir(self, sample_clean_results):
        """默认目录应被自动创建。"""
        report = build_report(sample_clean_results)
        filepath = save_report(report, as_json=False)

        try:
            assert os.path.exists(filepath)
            assert "WPSCleanup" in filepath
        finally:
            # 清理
            if os.path.exists(filepath):
                os.remove(filepath)
            parent = os.path.dirname(filepath)
            if os.path.exists(parent):
                os.rmdir(parent)


class TestCleanReportDataclass:
    """CleanReport 数据类测试。"""

    def test_properties(self):
        """应正确计算属性值。"""
        report = CleanReport(
            timestamp="2024-01-01 12:00:00",
            total_items=2,
            total_files=10,
            total_size=5000,
            results=[],
        )
        assert report.size_str is not None
        assert report.success_count == 0
        assert report.fail_count == 0
        assert report.has_details() is False
