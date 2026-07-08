"""
提示词管理工具 - 主程序 v2 (UI全面美化)
基于 tkinter + SQLite 的本地化提示词管理器
"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog, colorchooser
import webbrowser, os, sys, json, threading
import urllib.request, urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from database import (
    init_db, get_prompts, get_prompt, add_prompt, update_prompt,
    delete_prompt, toggle_pin_prompt, get_categories, add_category,
    rename_category, delete_category, get_tags, add_tag, rename_tag,
    delete_tag, get_colors, add_color, rename_color, delete_color,
    get_prompt_tags, set_prompt_tags, move_prompt_to_category,
    set_setting, get_setting, batch_delete_prompts,
    batch_move_prompts, batch_set_color, batch_set_tags,
    get_navigation, add_navigation, update_navigation, delete_navigation,
    batch_update_sort_orders, export_prompts_csv, import_prompts_csv)

# ═══════════════════ 现代配色系统 ═══════════════════
C = {
    # 主背景 — 柔和渐变感
    "bg":           "#F0F2F5",
    "card":         "#FFFFFF",
    "card_alt":     "#F8F9FB",
    # 工具栏/导航
    "bar_bg":       "#FFFFFF",
    "bar_bottom":   "#E8ECF1",
    # 强调色
    "accent":       "#6366F1",   # Indigo 500
    "accent_light": "#EEF2FF",
    "accent_hover": "#4F46E5",
    "success":      "#10B981",
    "danger":       "#EF4444",
    "warning":      "#F59E0B",
    # 文字
    "text":         "#1E293B",
    "text_sec":     "#64748B",
    "text_muted":   "#94A3B8",
    "text_on_accent":"#FFFFFF",
    # 边框/分隔
    "border":       "#E2E8F0",
    "divider":      "#F1F5F9",
    # Tree 选择
    "tree_sel":     "#E0E7FF",
    "tree_sel_text":"#3730A3",
    "tree_hover":   "#F1F5F9",
    "tree_stripe":  "#F8FAFC",
}

FONT = {
    "ui":    ("Microsoft YaHei UI", 9),
    "ui_bold": ("Microsoft YaHei UI", 9, "bold"),
    "header": ("Microsoft YaHei UI", 11, "bold"),
    "title":  ("Microsoft YaHei UI", 13, "bold"),
    "code":   ("Cascadia Code", 10),
    "tree":   ("Microsoft YaHei UI", 9),
    "search": ("Microsoft YaHei UI", 10),
    "status": ("Microsoft YaHei UI", 8),
    "nav":    ("Microsoft YaHei UI", 9),
}


class HoverButton(tk.Button):
    """带 hover 效果的按钮"""
    def __init__(self, parent, hover_bg=None, hover_fg=None, origin_bg=None, origin_fg=None, **kw):
        super().__init__(parent, **kw)
        self.origin_bg = origin_bg or kw.get("bg", C["card"])
        self.origin_fg = origin_fg or kw.get("fg", C["text"])
        self.hover_bg = hover_bg or self.origin_bg
        self.hover_fg = hover_fg or self.origin_fg
        self.bind("<Enter>", self._enter)
        self.bind("<Leave>", self._leave)
    def _enter(self, e):
        if self["state"] != "disabled":
            self.configure(bg=self.hover_bg, fg=self.hover_fg)
    def _leave(self, e):
        self.configure(bg=self.origin_bg, fg=self.origin_fg)


class PromptManager:
    def __init__(self, root):
        self.root = root
        self.root.title("✨ 提示词管理工具")
        self.root.geometry("1340x850")
        self.root.minsize(960, 650)
        self.root.configure(bg=C["bg"])

        # ═══ 全局 ttk 主题 ═══
        self._setup_ttk_theme()

        # 状态
        self.current_category_id = None
        self.current_tag_id = None
        self.current_color_id = None
        self.selected_prompt_id = None
        self.click_to_copy = tk.BooleanVar(value=False)
        self.window_topmost = tk.BooleanVar(value=False)
        self.editing_prompt_id = None
        self.api_provider = tk.StringVar(value=get_setting("api_provider", "openai"))
        self._drag_data = {"item": None, "start": False}

        init_db()
        self._build_status_bar()
        self._build_toolbar()
        self._build_main_layout()
        self._build_all_menus()
        self._build_navigation_bar()
        self.refresh_all()
        self.window_topmost.trace_add("write", self._toggle_topmost)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ═══════════════ ttk 主题 ═══════════════
    def _setup_ttk_theme(self):
        style = ttk.Style()
        if "clam" in style.theme_names(): style.theme_use("clam")

        # TreeView
        style.configure("Modern.Treeview",
            background=C["card"], foreground=C["text"],
            fieldbackground=C["card"], borderwidth=0, font=FONT["tree"],
            rowheight=30)
        style.configure("Modern.Treeview.Heading",
            background=C["card_alt"], foreground=C["text_sec"],
            borderwidth=0, font=FONT["ui_bold"], padding=(8, 6))
        style.map("Modern.Treeview.Heading",
            background=[("active", C["accent_light"])])
        style.map("Modern.Treeview",
            background=[("selected", C["tree_sel"])],
            foreground=[("selected", C["tree_sel_text"])])

        # Notebook
        style.configure("Modern.TNotebook",
            background=C["bg"], borderwidth=0)
        style.configure("Modern.TNotebook.Tab",
            background=C["card"], foreground=C["text_sec"],
            borderwidth=0, font=FONT["ui_bold"], padding=(14, 8))
        style.map("Modern.TNotebook.Tab",
            background=[("selected", C["accent"]), ("active", C["accent_light"])],
            foreground=[("selected", C["text_on_accent"]), ("active", C["accent"])])

        # PanedWindow
        style.configure("Modern.TPanedwindow", background=C["border"])
        # Scrollbar
        style.configure("Modern.Vertical.TScrollbar",
            background=C["card"], troughcolor=C["bg"], borderwidth=0, arrowsize=0)
        style.configure("Modern.Horizontal.TScrollbar",
            background=C["card"], troughcolor=C["bg"], borderwidth=0, arrowsize=0)

        # Combobox
        style.configure("Modern.TCombobox",
            background=C["card"], fieldbackground=C["card"],
            foreground=C["text"], borderwidth=1, font=FONT["ui"])

    # ═══════════════ 状态栏 ═══════════════
    def _build_status_bar(self):
        self.status_bar = tk.Frame(self.root, bg=C["accent"], height=3)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, after=self.root.winfo_children())
        self.status_frame = tk.Frame(self.root, bg=C["bar_bottom"], height=26)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        self.status_frame.pack_propagate(False)
        self.status_label = tk.Label(self.status_frame, text="就绪", font=FONT["status"],
                                      bg=C["bar_bottom"], fg=C["text_sec"], anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=12, pady=2)
        self.status_count = tk.Label(self.status_frame, text="", font=FONT["status"],
                                      bg=C["bar_bottom"], fg=C["text_muted"], anchor=tk.E)
        self.status_count.pack(side=tk.RIGHT, padx=12, pady=2)

    def _set_status(self, text, accent=False, duration=3000):
        self.status_label.configure(text=text,
            fg=C["text_on_accent"] if accent else C["text_sec"])
        if accent:
            self.status_bar.configure(bg=C["accent"])
            self.root.after(duration, lambda: (
                self.status_bar.configure(bg=C["border"]),
                self.status_label.configure(fg=C["text_sec"])
            ))

    # ═══════════════ 工具栏（全新设计） ═══════════════
    def _build_toolbar(self):
        tb = tk.Frame(self.root, bg=C["bar_bg"], height=48)
        tb.pack(fill=tk.X, side=tk.TOP)

        # 左侧：搜索
        search_frame = tk.Frame(tb, bg=C["accent_light"])
        search_frame.pack(side=tk.LEFT, padx=(14, 0), pady=8)

        self.search_icon = tk.Label(search_frame, text="🔍", bg=C["accent_light"],
                                     font=("Segoe UI", 10))
        self.search_icon.pack(side=tk.LEFT, padx=(8, 2))

        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._refresh_tree())
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
            font=FONT["search"], width=28, relief=tk.FLAT,
            bg=C["accent_light"], fg=C["text"],
            insertbackground=C["accent"], borderwidth=0)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 10), pady=3, ipady=2)
        # 搜索框 placeholder
        self._search_placeholder = True
        self.search_entry.bind("<FocusIn>", self._search_focus_in)
        self.search_entry.bind("<FocusOut>", self._search_focus_out)
        self._set_search_placeholder()

        # 分隔
        ttk.Separator(tb, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=14, pady=10)

        # API 区域
        api_frame = tk.Frame(tb, bg=C["bar_bg"])
        api_frame.pack(side=tk.LEFT, pady=8)
        tk.Label(api_frame, text="API", font=FONT["status"], bg=C["bar_bg"],
                 fg=C["text_muted"]).pack(side=tk.LEFT, padx=(0, 4))
        api_combo = ttk.Combobox(api_frame, textvariable=self.api_provider,
            values=["openai", "deepseek", "claude", "custom"],
            state="readonly", width=10, font=FONT["ui"], style="Modern.TCombobox")
        api_combo.pack(side=tk.LEFT, padx=(0, 4))
        self.api_provider.trace_add("write", lambda *a: set_setting("api_provider", self.api_provider.get()))

        HoverButton(api_frame, text="⚙", font=("Segoe UI", 10), bg=C["bar_bg"],
            fg=C["text_sec"], hover_bg=C["accent_light"], hover_fg=C["accent"],
            relief=tk.FLAT, cursor="hand2", bd=0,
            command=self._config_api, width=3).pack(side=tk.LEFT)

        # 右侧操作按钮
        right = tk.Frame(tb, bg=C["bar_bg"])
        right.pack(side=tk.RIGHT, padx=6, pady=6)

        for text, cmd, accent_btn in [
            ("单击复制", None, False),
            ("窗口置顶", None, False),
        ]:
            if text == "单击复制":
                cb = tk.Checkbutton(right, text="单击复制", variable=self.click_to_copy,
                    bg=C["bar_bg"], fg=C["text_sec"], font=FONT["status"],
                    selectcolor=C["accent_light"], cursor="hand2",
                    activebackground=C["bar_bg"], activeforeground=C["accent"],
                    relief=tk.FLAT, bd=0, padx=4)
                cb.pack(side=tk.LEFT, padx=2)
            elif text == "窗口置顶":
                cb = tk.Checkbutton(right, text="窗口置顶", variable=self.window_topmost,
                    bg=C["bar_bg"], fg=C["text_sec"], font=FONT["status"],
                    selectcolor=C["accent_light"], cursor="hand2",
                    activebackground=C["bar_bg"], activeforeground=C["accent"],
                    relief=tk.FLAT, bd=0, padx=4)
                cb.pack(side=tk.LEFT, padx=2)

        # 中间：新建/导入/导出
        mid = tk.Frame(tb, bg=C["bar_bg"])
        mid.pack(side=tk.RIGHT, padx=10, pady=6)
        for text, cmd in [
            ("➕ 新建", self._add_prompt),
            ("📥 导入", self._import_csv),
            ("📤 导出全部", lambda: self._export_csv(all=True)),
        ]:
            btn = HoverButton(mid, text=text, font=FONT["nav"],
                bg=C["card_alt"], fg=C["text"], relief=tk.FLAT,
                cursor="hand2", bd=0, padx=10, pady=3,
                hover_bg=C["accent_light"], hover_fg=C["accent"],
                command=cmd)
            btn.pack(side=tk.LEFT, padx=2)

    def _set_search_placeholder(self):
        if not self.search_var.get():
            self.search_var.set("搜索标题或正文…")
            self.search_entry.configure(fg=C["text_muted"])
            self._search_placeholder = True

    def _search_focus_in(self, e):
        if self._search_placeholder:
            self.search_var.set("")
            self.search_entry.configure(fg=C["text"])
            self._search_placeholder = False

    def _search_focus_out(self, e):
        if not self.search_var.get().strip():
            self._set_search_placeholder()

    # ═══════════════ 主布局 ═══════════════
    def _build_main_layout(self):
        self.main_pw = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL, style="Modern.TPanedwindow")
        self.main_pw.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)
        lf = tk.Frame(self.main_pw, bg=C["bg"])
        rf = tk.Frame(self.main_pw, bg=C["bg"])
        self.main_pw.add(lf, weight=3)
        self.main_pw.add(rf, weight=1)
        self._build_left(lf)
        self._build_right(rf)

    def _build_left(self, parent):
        pw = ttk.PanedWindow(parent, orient=tk.VERTICAL, style="Modern.TPanedwindow")
        pw.pack(fill=tk.BOTH, expand=True)

        # 上：Tree
        tl = tk.Frame(pw, bg=C["card"])
        pw.add(tl, weight=3)
        self._build_tree(tl)

        # 下：编辑区（卡片风格）
        ef = tk.Frame(pw, bg=C["bg"])
        pw.add(ef, weight=1)
        self._build_editor(ef)

    def _build_tree(self, parent):
        # 顶部装饰条
        top_bar = tk.Frame(parent, bg=C["accent"], height=2)
        top_bar.pack(fill=tk.X, side=tk.TOP)

        cols = ("id", "pinned", "title", "content", "category", "tags", "color")
        self.tree = ttk.Treeview(parent, columns=cols, show="headings",
            selectmode="extended", style="Modern.Treeview")
        headings = {"id": "#", "pinned": "", "title": "标题",
                     "content": "提示词内容", "category": "分类",
                     "tags": "标签", "color": "背景色"}
        widths = {"id": 38, "pinned": 26, "title": 180, "content": 320,
                  "category": 80, "tags": 100, "color": 60}
        stretch = {"id": False, "pinned": False, "title": True,
                   "content": True, "category": False, "tags": True, "color": False}
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, width=widths[c], minwidth=20, stretch=stretch[c])

        sy = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview, style="Modern.Vertical.TScrollbar")
        sx = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=self.tree.xview, style="Modern.Horizontal.TScrollbar")
        self.tree.configure(yscrollcommand=sy.set, xscrollcommand=sx.set)
        self.tree.grid(row=0, column=0, sticky="nsew", padx=(0, 0), pady=(2, 0))
        sy.grid(row=0, column=1, sticky="ns", pady=(2, 0))
        sx.grid(row=1, column=0, sticky="ew")
        parent.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        # 事件
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Double-1>", self._on_tree_double)
        self.tree.bind("<Button-3>", self._on_tree_right)
        self.tree.bind("<Control-a>", lambda e: (self.tree.selection_set(self.tree.get_children()), "break")[1])
        self.tree.bind("<ButtonPress-1>", self._on_drag_start, add="+")
        self.tree.bind("<B1-Motion>", self._on_drag_motion, add="+")
        self.tree.bind("<ButtonRelease-1>", self._on_drag_release, add="+")

    def _build_editor(self, parent):
        # 编辑区卡片
        card = tk.Frame(parent, bg=C["card"])
        card.pack(fill=tk.BOTH, expand=True, padx=6, pady=(4, 6))
        # 顶部装饰
        tk.Frame(card, bg=C["accent"], height=2).pack(fill=tk.X)

        hdr = tk.Frame(card, bg=C["card"])
        hdr.pack(fill=tk.X, padx=14, pady=(10, 0))
        tk.Label(hdr, text="📝 编辑区", font=FONT["header"], bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)
        tk.Label(hdr, text="所选提示词自动加载，编辑后自动保存", font=FONT["status"],
                 bg=C["card"], fg=C["text_muted"]).pack(side=tk.LEFT, padx=10)

        # 标题
        tk.Label(card, text="标题", font=FONT["ui_bold"], bg=C["card"], fg=C["text"]).pack(
            anchor=tk.W, padx=14, pady=(10, 0))
        tf = tk.Frame(card, bg=C["card_alt"])
        tf.pack(fill=tk.X, padx=14, pady=4)
        self.title_var = tk.StringVar()
        self.title_entry = tk.Entry(tf, textvariable=self.title_var,
            font=("Microsoft YaHei UI", 11), relief=tk.FLAT,
            bg=C["card_alt"], fg=C["text"],
            insertbackground=C["accent"], borderwidth=0)
        self.title_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=10, pady=3)
        self.title_entry.bind("<KeyRelease>", lambda e: self._auto_save())

        HoverButton(tf, text="✨ 润色", font=FONT["ui"],
            bg=C["accent_light"], fg=C["accent"], relief=tk.FLAT,
            cursor="hand2", bd=0, padx=12, pady=4,
            hover_bg=C["accent"], hover_fg=C["text_on_accent"],
            command=self._polish).pack(side=tk.RIGHT, padx=8, pady=3)

        # 正文
        tk.Label(card, text="正文", font=FONT["ui_bold"], bg=C["card"], fg=C["text"]).pack(
            anchor=tk.W, padx=14, pady=(8, 0))

        ctf = tk.Frame(card, bg=C["card_alt"])
        ctf.pack(fill=tk.BOTH, expand=True, padx=14, pady=(4, 0))
        self.content_text = tk.Text(ctf, font=("Microsoft YaHei UI", 10),
            relief=tk.FLAT, bg=C["card_alt"], fg=C["text"],
            wrap=tk.WORD, borderwidth=0, padx=12, pady=10,
            insertbackground=C["accent"],
            selectbackground=C["tree_sel"], selectforeground=C["tree_sel_text"])
        self.content_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.content_text.bind("<KeyRelease>", lambda e: self._auto_save())
        cs = ttk.Scrollbar(ctf, command=self.content_text.yview, style="Modern.Vertical.TScrollbar")
        cs.pack(side=tk.RIGHT, fill=tk.Y)
        self.content_text.configure(yscrollcommand=cs.set)

        # 底部按钮
        bf = tk.Frame(card, bg=C["card"])
        bf.pack(fill=tk.X, padx=14, pady=(8, 10))
        HoverButton(bf, text="💾 保存", font=FONT["ui_bold"],
            bg=C["accent"], fg=C["text_on_accent"], relief=tk.FLAT,
            cursor="hand2", bd=0, padx=20, pady=5,
            hover_bg=C["accent_hover"], hover_fg=C["text_on_accent"],
            command=self._save_edit).pack(side=tk.RIGHT)
        HoverButton(bf, text="🚀 提交给AI", font=FONT["ui"],
            bg=C["card"], fg=C["accent"], relief=tk.FLAT,
            cursor="hand2", bd=0, padx=14, pady=5,
            hover_bg=C["accent_light"], hover_fg=C["accent"],
            command=self._submit_current).pack(side=tk.RIGHT, padx=4)

    def _submit_current(self):
        """当前编辑区内容直接提交"""
        content = self.content_text.get("1.0", "end-1c")
        if not content.strip():
            messagebox.showinfo("提示", "编辑区无内容"); return
        self._call_ai(content, self._show_ai_result)

    # ═══════════════ 右侧面板 ═══════════════
    def _build_right(self, parent):
        self.rnb = ttk.Notebook(parent, style="Modern.TNotebook")
        self.rnb.pack(fill=tk.BOTH, expand=True, padx=(2, 4), pady=4)
        self._build_cat_tab()
        self._build_tag_tab()
        self._build_color_tab()

    def _section_header(self, parent, text, emoji):
        h = tk.Frame(parent, bg=C["card"])
        h.pack(fill=tk.X, padx=10, pady=(8, 2))
        tk.Label(h, text=f"{emoji}  {text}", font=FONT["header"],
                 bg=C["card"], fg=C["text"]).pack(side=tk.LEFT)

    def _build_cat_tab(self):
        frame = tk.Frame(self.rnb, bg=C["card"])
        self.rnb.add(frame, text="📁  分类")

        self.cat_listbox = tk.Listbox(frame, font=("Microsoft YaHei UI", 10),
            bg=C["card"], fg=C["text"],
            selectbackground=C["tree_sel"], selectforeground=C["tree_sel_text"],
            relief=tk.FLAT, activestyle="none", borderwidth=0,
            highlightthickness=0, height=15)
        self.cat_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        self.cat_listbox.bind("<<ListboxSelect>>", self._on_cat_select)
        self.cat_listbox.bind("<Button-3>", self._on_cat_right)
        sb = ttk.Scrollbar(frame, command=self.cat_listbox.yview, style="Modern.Vertical.TScrollbar")
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        self.cat_listbox.configure(yscrollcommand=sb.set)

    def _build_tag_tab(self):
        frame = tk.Frame(self.rnb, bg=C["card"])
        self.rnb.add(frame, text="🏷  标签")

        self.tag_canvas = tk.Canvas(frame, bg=C["card"], highlightthickness=0, borderwidth=0)
        sb = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.tag_canvas.yview, style="Modern.Vertical.TScrollbar")
        self.tag_check_frame = tk.Frame(self.tag_canvas, bg=C["card"])
        self.tag_check_frame.bind("<Configure>", lambda e: self.tag_canvas.configure(
            scrollregion=self.tag_canvas.bbox("all")))
        self.tag_canvas.create_window((0, 0), window=self.tag_check_frame, anchor="nw")
        self.tag_canvas.configure(yscrollcommand=sb.set)
        self.tag_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        self.tag_check_frame.bind("<Button-3>", lambda e: self._show_tag_add())

    def _build_color_tab(self):
        frame = tk.Frame(self.rnb, bg=C["card"])
        self.rnb.add(frame, text="🎨  背景色")

        self.color_listbox = tk.Listbox(frame, font=("Microsoft YaHei UI", 10),
            bg=C["card"], fg=C["text"],
            selectbackground=C["tree_sel"], selectforeground=C["tree_sel_text"],
            relief=tk.FLAT, activestyle="none", borderwidth=0,
            highlightthickness=0, height=15)
        self.color_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(10, 0), pady=10)
        self.color_listbox.bind("<<ListboxSelect>>", self._on_color_select)
        self.color_listbox.bind("<Button-3>", self._on_color_right)
        sb = ttk.Scrollbar(frame, command=self.color_listbox.yview, style="Modern.Vertical.TScrollbar")
        sb.pack(side=tk.RIGHT, fill=tk.Y, pady=10)
        self.color_listbox.configure(yscrollcommand=sb.set)

    # ═══════════════ 导航栏 ═══════════════
    def _build_navigation_bar(self):
        nb = tk.Frame(self.root, bg=C["bar_bottom"], height=34)
        nb.pack(fill=tk.X, side=tk.BOTTOM)
        nb.pack_propagate(False)

        self.nav_buttons_frame = tk.Frame(nb, bg=C["bar_bottom"])
        self.nav_buttons_frame.pack(side=tk.LEFT, padx=8, pady=2)

        right = tk.Frame(nb, bg=C["bar_bottom"])
        right.pack(side=tk.RIGHT, padx=8)

        for text, cmd in [
            ("📖 帮助", self._show_help),
            ("🔄 刷新", self.refresh_all),
        ]:
            HoverButton(right, text=text, font=FONT["status"],
                bg=C["bar_bottom"], fg=C["text_sec"], relief=tk.FLAT,
                cursor="hand2", bd=0, padx=6,
                hover_bg=C["accent_light"], hover_fg=C["accent"],
                command=cmd).pack(side=tk.RIGHT, padx=1)

    # ═══════════════ 菜单 ═══════════════
    def _build_all_menus(self):
        self.menu_single = self._mkmenu("single")
        self.menu_batch = self._mkmenu("batch")
        self.menu_blank = tk.Menu(self.root, tearoff=0,
            bg=C["card"], fg=C["text"],
            activebackground=C["accent_light"], activeforeground=C["accent"],
            font=("Microsoft YaHei UI", 9))
        self.menu_blank.add_command(label="➕ 新建提示词", command=self._add_prompt)
        self.menu_blank.add_separator()
        self.menu_blank.add_command(label="📥 导入提示词", command=self._import_csv)
        self.menu_blank.add_command(label="📖 使用说明", command=self._show_help)
        self.menu_blank.add_command(label="☑ 选择全部",
            command=lambda: self.tree.selection_set(self.tree.get_children()))

    def _mkmenu(self, kind):
        m = tk.Menu(self.root, tearoff=0,
            bg=C["card"], fg=C["text"],
            activebackground=C["accent_light"], activeforeground=C["accent"],
            font=("Microsoft YaHei UI", 9))
        if kind == "single":
            m.add_command(label="➕ 添加问答文本", command=self._add_prompt)
            m.add_separator()
            m.add_command(label="✏️ 编辑提示词", command=self._edit_prompt_from_menu)
            m.add_command(label="📋 复制正文", command=self._copy_content)
            m.add_separator()
            m.add_command(label="📌 置顶 / 取消置顶", command=self._toggle_pin)
            m.add_separator()
        elif kind == "batch":
            m.add_command(label="📋 批量复制正文", command=self._batch_copy)
        self._sub_move = tk.Menu(m, tearoff=0,
            bg=C["card"], fg=C["text"],
            activebackground=C["accent_light"], activeforeground=C["accent"],
            font=("Microsoft YaHei UI", 9))
        m.add_cascade(label="📁 移动到分类", menu=self._sub_move)
        self._sub_tags = tk.Menu(m, tearoff=0,
            bg=C["card"], fg=C["text"],
            activebackground=C["accent_light"], activeforeground=C["accent"],
            font=("Microsoft YaHei UI", 9))
        m.add_cascade(label="🏷 标签", menu=self._sub_tags)
        self._sub_color = tk.Menu(m, tearoff=0,
            bg=C["card"], fg=C["text"],
            activebackground=C["accent_light"], activeforeground=C["accent"],
            font=("Microsoft YaHei UI", 9))
        m.add_cascade(label="🎨 设置背景色", menu=self._sub_color)
        if kind == "single":
            m.add_separator()
            m.add_command(label="🚀 提交给AI", command=self._submit_to_ai)
        m.add_separator()
        m.add_command(label="📤 导出选中", command=lambda: self._export_csv(all=False))
        m.add_command(label="🗑 删除", command=self._delete_selected)
        return m

    def _fill_sub_menus(self, is_batch):
        sel_ids = [int(s) for s in self.tree.selection()] if is_batch else []
        # 移动
        self._sub_move.delete(0, tk.END)
        for c in self.categories:
            self._sub_move.add_command(label=c["name"], command=lambda cid=c["id"]:
                (batch_move_prompts(sel_ids, cid), self._refresh_tree(),
                 self._set_status(f"已移动 {len(sel_ids)} 个提示词", True))
                if is_batch else self._move_to_category(cid))
        self._sub_move.add_separator()
        self._sub_move.add_command(label="❌ 移除分类", command=lambda:
            (batch_move_prompts(sel_ids, None), self._refresh_tree(),
             self._set_status(f"已移除 {len(sel_ids)} 个分类", True))
            if is_batch else (move_prompt_to_category(self.selected_prompt_id, None), self._refresh_tree()))
        # 标签
        self._sub_tags.delete(0, tk.END)
        if is_batch:
            self._sub_tags.add_command(label="➕ 添加标签到选中项...", command=self._batch_add_tags)
            self._sub_tags.add_separator()
            for tag in self.tags:
                self._sub_tags.add_command(label=f"覆盖为: {tag['name']}",
                    command=lambda tid=tag["id"]: self._batch_set_one_tag(tid))
        else:
            pt_ids = [t["id"] for t in get_prompt_tags(self.selected_prompt_id)]
            for tag in self.tags:
                prefix = "✓  " if tag["id"] in pt_ids else "     "
                self._sub_tags.add_command(label=f"{prefix}{tag['name']}",
                    command=lambda tid=tag["id"]: self._toggle_prompt_tag(tid))
        self._sub_tags.add_separator()
        self._sub_tags.add_command(label="➕ 新建标签...", command=self._add_tag)
        # 颜色
        self._sub_color.delete(0, tk.END)
        self._sub_color.add_command(label="❌ 无背景色", command=lambda:
            (batch_set_color(sel_ids, None), self._refresh_tree())
            if is_batch else (update_prompt(self.selected_prompt_id, color_id=None), self._refresh_tree()))
        for c in self.colors:
            self._sub_color.add_command(label=c["name"], command=lambda cid=c["id"]:
                (batch_set_color(sel_ids, cid), self._refresh_tree())
                if is_batch else (update_prompt(self.selected_prompt_id, color_id=cid), self._refresh_tree()))

    def _batch_add_tags(self):
        d = tk.Toplevel(self.root); d.title("批量添加标签"); d.geometry("320x380")
        d.configure(bg=C["card"]); d.transient(self.root); d.grab_set()
        self._center_dialog(d)
        tk.Label(d, text="选择要添加的标签", font=FONT["header"],
                 bg=C["card"], fg=C["text"]).pack(pady=(14, 6))
        vars_ = {}
        for tag in self.tags:
            v = tk.BooleanVar(value=False); vars_[tag["id"]] = v
            cb = tk.Checkbutton(d, text=f"  {tag['name']}", variable=v, bg=C["card"],
                fg=C["text"], font=FONT["ui"], cursor="hand2",
                selectcolor=C["accent_light"],
                activebackground=C["card"], activeforeground=C["accent"])
            cb.pack(anchor=tk.W, padx=30, pady=3)
        def _apply():
            tids = [tid for tid, v in vars_.items() if v.get()]
            if not tids: messagebox.showwarning("提示", "请选择标签"); return
            ids = [int(s) for s in self.tree.selection()]
            batch_set_tags(ids, tids); self._refresh_tree()
            self._set_status(f"已为 {len(ids)} 个提示词添加标签", True); d.destroy()
        HoverButton(d, text="✓  应用", font=FONT["ui_bold"], bg=C["accent"],
            fg=C["text_on_accent"], relief=tk.FLAT, cursor="hand2", bd=0,
            padx=24, pady=6, hover_bg=C["accent_hover"],
            hover_fg=C["text_on_accent"], command=_apply).pack(pady=16)

    def _batch_set_one_tag(self, tag_id):
        ids = [int(s) for s in self.tree.selection()]
        batch_set_tags(ids, [tag_id]); self._refresh_tree()
        self._set_status(f"已设置 {len(ids)} 个提示词标签", True)

    def _batch_copy(self):
        sel = self.tree.selection()
        texts = []
        for s in sel:
            p = get_prompt(int(s))
            if p: texts.append(f"【{p['title']}】\n{p['content']}")
        self._set_clipboard("\n\n───\n\n".join(texts))
        self._set_status(f"已复制 {len(sel)} 个提示词", True)

    # ═══════════════ 数据刷新 ═══════════════
    def refresh_all(self):
        self._refresh_categories(); self._refresh_tags()
        self._refresh_colors(); self._refresh_tree(); self._refresh_navigation()

    def _refresh_categories(self):
        self.categories = get_categories()
        self.cat_listbox.delete(0, tk.END)
        self.cat_listbox.insert(tk.END, "  📋  全部提示词")
        self.cat_listbox.itemconfigure(0, fg=C["accent"], font=("Microsoft YaHei UI", 10, "bold"))
        for i, c in enumerate(self.categories):
            self.cat_listbox.insert(tk.END, f"     {c['name']}")
            self.cat_listbox.itemconfigure(i + 1, fg=C["text_sec"])
        # 分隔线
        self.cat_listbox.insert(tk.END, "")
        self.cat_listbox.insert(tk.END, "  ──────────────")
        self.cat_listbox.itemconfigure(tk.END, fg=C["border"])
        self.cat_listbox.insert(tk.END, "  ＋ 新建分类")
        self.cat_listbox.itemconfigure(tk.END, fg=C["accent"], font=("Microsoft YaHei UI", 9))
        # 恢复选中
        if self.current_category_id is None:
            self.cat_listbox.selection_set(0)
        else:
            for i, c in enumerate(self.categories):
                if c["id"] == self.current_category_id:
                    self.cat_listbox.selection_set(i + 1); break

    def _refresh_tags(self):
        self.tags = get_tags()
        for w in self.tag_check_frame.winfo_children(): w.destroy()
        self.tag_vars = {}

        # 全部 / 无标签
        of = tk.Frame(self.tag_check_frame, bg=C["card"])
        of.pack(fill=tk.X, padx=10, pady=(2, 0))
        tk.Label(of, text="筛选", font=("Microsoft YaHei UI", 8, "bold"),
                 bg=C["card"], fg=C["text_muted"]).pack(anchor=tk.W, padx=2)

        for label, is_all in [("🏷  全部显示", True), ("  无标签", False)]:
            f = tk.Frame(self.tag_check_frame, bg=C["card"])
            f.pack(fill=tk.X, padx=10)
            sel = (self.current_tag_id is None and is_all) or (self.current_tag_id == 0 and not is_all)
            var = tk.BooleanVar(value=sel)
            rb = tk.Radiobutton(f, text=label, variable=var, value=True,
                bg=C["card"], fg=C["text_sec"] if not sel else C["accent"],
                font=("Microsoft YaHei UI", 9),
                selectcolor=C["accent_light"], cursor="hand2",
                activebackground=C["card"], activeforeground=C["accent"],
                command=lambda t=None if is_all else 0: self._set_tag_filter(t))
            rb.pack(anchor=tk.W, padx=6)
            if is_all: self.tag_var_all_rb = rb

        ttk.Separator(self.tag_check_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, padx=12, pady=6)

        for tag in self.tags:
            var = tk.BooleanVar(value=(self.current_tag_id == tag["id"]))
            self.tag_vars[tag["id"]] = var
            f = tk.Frame(self.tag_check_frame, bg=C["card"])
            f.pack(fill=tk.X, padx=10)
            cb = tk.Checkbutton(f, text=tag["name"], variable=var,
                bg=C["card"], fg=C["text"], font=("Microsoft YaHei UI", 9),
                selectcolor=C["accent_light"], cursor="hand2",
                activebackground=C["card"], activeforeground=C["accent"],
                command=lambda tid=tag["id"]: self._set_tag_filter(tid))
            cb.pack(anchor=tk.W, padx=6, pady=1)

        # 底部新建
        tk.Label(self.tag_check_frame, text="", bg=C["card"], font=("", 2)).pack()
        add_btn = HoverButton(self.tag_check_frame, text="＋ 新建标签",
            font=("Microsoft YaHei UI", 9), bg=C["card"], fg=C["accent"],
            relief=tk.FLAT, cursor="hand2", bd=0, padx=8,
            hover_bg=C["accent_light"], hover_fg=C["accent"],
            command=self._show_tag_add)
        add_btn.pack(pady=(2, 10))

    def _set_tag_filter(self, tid):
        self.current_tag_id = tid; self._refresh_tags(); self._refresh_tree()

    def _refresh_colors(self):
        self.colors = get_colors()
        self.color_listbox.delete(0, tk.END)
        self.color_listbox.insert(tk.END, "  🎨  全部颜色")
        self.color_listbox.itemconfigure(0, fg=C["accent"], font=("Microsoft YaHei UI", 10, "bold"))
        for i, c in enumerate(self.colors):
            self.color_listbox.insert(tk.END, f"     {c['name']}")
            idx = i + 1
            try:
                hex_val = c['hex_value'].lstrip('#')
                r, g, b = int(hex_val[0:2], 16), int(hex_val[2:4], 16), int(hex_val[4:6], 16)
                self.color_listbox.itemconfigure(idx, bg=c['hex_value'],
                    fg="#333" if r + g + b > 400 else "#FFF",
                    font=("Microsoft YaHei UI", 9))
            except: pass
        # 新建
        self.color_listbox.insert(tk.END, "")
        self.color_listbox.insert(tk.END, "  ──────────────")
        self.color_listbox.itemconfigure(tk.END, fg=C["border"])
        self.color_listbox.insert(tk.END, "  ＋ 新建颜色")
        self.color_listbox.itemconfigure(tk.END, fg=C["accent"], font=("Microsoft YaHei UI", 9))

        if self.current_color_id is None:
            self.color_listbox.selection_set(0)
        else:
            for i, c in enumerate(self.colors):
                if c["id"] == self.current_color_id:
                    self.color_listbox.selection_set(i + 1); break

    def _refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        search_raw = self.search_var.get().strip()
        search = None if (self._search_placeholder or not search_raw) else search_raw
        prompts = get_prompts(
            category_id=self.current_category_id,
            tag_id=self.current_tag_id,
            color_id=self.current_color_id,
            search=search)

        for idx, p in enumerate(prompts):
            cat_name = next((c["name"] for c in self.categories if c["id"] == p["category_id"]), "")
            tag_names = ", ".join(t["name"] for t in get_prompt_tags(p["id"]))
            color_hex = next((c["hex_value"] for c in self.colors if c["id"] == p["color_id"]), "")
            color_name = next((c["name"] for c in self.colors if c["id"] == p["color_id"]), "")
            iid = str(p["id"])

            tags = ()
            if color_hex:
                self.tree.tag_configure(f"cr_{p['id']}", background=color_hex)
                tags = (f"cr_{p['id']}",)

            self.tree.insert("", tk.END, iid=iid, values=(
                p["id"], "📌" if p["is_pinned"] else "",
                p["title"], p["content"], cat_name, tag_names, color_name
            ), tags=tags)

        self.status_count.configure(
            text=f"共 {len(prompts)} 条提示词" + (f"（搜索: {search}）" if search else ""))

    def _refresh_navigation(self):
        for w in self.nav_buttons_frame.winfo_children(): w.destroy()
        navs = get_navigation()
        for nav in navs:
            HoverButton(self.nav_buttons_frame, text=nav["name"], font=FONT["nav"],
                bg=C["bar_bottom"], fg=C["text_sec"], relief=tk.FLAT,
                cursor="hand2", bd=0, padx=8,
                hover_bg=C["accent_light"], hover_fg=C["accent"],
                command=lambda u=nav["url"]: webbrowser.open(u)).pack(side=tk.LEFT, padx=1)
        HoverButton(self.nav_buttons_frame, text="⚙ 导航设置", font=FONT["nav"],
            bg=C["bar_bottom"], fg=C["text_muted"], relief=tk.FLAT,
            cursor="hand2", bd=0, padx=8,
            hover_bg=C["accent_light"], hover_fg=C["accent"],
            command=self._nav_settings).pack(side=tk.LEFT, padx=(8, 1))

    # ═══════════════ 事件 ═══════════════
    def _on_tree_click(self, event):
        if self.tree.identify_region(event.x, event.y) != "cell": return
        item = self.tree.identify_row(event.y)
        if not item: return
        self.selected_prompt_id = int(item)
        if self.click_to_copy.get():
            p = get_prompt(self.selected_prompt_id)
            if p: self._set_clipboard(p["content"]); self._set_status(f"已复制: {p['title'][:30]}", True, 2000)
        self._load_editor(self.selected_prompt_id)

    def _on_tree_double(self, event):
        item = self.tree.identify_row(event.y)
        if not item: self._add_prompt(); return
        self.selected_prompt_id = int(item)
        if not self.click_to_copy.get():
            p = get_prompt(self.selected_prompt_id)
            if p: self._set_clipboard(p["content"]); self._set_status(f"已复制: {p['title'][:30]}", True, 2000)

    def _on_tree_right(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            if item not in self.tree.selection(): self.tree.selection_set(item)
            sel = self.tree.selection()
            if len(sel) == 1:
                self.selected_prompt_id = int(sel[0])
                self._fill_sub_menus(False); self.menu_single.post(event.x_root, event.y_root)
            else:
                self._fill_sub_menus(True); self.menu_batch.post(event.x_root, event.y_root)
        else:
            self.menu_blank.post(event.x_root, event.y_root)

    def _on_cat_select(self, event):
        sel = self.cat_listbox.curselection()
        if not sel: return
        idx = sel[0]
        total_items = len(self.categories) + 3  # + all, divider, add
        if idx >= total_items - 3:
            # 点击"新建分类"
            if idx == total_items - 1:
                self._add_category()
            # 点击分隔线 - 忽略
            return
        self.current_category_id = None if idx == 0 else self.categories[idx - 1]["id"]
        self._refresh_tree()
        self._set_status(f"分类: {'全部' if idx == 0 else self.categories[idx - 1]['name']}")

    def _on_cat_right(self, event):
        m = tk.Menu(self.root, tearoff=0, bg=C["card"], fg=C["text"],
            activebackground=C["accent_light"], activeforeground=C["accent"],
            font=("Microsoft YaHei UI", 9))
        m.add_command(label="➕ 新增分类", command=self._add_category)
        sel = self.cat_listbox.curselection()
        if sel and sel[0] > 0 and sel[0] <= len(self.categories):
            m.add_command(label="✏️ 重命名分类", command=self._rename_category)
            m.add_command(label="🗑 删除分类", command=self._delete_category)
        m.post(event.x_root, event.y_root)

    def _on_color_select(self, event):
        sel = self.color_listbox.curselection()
        if not sel: return
        idx = sel[0]
        real_colors = len(self.colors)
        if idx >= real_colors + 3:
            if idx == real_colors + 3: self._add_color()
            return
        self.current_color_id = None if idx == 0 else self.colors[idx - 1]["id"]
        self._refresh_tree()

    def _on_color_right(self, event):
        m = tk.Menu(self.root, tearoff=0, bg=C["card"], fg=C["text"],
            activebackground=C["accent_light"], activeforeground=C["accent"],
            font=("Microsoft YaHei UI", 9))
        m.add_command(label="➕ 新增颜色", command=self._add_color)
        sel = self.color_listbox.curselection()
        if sel and sel[0] > 0 and sel[0] <= len(self.colors):
            m.add_command(label="✏️ 重命名颜色", command=self._rename_color)
            m.add_command(label="🗑 删除颜色", command=self._delete_color)
        m.post(event.x_root, event.y_root)

    def _show_tag_add(self):
        name = simpledialog.askstring("新建标签", "请输入标签名称:")
        if name and name.strip(): add_tag(name.strip()); self._refresh_tags()
        self._set_status(f"已创建标签: {name.strip()}", True) if name and name.strip() else None

    # ═══════════════ 拖动 ═══════════════
    def _on_drag_start(self, event):
        if self.tree.identify_region(event.x, event.y) == "heading": return
        item = self.tree.identify_row(event.y)
        if item:
            self._drag_data["item"] = item; self._drag_data["start"] = True
            self._drag_data["x"] = event.x; self._drag_data["y"] = event.y

    def _on_drag_motion(self, event):
        if not self._drag_data.get("start"): return
        if abs(event.x - self._drag_data.get("x", 0)) < 5 and abs(event.y - self._drag_data.get("y", 0)) < 5: return
        self._drag_data["start"] = False
        item = self._drag_data.get("item")
        target = self.tree.identify_row(event.y)
        if target and target != item:
            self.tree.move(item, self.tree.parent(target), self.tree.index(target))
            self._sync_sort_order()

    def _on_drag_release(self, event):
        self._drag_data = {"item": None, "start": False}

    def _sync_sort_order(self):
        batch_update_sort_orders({int(item): i for i, item in enumerate(self.tree.get_children())})

    # ═══════════════ 编辑 ═══════════════
    def _load_editor(self, pid):
        p = get_prompt(pid)
        if p:
            self.editing_prompt_id = pid
            self.title_var.set(p["title"])
            self.content_text.delete("1.0", tk.END); self.content_text.insert("1.0", p["content"])

    def _auto_save(self):
        if self.editing_prompt_id:
            update_prompt(self.editing_prompt_id, title=self.title_var.get(),
                          content=self.content_text.get("1.0", "end-1c"))
            self._refresh_tree()

    def _save_edit(self):
        if self.editing_prompt_id is not None:
            update_prompt(self.editing_prompt_id, title=self.title_var.get(),
                          content=self.content_text.get("1.0", "end-1c"))
            self._refresh_tree(); self._set_status("已保存 ✓", True, 2000)
        elif self.title_var.get().strip():
            pid = add_prompt(self.title_var.get().strip(), self.content_text.get("1.0", "end-1c"),
                             category_id=self.current_category_id)
            self.editing_prompt_id = pid; self._refresh_tree()
            self._set_status("已创建新提示词 ✓", True, 2000)
        else:
            messagebox.showwarning("提示", "请输入标题")

    def _set_clipboard(self, text):
        self.root.clipboard_clear(); self.root.clipboard_append(text); self.root.update()

    def _center_dialog(self, d):
        d.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - d.winfo_width()) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - d.winfo_height()) // 2
        d.geometry(f"+{x}+{y}")

    # ═══════════════ CRUD ═══════════════
    def _add_prompt(self):
        self.editing_prompt_id = None; self.title_var.set("")
        self.content_text.delete("1.0", tk.END)
        self.title_entry.focus_set(); self._set_status("输入标题后点击保存")

    def _edit_prompt_from_menu(self):
        sel = self.tree.selection()
        if sel: self._load_editor(int(sel[0])); self.title_entry.focus_set()

    def _copy_content(self):
        sel = self.tree.selection()
        if sel:
            p = get_prompt(int(sel[0]))
            if p: self._set_clipboard(p["content"]); self._set_status(f"已复制: {p['title'][:30]}", True, 2000)

    def _toggle_pin(self):
        sel = self.tree.selection()
        if sel: toggle_pin_prompt(int(sel[0])); self._refresh_tree()

    def _move_to_category(self, cid):
        sel = self.tree.selection()
        if sel: move_prompt_to_category(int(sel[0]), cid); self._refresh_tree()

    def _toggle_prompt_tag(self, tid):
        sel = self.tree.selection()
        if not sel: return
        pid = int(sel[0])
        existing = [t["id"] for t in get_prompt_tags(pid)]
        if tid in existing: existing.remove(tid)
        else: existing.append(tid)
        set_prompt_tags(pid, existing); self._refresh_tree()

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel: return
        if messagebox.askyesno("确认删除", f"确定删除 {len(sel)} 个提示词吗？\n此操作不可恢复！"):
            batch_delete_prompts([int(s) for s in sel])
            self.editing_prompt_id = None; self.title_var.set("")
            self.content_text.delete("1.0", tk.END)
            self._refresh_tree(); self._set_status(f"已删除 {len(sel)} 个提示词", True)

    def _export_csv(self, all=False):
        sel = self.tree.get_children() if all else self.tree.selection()
        if not sel: messagebox.showwarning("提示", "请先选择提示词"); return
        fp = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if fp:
            export_prompts_csv([int(s) for s in sel], fp)
            self._set_status(f"已导出: {os.path.basename(fp)}", True)

    def _import_csv(self):
        fp = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if fp:
            imported = import_prompts_csv(fp); self.refresh_all()
            self._set_status(f"已导入 {imported} 条提示词", True)

    # ═══════════════ AI ═══════════════
    def _get_api_config(self):
        provider = self.api_provider.get()
        key = get_setting(f"{provider}_api_key", "") or get_setting("api_key", "")
        if not key: return None, None, None, None
        if provider == "openai":
            return key, "https://api.openai.com/v1/chat/completions", get_setting("openai_model", "gpt-3.5-turbo"), "openai"
        elif provider == "deepseek":
            return key, "https://api.deepseek.com/v1/chat/completions", "deepseek-chat", "openai"
        elif provider == "claude":
            return key, "https://api.anthropic.com/v1/messages", "claude-3-sonnet-20240229", "claude"
        else:
            return (get_setting("custom_api_key", "") or key,
                    get_setting("custom_api_url", "https://api.openai.com/v1/chat/completions"),
                    get_setting("custom_model", "gpt-3.5-turbo"), "openai")

    def _call_ai(self, prompt_content, on_result):
        key, url, model, fmt = self._get_api_config()
        if not key: self.root.after(0, self._ask_config); return
        self._set_status("正在调用 AI…")
        def _run():
            try:
                if fmt == "claude":
                    data = json.dumps({"model": model, "max_tokens": 1024,
                        "messages": [{"role": "user", "content": prompt_content}]}).encode()
                    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}
                else:
                    data = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt_content}]}).encode()
                    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
                req = urllib.request.Request(url, data=data, headers=headers)
                with urllib.request.urlopen(req, timeout=60) as resp:
                    result = json.loads(resp.read().decode())
                reply = (result.get("content", [{}])[0].get("text", "无响应") if fmt == "claude"
                         else result.get("choices", [{}])[0].get("message", {}).get("content", "无响应"))
                self.root.after(0, lambda: on_result(reply))
                self.root.after(0, lambda: self._set_status("AI 回复已加载", True, 3000))
            except urllib.error.HTTPError as e:
                self.root.after(0, lambda: messagebox.showerror("API 错误", f"HTTP {e.code}"))
                self.root.after(0, lambda: self._set_status("API 调用失败"))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("网络错误", str(e)))
                self.root.after(0, lambda: self._set_status("网络错误"))
        threading.Thread(target=_run, daemon=True).start()

    def _ask_config(self):
        if messagebox.askyesno("API 密钥未配置", "请先在设置中配置 API 密钥。\n现在前往配置？"):
            self._config_api()

    def _submit_to_ai(self):
        sel = self.tree.selection()
        if not sel: messagebox.showwarning("提示", "请选择一个提示词"); return
        p = get_prompt(int(sel[0]))
        if p: self._call_ai(p["content"], self._show_ai_result)

    def _show_ai_result(self, reply):
        self.content_text.delete("1.0", tk.END); self.content_text.insert("1.0", reply)

    def _polish(self):
        content = self.content_text.get("1.0", "end-1c")
        if not content.strip(): messagebox.showinfo("提示", "请输入内容"); return
        self._call_ai(f"请润色以下提示词，使其更清晰、专业，保留原意。只输出润色后的内容：\n\n{content}", self._show_ai_result)

    # ═══════════════ 分类 / 标签 / 颜色 CRUD ═══════════════
    def _add_category(self):
        name = simpledialog.askstring("新建分类", "请输入分类名称:")
        if name and name.strip(): add_category(name.strip()); self._refresh_categories(); self._refresh_tree()

    def _rename_category(self):
        sel = self.cat_listbox.curselection()
        if sel and sel[0] > 0 and sel[0] <= len(self.categories):
            c = self.categories[sel[0] - 1]
            nn = simpledialog.askstring("重命名", "新名称:", initialvalue=c["name"])
            if nn and nn.strip(): rename_category(c["id"], nn.strip()); self._refresh_categories()

    def _delete_category(self):
        sel = self.cat_listbox.curselection()
        if sel and sel[0] > 0 and sel[0] <= len(self.categories):
            c = self.categories[sel[0] - 1]
            if messagebox.askyesno("确认", f"删除分类「{c['name']}」？\n该分类下的提示词将变为未分类。"):
                delete_category(c["id"])
                if self.current_category_id == c["id"]: self.current_category_id = None
                self._refresh_categories(); self._refresh_tree()

    def _add_tag(self):
        name = simpledialog.askstring("新建标签", "请输入标签名称:")
        if name and name.strip(): add_tag(name.strip()); self._refresh_tags()

    def _add_color(self):
        name = simpledialog.askstring("新建颜色", "请输入颜色名称:")
        if not name or not name.strip(): return
        result = colorchooser.askcolor(title="选择颜色", color="#FFCDD2")
        if result and result[1]: add_color(name.strip(), result[1]); self._refresh_colors()

    def _rename_color(self):
        sel = self.color_listbox.curselection()
        if sel and sel[0] > 0 and sel[0] <= len(self.colors):
            c = self.colors[sel[0] - 1]
            nn = simpledialog.askstring("重命名", "新名称:", initialvalue=c["name"])
            if nn and nn.strip(): rename_color(c["id"], nn.strip()); self._refresh_colors()

    def _delete_color(self):
        sel = self.color_listbox.curselection()
        if sel and sel[0] > 0 and sel[0] <= len(self.colors):
            c = self.colors[sel[0] - 1]
            if messagebox.askyesno("确认", f"删除颜色「{c['name']}」？"):
                delete_color(c["id"])
                if self.current_color_id == c["id"]: self.current_color_id = None
                self._refresh_colors(); self._refresh_tree()

    # ═══════════════ 对话框（API 配置 + 导航设置 + 帮助） ═══════════════
    def _config_api(self):
        d = tk.Toplevel(self.root); d.title("API 配置"); d.geometry("520x460")
        d.configure(bg=C["card"]); d.transient(self.root); d.grab_set()

        h = tk.Frame(d, bg=C["accent"], height=3); h.pack(fill=tk.X)
        tk.Label(d, text="⚙  API 配置", font=FONT["title"], bg=C["card"], fg=C["text"]).pack(pady=(14, 6))

        notebook = ttk.Notebook(d, style="Modern.TNotebook")
        notebook.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))
        vars_ = {}

        providers = [
            ("OpenAI", [("openai_api_key", "API Key", True), ("openai_model", "Model", False)]),
            ("DeepSeek", [("deepseek_api_key", "API Key", True)]),
            ("Claude", [("claude_api_key", "API Key", True)]),
            ("自定义", [("custom_api_url", "URL", False), ("custom_api_key", "API Key", True), ("custom_model", "Model", False)]),
        ]
        for name, fields in providers:
            tab = tk.Frame(notebook, bg=C["card"])
            notebook.add(tab, text=f"  {name}  ")
            for i, (key, label, is_secret) in enumerate(fields):
                rf = tk.Frame(tab, bg=C["card"])
                rf.pack(fill=tk.X, padx=12, pady=4)
                tk.Label(rf, text=label, font=FONT["ui_bold"], bg=C["card"],
                         fg=C["text"], width=10, anchor=tk.W).pack(side=tk.LEFT)
                v = tk.StringVar(value=get_setting(key, ""))
                vars_[key] = v
                e = tk.Entry(rf, textvariable=v, font=FONT["ui"], width=36,
                    relief=tk.FLAT, bg=C["card_alt"], fg=C["text"],
                    insertbackground=C["accent"], show="●" if is_secret else "")
                e.pack(side=tk.LEFT, ipady=4, padx=6)

        HoverButton(d, text="💾  保存配置", font=FONT["ui_bold"],
            bg=C["accent"], fg=C["text_on_accent"], relief=tk.FLAT,
            cursor="hand2", bd=0, padx=24, pady=7,
            hover_bg=C["accent_hover"], hover_fg=C["text_on_accent"],
            command=lambda: [set_setting(k, v.get()) for k, v in vars_.items()] +
            [d.destroy(), self._set_status("API 配置已保存 ✓", True)]
        ).pack(pady=(0, 14))
        self._center_dialog(d)

    def _nav_settings(self):
        d = tk.Toplevel(self.root); d.title("导航设置"); d.geometry("500x380")
        d.configure(bg=C["card"]); d.transient(self.root); d.grab_set()
        h = tk.Frame(d, bg=C["accent"], height=3); h.pack(fill=tk.X)
        tk.Label(d, text="🔗  导航链接管理", font=FONT["header"],
                 bg=C["card"], fg=C["text"]).pack(pady=(12, 6))
        lb = tk.Listbox(d, font=FONT["ui"], bg=C["card_alt"], fg=C["text"],
            relief=tk.FLAT, selectbackground=C["tree_sel"],
            selectforeground=C["tree_sel_text"], borderwidth=0)
        lb.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)
        navs = get_navigation()
        for n in navs: lb.insert(tk.END, f"  {n['name']}  →  {n['url']}")

        bf = tk.Frame(d, bg=C["card"]); bf.pack(fill=tk.X, padx=16, pady=(8, 12))
        for t, c in [("➕ 添加", lambda: self._nav_add(d)),
                      ("✏️ 编辑", lambda: self._nav_edit(lb, navs, d)),
                      ("🗑 删除", lambda: self._nav_del(lb, navs, d))]:
            HoverButton(bf, text=t, font=FONT["ui"], bg=C["card_alt"], fg=C["text"],
                relief=tk.FLAT, cursor="hand2", bd=0, padx=12, pady=4,
                hover_bg=C["accent_light"], hover_fg=C["accent"],
                command=c).pack(side=tk.LEFT, padx=3)
        self._center_dialog(d)

    def _nav_add(self, d):
        name = simpledialog.askstring("添加导航", "名称:", parent=d)
        if name and name.strip():
            url = simpledialog.askstring("添加导航", "URL:", parent=d)
            if url and url.strip(): add_navigation(name.strip(), url.strip()); self._refresh_navigation(); d.destroy()

    def _nav_edit(self, lb, navs, d):
        sel = lb.curselection()
        if sel:
            n = navs[sel[0]]
            name = simpledialog.askstring("编辑", "名称:", initialvalue=n["name"], parent=d)
            if name and name.strip():
                url = simpledialog.askstring("编辑", "URL:", initialvalue=n["url"], parent=d)
                if url and url.strip(): update_navigation(n["id"], name.strip(), url.strip()); self._refresh_navigation(); d.destroy()

    def _nav_del(self, lb, navs, d):
        sel = lb.curselection()
        if sel:
            n = navs[sel[0]]
            if messagebox.askyesno("确认", f"删除链接「{n['name']}」？"):
                delete_navigation(n["id"]); self._refresh_navigation(); d.destroy()

    def _show_help(self):
        d = tk.Toplevel(self.root); d.title("使用说明"); d.geometry("580x520")
        d.configure(bg=C["card"]); d.transient(self.root)
        h = tk.Frame(d, bg=C["accent"], height=3); h.pack(fill=tk.X)
        tk.Label(d, text="📚  使用说明", font=FONT["title"], bg=C["card"], fg=C["text"]).pack(pady=(12, 6))
        txt = tk.Text(d, font=FONT["ui"], bg=C["card"], fg=C["text"], relief=tk.FLAT,
            wrap=tk.WORD, borderwidth=0, padx=14, pady=10,
            selectbackground=C["tree_sel"], selectforeground=C["tree_sel_text"])
        txt.pack(fill=tk.BOTH, expand=True, padx=12)
        help_text = """📚 提示词管理工具 · 使用说明

