"""
WPS 磁盘清理工具 - 现代化 Tkinter GUI。

采用左右分栏布局：
  - 左侧：分类导航面板（显示各类别名称、图标、可清理项数量）
  - 右侧：当前类别的可清理项列表（勾选、查看详情）
  - 底部：统计摘要 + 操作按钮 + 进度条
"""

import threading
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional

from .cleaner import clean_selected, CleanResult, WPS_BLOCKED_SENTINEL
from .config import SafetyLevel, Category, CLEANUP_ITEMS
from .scanner import scan_all, get_total_cleanable
from .utils import check_wps_running, format_size
from .report_dialog import ReportDialog


# ── 调色板 ──────────────────────────────────────────────
class Colors:
    BG          = "#f4f6f9"
    CARD        = "#ffffff"
    SIDEBAR_BG  = "#2c3e50"
    SIDEBAR_ACT = "#34495e"
    SIDEBAR_TEXT = "#ecf0f1"
    SIDEBAR_ACCENT = "#3498db"
    SAFE        = "#27ae60"
    CAUTION     = "#e67e22"
    DANGER      = "#e74c3c"
    PRIMARY     = "#2c6fbb"
    PRIMARY_HV  = "#1a4f8a"
    TEXT        = "#2c3e50"
    TEXT_SEC    = "#95a5a6"
    BORDER      = "#e0e4e8"
    SUCCESS_BG  = "#e8f8f0"
    CAUTION_BG  = "#fef5e7"

    @classmethod
    def safety_bg(cls, safety: SafetyLevel) -> str:
        return cls.SUCCESS_BG if safety == SafetyLevel.SAFE else cls.CAUTION_BG

    @classmethod
    def safety_fg(cls, safety: SafetyLevel) -> str:
        return cls.SAFE if safety == SafetyLevel.SAFE else cls.CAUTION


# ── 类别图标 ──────────────────────────────────────────────
CATEGORY_ICONS = {
    Category.PLUGIN_CACHE:  "📦",
    Category.LOCAL_BACKUP:  "💾",
    Category.CLOUD_CACHE:   "☁️",
    Category.FEATURE_CACHE: "⚡",
}


