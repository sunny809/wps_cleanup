"""
清理报告弹窗。

在清理完成后展示详细报告，支持：
  - 按类别分组的摘要卡片
  - 展开/收缩每项的文件明细
  - 保存报告到文件
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List

from .cleaner import CleanResult
from .report import build_report, report_to_text, report_to_json
from .utils import format_size


class ReportDialog:
    """清理报告弹窗。"""

    def __init__(self, parent: tk.Widget, results: List[CleanResult], duration: float = 0.0):
        self.parent = parent
        self.report = build_report(results, duration)

        self._build_dialog()

    def _build_dialog(self):
        self.win = tk.Toplevel(self.parent)
        self.win.title("🧹 清理报告")
        self.win.geometry("780x600")
        self.win.minsize(680, 480)
        self.win.configure(bg="#f4f6f9")
        self.win.transient(self.parent)
        self.win.grab_set()

        # 整体布局
        self.win.columnconfigure(0, weight=1)
        self.win.rowconfigure(0, weight=0)  # 摘要区
        self.win.rowconfigure(1, weight=1)  # 明细区
        self.win.rowconfigure(2, weight=0)  # 底部按钮

        self._build_summary()
        self._build_details()
        self._build_buttons()

        # 居中
        self.win.update_idletasks()
        x = self.parent.winfo_rootx() + (self.parent.winfo_width() - self.win.winfo_width()) // 2
        y = self.parent.winfo_rooty() + (self.parent.winfo_height() - self.win.winfo_height()) // 2
        self.win.geometry(f"+{x}+{y}")

    def _build_summary(self):
        """顶部摘要区域。"""
        frame = tk.Frame(self.win, bg="white", highlightbackground="#e0e4e8", highlightthickness=1)
        frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 8))
        frame.columnconfigure(0, weight=1)

        # 标题
        tk.Label(
            frame, text="✅  清理完成",
            font=("Microsoft YaHei", 14, "bold"),
            bg="white", fg="#2c3e50",
        ).grid(row=0, column=0, columnspan=4, padx=20, pady=(14, 4), sticky="w")

        # 时间
        tk.Label(
            frame, text=self.report.timestamp,
            font=("Microsoft YaHei", 8),
            bg="white", fg="#95a5a6",
        ).grid(row=1, column=0, columnspan=4, padx=20, pady=(0, 10), sticky="w")

        # 四个统计卡片
        stats = [
            ("✅ 成功", str(self.report.success_count), "#27ae60"),
            ("📄 删除文件", str(self.report.total_files), "#2c6fbb"),
            ("💾 释放空间", self.report.size_str, "#2c6fbb"),
            ("⏱ 耗时", f"{self.report.duration_seconds:.1f} 秒", "#888"),
        ]
        if self.report.fail_count:
            stats.append(("❌ 失败", str(self.report.fail_count), "#e74c3c"))

        for i, (label, value, color) in enumerate(stats):
            card = tk.Frame(frame, bg="#f8f9fa", highlightbackground="#e0e4e8", highlightthickness=1)
            card.grid(row=2, column=i, padx=(20 if i == 0 else 4, 4), pady=(0, 16), sticky="ew")
            frame.columnconfigure(i, weight=1)
            tk.Label(
                card, text=value,
                font=("Microsoft YaHei", 18, "bold"),
                bg="#f8f9fa", fg=color,
            ).pack(padx=12, pady=(10, 0))
            tk.Label(
                card, text=label,
                font=("Microsoft YaHei", 9),
                bg="#f8f9fa", fg="#888",
            ).pack(padx=12, pady=(0, 10))

    def _build_details(self):
        """中部明细区域，带 Notebook 标签页。"""
        container = tk.Frame(self.win, bg="#f4f6f9")
        container.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        notebook = ttk.Notebook(container)
        notebook.grid(row=0, column=0, sticky="nsew")

        # Tab 1: 按类别汇总
        cat_frame = tk.Frame(notebook, bg="white")
        notebook.add(cat_frame, text="📊 按类别汇总")
        self._build_category_tab(cat_frame)

        # Tab 2: 逐项明细
        detail_frame = tk.Frame(notebook, bg="white")
        notebook.add(detail_frame, text="📋 逐项明细")
        self._build_item_detail_tab(detail_frame)

        # Tab 3: 文件列表
        files_frame = tk.Frame(notebook, bg="white")
        notebook.add(files_frame, text="📁 被删文件列表")
        self._build_file_list_tab(files_frame)

    def _build_category_tab(self, parent):
        """按类别汇总标签页。"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        tree = ttk.Treeview(
            parent,
            columns=("items", "files", "size", "status"),
            show="headings",
            height=8,
        )
        tree.heading("items", text="类别")
        tree.heading("files", text="清理项")
        tree.heading("size", text="删除文件")
        tree.heading("status", text="释放空间")
        tree.column("items", width=180)
        tree.column("files", width=100, anchor="center")
        tree.column("size", width=120, anchor="center")
        tree.column("status", width=120, anchor="center")

        for cs in self.report.category_summaries:
            tree.insert("", "end", values=(
                cs.name,
                cs.item_count,
                f"{cs.file_count} 个",
                cs.size_str,
            ))

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=16)

    def _build_item_detail_tab(self, parent):
        """逐项明细标签页（TreeView）。"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        tree = ttk.Treeview(
            parent,
            columns=("name", "files", "size", "status"),
            show="headings",
            height=12,
        )
        tree.heading("name", text="清理项")
        tree.heading("files", text="文件数")
        tree.heading("size", text="释放大小")
        tree.heading("status", text="状态")
        tree.column("name", width=250)
        tree.column("files", width=100, anchor="center")
        tree.column("size", width=120, anchor="center")
        tree.column("status", width=100, anchor="center")

        for r in self.report.results:
            if r.success:
                status = "✅ 成功"
                size_str = format_size(r.deleted_size)
            else:
                status = f"❌ {r.error or '失败'}"
                size_str = "—"
            tree.insert("", "end", values=(
                r.name,
                r.deleted_files if r.success else "—",
                size_str,
                status,
            ))

        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)

        tree.grid(row=0, column=0, sticky="nsew", padx=16, pady=16)
        scrollbar.grid(row=0, column=1, sticky="ns", pady=16)

    def _build_file_list_tab(self, parent):
        """被删文件列表标签页（带搜索过滤）。"""
        parent.columnconfigure(0, weight=1)
        parent.rowconfigure(1, weight=1)

        # 搜索框
        search_frame = tk.Frame(parent, bg="white")
        search_frame.grid(row=0, column=0, sticky="ew", padx=16, pady=(16, 4))
        search_frame.columnconfigure(1, weight=1)

        tk.Label(
            search_frame, text="🔍 搜索:",
            font=("Microsoft YaHei", 9),
            bg="white", fg="#555",
        ).grid(row=0, column=0, padx=(0, 8))

        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_files())
        search_entry = tk.Entry(
            search_frame, textvariable=self._search_var,
            font=("Microsoft YaHei", 9),
            relief="solid", borderwidth=1,
        )
        search_entry.grid(row=0, column=1, sticky="ew")

        # 统计
        total_file_count = sum(
            len(r.deleted_file_paths) for r in self.report.results if r.success
        )
        self._file_count_label = tk.Label(
            search_frame,
            text=f"共 {total_file_count} 个文件",
            font=("Microsoft YaHei", 9),
            bg="white", fg="#888",
        )
        self._file_count_label.grid(row=0, column=2, padx=8)

        # 文件列表
        list_frame = tk.Frame(parent, bg="white")
        list_frame.grid(row=1, column=0, sticky="nsew", padx=16, pady=(4, 16))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)

        self._files_text = tk.Text(
            list_frame,
            font=("Consolas", 9),
            bg="#fafafa", fg="#333",
            relief="solid", borderwidth=1,
            wrap="none",
        )
        self._files_text.grid(row=0, column=0, sticky="nsew")

        scroll_y = ttk.Scrollbar(list_frame, orient="vertical", command=self._files_text.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self._files_text.configure(yscrollcommand=scroll_y.set)

        scroll_x = ttk.Scrollbar(list_frame, orient="horizontal", command=self._files_text.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")
        self._files_text.configure(xscrollcommand=scroll_x.set)

        # 填充数据
        self._all_file_paths = []
        for r in self.report.results:
            if r.success and r.deleted_file_paths:
                # 分组标题
                self._all_file_paths.append((f"── {r.name} ──", True))
                for fp in r.deleted_file_paths:
                    self._all_file_paths.append((fp, False))
                self._all_file_paths.append(("", False))
        self._filter_files()

    def _filter_files(self):
        """根据搜索词过滤文件列表。"""
        keyword = self._search_var.get().lower()
        self._files_text.delete("1.0", tk.END)

        count = 0
        for text, is_header in self._all_file_paths:
            if is_header or not keyword or keyword in text.lower():
                if is_header:
                    self._files_text.insert(tk.END, text + "\n", "header")
                elif text:
                    self._files_text.insert(tk.END, text + "\n", "file")
                    count += 1
                else:
                    self._files_text.insert(tk.END, "\n")

        self._files_text.tag_config("header", foreground="#2c6fbb", font=("Microsoft YaHei", 9, "bold"))
        self._files_text.tag_config("file", foreground="#555", font=("Consolas", 9))

        self._file_count_label.config(text=f"共 {count} 个文件")
        self._files_text.see("1.0")

    def _build_buttons(self):
        """底部按钮。"""
        frame = tk.Frame(self.win, bg="white", highlightbackground="#e0e4e8", highlightthickness=1)
        frame.grid(row=2, column=0, sticky="ew", padx=16, pady=(8, 16))
        frame.columnconfigure(0, weight=1)

        # 左侧：保存报告
        tk.Button(
            frame, text="💾 保存报告 (.txt)",
            font=("Microsoft YaHei", 9),
            bg="#ecf0f1", fg="#333",
            relief="flat", padx=16, pady=4, cursor="hand2",
            command=self._save_txt,
        ).grid(row=0, column=0, padx=(16, 4), pady=10, sticky="w")

        tk.Button(
            frame, text="💾 保存报告 (.json)",
            font=("Microsoft YaHei", 9),
            bg="#ecf0f1", fg="#333",
            relief="flat", padx=16, pady=4, cursor="hand2",
            command=self._save_json,
        ).grid(row=0, column=1, padx=4, pady=10, sticky="w")

        # 右侧：关闭
        tk.Button(
            frame, text="关闭",
            font=("Microsoft YaHei", 10, "bold"),
            bg="#2c6fbb", fg="white",
            activebackground="#1a4f8a", activeforeground="white",
            relief="flat", padx=24, pady=4, cursor="hand2",
            command=self.win.destroy,
        ).grid(row=0, column=2, padx=(4, 16), pady=10, sticky="e")

    def _save_txt(self):
        self._save_report(as_json=False)

    def _save_json(self):
        self._save_report(as_json=True)

    def _save_report(self, as_json: bool = False):
        default_name = f"wps_cleanup_report_{self.report.timestamp.replace(':', '-').replace(' ', '_')}"
        ext = ".json" if as_json else ".txt"
        filetypes = [
            ("JSON 文件", "*.json") if as_json else ("文本文件", "*.txt"),
            ("所有文件", "*.*"),
        ]

        path = filedialog.asksaveasfilename(
            parent=self.win,
            title="保存清理报告",
            defaultextension=ext,
            filetypes=filetypes,
            initialfile=default_name + ext,
        )
        if not path:
            return

        try:
            content = report_to_json(self.report) if as_json else report_to_text(self.report, True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("保存成功", f"报告已保存到:\n{path}", parent=self.win)
        except Exception as e:
            messagebox.showerror("保存失败", str(e), parent=self.win)