━━━━━━━━━━━━━━━━━━━━━━━━━━
  🎯 核心功能
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 提示词管理   — 新建 / 编辑 / 删除 / 拖动排序
• 分类管理     — 右侧面板，右键操作
• 标签系统     — 勾选筛选，支持批量添加
• 背景色       — 为提示词设置颜色标识
• 快速复制     — 单击 / 双击 / 批量复制
• 实时搜索     — 匹配标题和正文
• AI 集成      — 提交给AI / 润色优化

━━━━━━━━━━━━━━━━━━━━━━━━━━
  💡 操作技巧
━━━━━━━━━━━━━━━━━━━━━━━━━━
• Ctrl + 点击 → 批量选择（右键批量操作）
• 长按拖动     → 调整提示词顺序
• 勾选「单击复制」 → 单击表格行直接复制
• 未开启时双击     → 复制正文
• 双击空白区域     → 新建提示词

━━━━━━━━━━━━━━━━━━━━━━━━━━
  📦 数据管理
━━━━━━━━━━━━━━━━━━━━━━━━━━
• 存储位置：storage/prompts.db
• 导出备份：右键 → 导出选中 / 导出全部
• 从 CSV 导入：右键 → 导入提示词
• 备份方法：直接复制 prompts.db 文件"""
        txt.insert("1.0", help_text)
        txt.configure(state="disabled")
        HoverButton(d, text="关闭", font=FONT["ui_bold"], bg=C["accent"], fg=C["text_on_accent"],
            relief=tk.FLAT, cursor="hand2", bd=0, padx=20, pady=6,
            hover_bg=C["accent_hover"], hover_fg=C["text_on_accent"],
            command=d.destroy).pack(pady=(6, 12))
        self._center_dialog(d)

    # ═══════════════ 窗口 ═══════════════
    def _toggle_topmost(self, *a):
        self.root.attributes("-topmost", self.window_topmost.get())

    def _on_close(self):
        set_setting("click_to_copy", "1" if self.click_to_copy.get() else "0")
        set_setting("window_topmost", "1" if self.window_topmost.get() else "0")
        self.root.destroy()


def main():
    init_db()
    root = tk.Tk()
    # Windows DPI 感知
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    PromptManager(root)
    root.mainloop()


if __name__ == "__main__":
    main()