class WPSCleanupApp:
    """WPS 磁盘清理 GUI 应用。"""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("WPS Office 磁盘清理工具")
        self.root.geometry("960x680")
        self.root.minsize(840, 580)
        self.root.configure(bg=Colors.BG)

        from .config import detect_wps_version
        self.version = detect_wps_version()

        # 数据
        self.scan_results: List[dict] = []
        self.check_states: Dict[int, tk.BooleanVar] = {}
        self._cleaning = False

        # 当前选中的分类（None = 全部）
        self._selected_category: Optional[Category] = None

        # 控件引用
        self._sidebar_btns: Dict[Category, tk.Button] = {}
        self._right_frame: Optional[tk.Frame] = None
        self._progress_bar: Optional[ttk.Progressbar] = None
        self._progress_label: Optional[tk.Label] = None
        self._summary_label: Optional[tk.Label] = None
        self._status_label: Optional[tk.Label] = None
        self._clean_btn: Optional[tk.Button] = None
        self._select_all_var = tk.BooleanVar(value=True)

        self._build_ui()
        self._perform_scan()

    # ═══════════════════════════════════════════════════════
    #  UI 构建
    # ═══════════════════════════════════════════════════════

    def _build_ui(self):
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_header()
        self._build_sidebar()
        self._build_right_panel()
        self._build_bottom()

    def _build_header(self):
        """顶部标题栏。"""
        header = tk.Frame(self.root, bg=Colors.CARD, height=56)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=0, pady=(0, 1))
        header.columnconfigure(1, weight=1)

        tk.Label(
            header,
            text="  🧹  WPS Office 磁盘清理工具",
            font=("Microsoft YaHei", 13, "bold"),
            bg=Colors.CARD, fg=Colors.TEXT,
        ).grid(row=0, column=0, padx=(20, 8), pady=14, sticky="w")

        self._status_label = tk.Label(
            header, text="就绪",
            font=("Microsoft YaHei", 9),
            bg=Colors.CARD, fg=Colors.TEXT_SEC, anchor="e",
        )
        self._status_label.grid(row=0, column=1, padx=8, pady=14, sticky="e")

        tk.Label(
            header, text=f"v{self.version}",
            font=("Microsoft YaHei", 8),
            bg=Colors.CARD, fg="#bbb",
        ).grid(row=0, column=2, padx=(4, 20), pady=14, sticky="e")

        tk.Frame(header, bg=Colors.BORDER, height=1).grid(
            row=1, column=0, columnspan=3, sticky="ew"
        )

    def _build_sidebar(self):
        """左侧分类导航栏。"""
        side = tk.Frame(self.root, bg=Colors.SIDEBAR_BG, width=180)
        side.grid(row=1, column=0, sticky="ns", padx=(0, 0))
        side.grid_propagate(False)

        tk.Label(
            side, text="清理分类",
            font=("Microsoft YaHei", 10, "bold"),
            bg=Colors.SIDEBAR_BG, fg=Colors.SIDEBAR_TEXT,
        ).pack(fill="x", padx=16, pady=(16, 8))

        tk.Frame(side, bg=Colors.SIDEBAR_ACCENT, height=2).pack(
            fill="x", padx=16, pady=(0, 12)
        )

        btn_all = tk.Button(
            side,
            text="📋  全部项目",
            font=("Microsoft YaHei", 10),
            bg=Colors.SIDEBAR_ACCENT, fg="white",
            activebackground=Colors.SIDEBAR_ACCENT, activeforeground="white",
            relief="flat", anchor="w", padx=12, pady=6,
            cursor="hand2", bd=0,
            command=lambda: self._select_category(None),
        )
        btn_all.pack(fill="x", padx=8, pady=(0, 2))
        self._sidebar_btn_all = btn_all

        for cat in Category:
            icon = CATEGORY_ICONS.get(cat, "📁")
            btn = tk.Button(
                side,
                text=f"  {icon}  {cat.value}",
                font=("Microsoft YaHei", 10),
                bg=Colors.SIDEBAR_BG, fg=Colors.SIDEBAR_TEXT,
                activebackground=Colors.SIDEBAR_ACT, activeforeground="white",
                relief="flat", anchor="w", padx=12, pady=6,
                cursor="hand2", bd=0,
                command=lambda c=cat: self._select_category(c),
            )
            btn.pack(fill="x", padx=8, pady=1)
            self._sidebar_btns[cat] = btn

        tk.Frame(side, bg=Colors.SIDEBAR_BG).pack(fill="both", expand=True)

    def _build_right_panel(self):
        """右侧内容区（滚动列表）。"""
        container = tk.Frame(self.root, bg=Colors.BG)
        container.grid(row=1, column=1, sticky="nsew", padx=12, pady=12)
        container.columnconfigure(0, weight=1)
        container.rowconfigure(0, weight=1)

        canvas = tk.Canvas(container, bg=Colors.BG, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        self._right_frame = tk.Frame(canvas, bg=Colors.BG)

        self._right_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=self._right_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)

    def _build_bottom(self):
        """底部操作栏。"""
        bottom = tk.Frame(self.root, bg=Colors.CARD, height=52)
        bottom.grid(row=2, column=0, columnspan=2, sticky="ew")
        bottom.columnconfigure(1, weight=1)

        tk.Frame(bottom, bg=Colors.BORDER, height=1).grid(
            row=0, column=0, columnspan=6, sticky="ew"
        )

        ttk.Checkbutton(
            bottom, text="全选", variable=self._select_all_var,
            command=self._toggle_all,
        ).grid(row=1, column=0, padx=(16, 4), pady=12, sticky="w")

        self._summary_label = tk.Label(
            bottom, text="",
            font=("Microsoft YaHei", 9),
            bg=Colors.CARD, fg=Colors.TEXT_SEC,
        )
        self._summary_label.grid(row=1, column=1, padx=8, pady=12, sticky="w")

        self._progress_bar = ttk.Progressbar(
            bottom, mode="determinate", length=160
        )
        self._progress_label = tk.Label(
            bottom, text="", font=("Microsoft YaHei", 8),
            bg=Colors.CARD, fg=Colors.TEXT_SEC,
        )

        self._refresh_btn = tk.Button(
            bottom, text="🔄 重新扫描",
            font=("Microsoft YaHei", 9),
            bg="#ecf0f1", fg=Colors.TEXT,
            relief="flat", padx=14, pady=3, cursor="hand2",
            command=self._perform_scan,
        )
        self._refresh_btn.grid(row=1, column=2, padx=4, pady=12, sticky="e")

        self._clean_btn = tk.Button(
            bottom, text="🧹  开始清理",
            font=("Microsoft YaHei", 10, "bold"),
            bg=Colors.PRIMARY, fg="white",
            activebackground=Colors.PRIMARY_HV, activeforeground="white",
            relief="flat", padx=20, pady=4, cursor="hand2",
            command=self._confirm_clean,
        )
        self._clean_btn.grid(row=1, column=3, padx=(4, 16), pady=12, sticky="e")

    # ═══════════════════════════════════════════════════════
    #  分类切换
    # ═══════════════════════════════════════════════════════

    def _select_category(self, category: Optional[Category]):
        """切换选中的分类，刷新右侧列表。"""
        self._selected_category = category

        for cat, btn in self._sidebar_btns.items():
            is_active = (cat == category)
            btn.configure(
                bg=Colors.SIDEBAR_ACCENT if is_active else Colors.SIDEBAR_BG,
                fg="white" if is_active else Colors.SIDEBAR_TEXT,
            )
        is_all = category is None
        self._sidebar_btn_all.configure(
            bg=Colors.SIDEBAR_ACCENT if is_all else Colors.SIDEBAR_BG,
            fg="white" if is_all else Colors.SIDEBAR_TEXT,
        )

        self._render_items()

    # ═══════════════════════════════════════════════════════
    #  扫描
    # ═══════════════════════════════════════════════════════

    def _perform_scan(self):
        self._set_busy(True, "⏳ 正在扫描目录...")
        self._summary_label.config(text="")

        def scan():
            results = scan_all(self.version)
            self.root.after(0, self._on_scan_complete, results)

        threading.Thread(target=scan, daemon=True).start()

    def _on_scan_complete(self, results):
        self.scan_results = results
        self._render_items()
        self._update_summary()

        running = check_wps_running()
        if running:
            self._status_label.config(
                text=f"⚠️ WPS 进程正在运行 ({', '.join(running)})，建议关闭后再清理",
                fg=Colors.CAUTION,
            )
        else:
            self._status_label.config(text="扫描完成 ✓", fg=Colors.SAFE)

        self._set_busy(False)

    # ═══════════════════════════════════════════════════════
    #  渲染列表
    # ═══════════════════════════════════════════════════════

    def _render_items(self):
        """根据选中的分类渲染右侧列表。"""
        for w in self._right_frame.winfo_children():
            w.destroy()
        self.check_states.clear()

        if self._selected_category is None:
            items = self.scan_results
        else:
            items = [
                r for r in self.scan_results
                if r["item"].category == self._selected_category
            ]

        current_cat = None
        for item_data in items:
            cat = item_data["item"].category
            if cat != current_cat:
                current_cat = cat
                self._render_category_header(item_data)
            self._render_item_card(item_data)

        if not items:
            tk.Label(
                self._right_frame,
                text="  此分类下没有可清理的项目  ",
                font=("Microsoft YaHei", 10),
                bg=Colors.BG, fg=Colors.TEXT_SEC,
            ).pack(padx=20, pady=40)

    def _render_category_header(self, item_data: dict):
        """渲染分类标题行。"""
        cat = item_data["item"].category
        icon = CATEGORY_ICONS.get(cat, "📁")
        has_caution = any(
            r["item"].safety == SafetyLevel.CAUTION and
            (self._selected_category is None or r["item"].category == self._selected_category)
            for r in self.scan_results
        )

        header = tk.Frame(self._right_frame, bg=Colors.CARD)
        header.pack(fill="x", pady=(16, 4), padx=0)
        header.columnconfigure(0, weight=1)

        tk.Label(
            header,
            text=f"{icon}  {cat.value}",
            font=("Microsoft YaHei", 12, "bold"),
            bg=Colors.CARD, fg=Colors.TEXT,
        ).grid(row=0, column=0, sticky="w", padx=16, pady=(10, 0))

        if has_caution:
            tk.Label(
                header,
                text="⚠️ 部分项包含重要数据，请确认后再清理",
                font=("Microsoft YaHei", 8),
                bg=Colors.CARD, fg=Colors.CAUTION,
            ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        tk.Frame(self._right_frame, bg=Colors.BORDER, height=1).pack(
            fill="x", padx=0
        )

    def _render_item_card(self, item_data: dict):
        """渲染单个可清理项的卡片。"""
        item = item_data["item"]
        idx = next(
            i for i, r in enumerate(self.scan_results)
            if r["resolved_path"] == item_data["resolved_path"]
        )

        exists = item_data["exists"]
        safety_bg = Colors.safety_bg(item.safety)
        safety_fg = Colors.safety_fg(item.safety)
        safety_text = "可安全删除" if item.safety == SafetyLevel.SAFE else "谨慎清理"

        card = tk.Frame(
            self._right_frame, bg=Colors.CARD,
            highlightbackground=Colors.BORDER, highlightthickness=1,
        )
        card.pack(fill="x", pady=3, padx=2)
        card.columnconfigure(1, weight=1)

        pad = 14
        var = tk.BooleanVar(value=True)
        self.check_states[idx] = var

        cb = ttk.Checkbutton(card, variable=var)
        cb.grid(row=0, column=0, padx=(pad, 4), pady=(pad, 0), sticky="n")

        tk.Label(
            card, text=item.name,
            font=("Microsoft YaHei", 10, "bold"),
            bg=Colors.CARD, fg=Colors.TEXT, anchor="w",
        ).grid(row=0, column=1, sticky="w", pady=(pad, 0))

        lbl_safety = tk.Label(
            card, text=safety_text,
            font=("Microsoft YaHei", 8),
            bg=safety_bg, fg=safety_fg,
            padx=6, pady=1,
        )
        lbl_safety.grid(row=0, column=2, padx=8, pady=(pad, 0), sticky="e")

        if exists:
            sz_text = format_size(item_data["total_size"])
            tk.Label(
                card, text=sz_text,
                font=("Microsoft YaHei", 9, "bold"),
                bg=Colors.CARD, fg=Colors.TEXT,
            ).grid(row=0, column=3, padx=(0, pad), pady=(pad, 0), sticky="e")
        else:
            tk.Label(
                card, text="—",
                font=("Microsoft YaHei", 9),
                bg=Colors.CARD, fg="#ccc",
            ).grid(row=0, column=3, padx=(0, pad), pady=(pad, 0), sticky="e")

        path_display = item_data["resolved_path"]
        if len(path_display) > 80:
            path_display = "…" + path_display[-78:]
        path_color = Colors.TEXT_SEC if exists else "#ddd"
        tk.Label(
            card, text=path_display,
            font=("Microsoft YaHei", 8),
            bg=Colors.CARD, fg=path_color, anchor="w",
        ).grid(row=1, column=1, columnspan=3, sticky="w", padx=(0, pad), pady=(2, 6))

        if item_data.get("error"):
            tk.Label(
                card, text=f"⚠ {item_data['error']}",
                font=("Microsoft YaHei", 8),
                bg=Colors.CARD, fg=Colors.DANGER,
            ).grid(row=2, column=1, columnspan=3, sticky="w", padx=(0, pad), pady=(0, pad))

        if item.note and exists:
            tk.Label(
                card, text=f"💡 {item.note}",
                font=("Microsoft YaHei", 8, "italic"),
                bg=Colors.CARD, fg="#aaa",
            ).grid(row=3, column=1, columnspan=3, sticky="w", padx=(0, pad), pady=(0, pad))

    # ═══════════════════════════════════════════════════════
    #  交互逻辑
    # ═══════════════════════════════════════════════════════

    def _toggle_all(self):
        val = self._select_all_var.get()
        for var in self.check_states.values():
            var.set(val)

    def _update_summary(self):
        total_files, total_size = get_total_cleanable(self.scan_results)
        selected_count = sum(
            1 for idx, v in self.check_states.items()
            if v.get() and self.scan_results[idx]["exists"]
        )
        exists_count = sum(1 for r in self.scan_results if r["exists"])
        self._summary_label.config(
            text=f"共 {exists_count} 项 / {format_size(total_size)} 可清理"
            f"  |  已选 {selected_count} 项"
        )

    def _confirm_clean(self):
        selected = [
            (idx, data) for idx, data in enumerate(self.scan_results)
            if self.check_states.get(idx, tk.BooleanVar(value=False)).get()
            and data["exists"]
        ]

        if not selected:
            messagebox.showinfo("提示", "没有选中任何需要清理的项目。")
            return

        total_files = sum(d["file_count"] for _, d in selected)
        total_size = sum(d["total_size"] for _, d in selected)
        names = "\n".join(
            f"  • {d['item'].name}  ({format_size(d['total_size'])})"
            for _, d in selected
        )

        caution_items = [d for _, d in selected if d["item"].safety == SafetyLevel.CAUTION]
        caution_warning = ""
        if caution_items:
            caution_names = "\n".join(f"  • {d['item'].name}" for d in caution_items)
            caution_warning = (
                f"\n\n⚠️ 以下项目包含重要数据，请确认已备份：\n{caution_names}"
            )

        msg = (
            f"确定要清理以下 {len(selected)} 个项目吗？\n\n"
            f"{names}\n\n"
            f"总计: {total_files} 个文件, {format_size(total_size)}"
            f"{caution_warning}"
        )

        if not messagebox.askyesno("确认清理", msg, icon="warning"):
            return

        self._start_clean(selected)

    def _start_clean(self, selected: List):
        if self._cleaning:
            return
        self._cleaning = True

        total = len(selected)
        self._progress_bar["maximum"] = total
        self._progress_bar["value"] = 0
        self._show_progress(True)
        self._set_busy(True, "⏳ 正在清理...")
        self._clean_btn.config(state="disabled", text="⏳ 清理中...")

        items_to_clean = [data for _, data in selected]

        def do_clean():
            import time
            start_time = time.time()
            cleaned = 0

            def progress(msg: str):
                nonlocal cleaned
                cleaned += 1
                self.root.after(0, self._progress_bar.configure, {"value": cleaned})
                self.root.after(
                    0, self._progress_label.config,
                    {"text": f"{cleaned}/{total}  {msg}"}
                )
                self.root.after(
                    0, self._status_label.config,
                    {"text": msg, "fg": Colors.TEXT}
                )

            results = clean_selected(
                items_to_clean,
                use_recycle_bin=True,
                skip_if_wps_running=True,
                progress_callback=progress,
            )
            duration = time.time() - start_time
            self.root.after(0, self._on_clean_done, results, duration)

        threading.Thread(target=do_clean, daemon=True).start()

    def _on_clean_done(self, results: List[CleanResult], duration: float = 0.0):
        self._cleaning = False
        self._show_progress(False)
        self._set_busy(False)
        self._clean_btn.config(state="normal", text="🧹  开始清理")

        # 检查是否被 WPS 拦截
        if (
            len(results) == 1
            and results[0].error == WPS_BLOCKED_SENTINEL
        ):
            messagebox.showwarning(
                "WPS 正在运行",
                "检测到 WPS 进程正在运行，请先关闭所有 WPS 程序后再清理。\n\n"
                "关闭 WPS 后可以点击「重新扫描」再次检查。",
            )
            self._status_label.config(text="⚠️ 因 WPS 运行中跳过清理", fg=Colors.CAUTION)
            self._perform_scan()
            return

        # 显示详细报告弹窗
        self.root.after(0, lambda: ReportDialog(self.root, results, duration))

        self._perform_scan()

    # ═══════════════════════════════════════════════════════
    #  UI 状态辅助
    # ═══════════════════════════════════════════════════════

    def _set_busy(self, busy: bool, status_text: str = ""):
        state = "disabled" if busy else "normal"
        self._refresh_btn.config(state=state)
        if status_text:
            self._status_label.config(text=status_text)

    def _show_progress(self, show: bool):
        if show:
            self._progress_bar.grid(row=1, column=2, padx=4, pady=12, sticky="e")
            self._progress_label.grid(row=1, column=3, padx=(0, 4), pady=12, sticky="e")
        else:
            self._progress_bar.grid_forget()
            self._progress_label.grid_forget()

    # ═══════════════════════════════════════════════════════
    #  启动
    # ═══════════════════════════════════════════════════════

    def run(self):
        self.root.mainloop()
