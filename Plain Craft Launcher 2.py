import tkinter as tk
from tkinter import ttk, messagebox
import random
import time
import os
import sys


class PCL_PlayerLauncher:
    WIN_W, WIN_H = 900, 550
    TOP_H = 50
    BTN_W, BTN_H = 280, 55

    BTN_FONT = ("Microsoft YaHei", 14, "bold")
    BTN_BG = "#FFFFFF"
    BTN_FG = "#FF6B81"
    BTN_ABG = "#FFE4E8"
    BTN_AFG = "#FF6B81"
    BTN_BD = 2
    BTN_TEXT = "启动游戏"

    FLOAT_LIFETIME_MS = 2500
    NEAR_DIST = 200

    DESKTOP_BTN_TEXT = "PCL"
    DESKTOP_BTN_SIZE = 60
    DESKTOP_BTN_MARGIN = 20

    # ⚠️ 注销延迟秒数（用 tkinter after 实现）
    LOGOFF_DELAY_SECONDS = 5

    NAV_FAKE_ERRORS = [
        ("启动器文件损坏",
         "错误代码：PCL_CORRUPTED_0x0001\n\n"
         "无法读取核心配置文件。\n"
         "启动器将无法继续运行。\n\n"
         "请尝试重新下载 PCL2。"),
        ("启动器文件损坏",
         "错误代码：PCL_CORRUPTED_0x0007\n\n"
         "配置文件 Setup.ini 缺失或已损坏。\n"
         "请检查 PCL2 目录下是否存在该文件。\n\n"
         "若问题依旧，请重新下载 PCL2。"),
        ("启动器文件损坏",
         "错误代码：PCL_CORRUPTED_0x000A\n\n"
         "无法连接到 PCL 服务器。\n"
         "正在回退到本地缓存……\n"
         "本地缓存也已损坏。\n\n"
         "请尝试重新下载 PCL2。"),
        ("启动器文件损坏",
         "错误代码：PCL_CORRUPTED_0x0013\n\n"
         "内置资源释放失败。\n"
         "当前启动器可能被其他程序占用。\n\n"
         "请尝试重新下载 PCL2。"),
        ("启动器文件损坏",
         "错误代码：PCL_CORRUPTED_0x0019\n\n"
         "检测到启动器核心文件被修改。\n"
         "为防止意外行为，已自动停用。\n\n"
         "请尝试重新下载 PCL2。"),
    ]

    LAUNCH_STAGES = [
        ("预检测",           "ModLaunch 预检测已通过"),
        ("补全文件",         "加载器 LoaderCombo`1 补全文件"),
        ("获取 Java",        "已选定 Java：Java 25 (25.0.1.0)"),
        ("验证登录",         "验证登录开始（Validate, Auth）"),
        ("分析资源文件索引", "版本对应资源文件索引为 34"),
        ("下载支持库文件",   "LoaderDownload 下载支持库文件"),
        ("获取启动参数",     "参数获取开始"),
        ("启动进程",         "已启动游戏进程"),
        ("等待游戏窗口出现", "ModWatcher 监听中..."),
    ]

    STAGE_DETAILS = {
        "预检测":           ["预检测已通过", "后台检查资源文件索引"],
        "补全文件":         ["分析缺失支持库文件", "下载支持库文件（主加载器）",
                            "分析游戏支持库文件（副加载器）"],
        "获取 Java":        ["Mojang 要求至少使用 Java 25",
                            "自动选择 Java 范围：[25.0, +∞)",
                            "检查 Java 成功：Java 25 (25.0.1.0)"],
        "验证登录":         ["登录方式：Authlib-Injector",
                            "Login Auth 状态改变：Loading",
                            "向 littleskin.cn 请求 Validate"],
        "分析资源文件索引":  ["版本 26.3 对应索引为 34", "无需更新资源文件索引"],
        "下载支持库文件":    ["NetState: Downloading", "NetState: Merging",
                            "SHA1 校验通过"],
        "获取启动参数":      ["从版本 JSON 获取 JVM 参数",
                            "Authlib Injector Prefetch", "GC 设置：G1GC"],
        "启动进程":          ["构建 JVM 参数...", "启动 Java 进程...",
                            "已启动游戏进程：java.exe"],
        "等待游戏窗口出现":  ["开始 Minecraft 日志监控", "日志 1/5：已出现日志输出",
                            "日志 2/5：游戏用户已设置", "日志 3/5：LWJGL 版本已确认",
                            "日志 4/5：OpenAL 已加载", "日志 5/5：材质已加载"],
    }

    FAKE_CRASH_REASONS = [
        "检测到 Mod 冲突：optifine 与 sodium 不兼容",
        "缺失前置：fabric-api 未安装",
        "Java 版本不匹配：需要 Java 25，当前为 Java 8",
        "内存不足：分配内存低于 2GB",
        "配置文件损坏：options.txt 格式错误",
        "GLFW 初始化失败：显卡不支持所需扩展",
    ]

    def __init__(self, root):
        self.root = root
        self.root.title("PCL - 玩家特别版")
        self.root.geometry(f"{self.WIN_W}x{self.WIN_H}")
        self.root.resizable(False, False)
        self.root.configure(bg="#FFFFFF")
        self.root.overrideredirect(True)

        self.starting = False
        self.dodge_enabled = True
        self.is_flying_back = False
        self.dialog_open = False
        self.drag_x = 0
        self.drag_y = 0

        self.btn_x = 0.0
        self.btn_y = 0.0
        self.dodge_cooldown = 0.0

        self.float_win = None
        self.float_x = 0.0
        self.float_y = 0.0
        self.float_timer = None

        self.launch_count = 0
        self.shutdown_overlay = None
        self.desktop_btn = None
        self.logoff_timer = None    # ⭐ 注销倒计时 handle

        self.progress_var = tk.DoubleVar(value=0.0)
        self.progress_text_var = tk.StringVar(value="0.00 %")
        self.step_var = tk.StringVar(value="准备就绪")
        self.auth_var = tk.StringVar(value="Authlib-Injector")

        self.build_ui()
        self.root.bind("<Return>", self.start_game)
        self.root.bind("<Escape>", lambda e: self.cleanup_and_quit())

        self.root.after(120, self.place_flag)
        self.root.after(50, self.chase_tick)

    def cleanup_and_quit(self):
        if self.float_timer is not None:
            try:
                self.root.after_cancel(self.float_timer)
            except Exception:
                pass
        if self.logoff_timer is not None:
            try:
                self.root.after_cancel(self.logoff_timer)
            except Exception:
                pass
        if self.float_win is not None and self.float_win.winfo_exists():
            self.float_win.destroy()
        if self.shutdown_overlay is not None and self.shutdown_overlay.winfo_exists():
            self.shutdown_overlay.destroy()
        try:
            self.root.destroy()
        except tk.TclError:
            pass

    # ==================== UI ====================
    def build_ui(self):
        self.top_bar = tk.Frame(self.root, bg="#FF8C9A", height=self.TOP_H)
        self.top_bar.pack(fill="x", side="top")
        self.top_bar.pack_propagate(False)
        self.top_bar.bind("<Button-1>", self.start_move)
        self.top_bar.bind("<B1-Motion>", self.do_move)

        tk.Label(self.top_bar, text="PCL",
                 font=("Microsoft YaHei", 16, "bold"),
                 fg="white", bg="#FF8C9A").pack(side="left", padx=(20, 15))

        for item in ["启动", "下载", "联机", "设置", "更多"]:
            btn = tk.Label(self.top_bar, text=item,
                           font=("Microsoft YaHei", 10),
                           fg="white", bg="#FF8C9A", padx=10, cursor="hand2")
            btn.pack(side="left", padx=3)
            btn.bind("<Button-1>",
                     lambda e, name=item: self.on_nav_clicked(name))

        close_btn = tk.Label(self.top_bar, text="✕",
                             font=("Microsoft YaHei", 12, "bold"),
                             fg="white", bg="#FF8C9A", padx=12, cursor="hand2")
        close_btn.pack(side="right")
        close_btn.bind("<Button-1>", lambda e: self.cleanup_and_quit())

        min_btn = tk.Label(self.top_bar, text="—",
                           font=("Microsoft YaHei", 12, "bold"),
                           fg="white", bg="#FF8C9A", padx=12, cursor="hand2")
        min_btn.pack(side="right")
        min_btn.bind("<Button-1>", lambda e: self.root.iconify())

        self.main_frame = tk.Frame(self.root, bg="#FFFFFF")
        self.main_frame.pack(fill="both", expand=True)

        self.left_panel = tk.Frame(self.main_frame, bg="#FFFFFF")
        self.left_panel.pack(fill="both", expand=True)

        self.init_view = tk.Frame(self.left_panel, bg="#FFFFFF")
        self.launch_view = tk.Frame(self.left_panel, bg="#FFFFFF")

        self.setup_init_view()
        self.setup_launch_view()
        self.init_view.pack(fill="both", expand=True)

    def on_nav_clicked(self, name):
        if self.starting or self.dialog_open:
            return
        if name == "启动":
            self.on_main_clicked()
            return

        self.dialog_open = True
        self.reset_main_button()

        title, content = random.choice(self.NAV_FAKE_ERRORS)
        try:
            messagebox.showerror(
                title,
                f"「{name}」模块加载失败。\n\n{content}"
            )
        finally:
            self.dialog_open = False
            self.dodge_cooldown = time.time() + 0.3
            self.reset_main_button()

    def reset_main_button(self):
        self.btn_x = float((self.WIN_W - self.BTN_W) // 2)
        self.btn_y = float((self.WIN_H - self.TOP_H) - self.BTN_H - 140)
        try:
            self.start_btn.place(x=int(self.btn_x), y=int(self.btn_y),
                                 width=self.BTN_W, height=self.BTN_H)
        except tk.TclError:
            pass

    def setup_init_view(self):
        self.flag_size = 48
        self.flag_canvas = tk.Canvas(
            self.init_view, width=self.flag_size, height=self.flag_size,
            bg="#FFFFFF", highlightthickness=0, bd=0, cursor="hand2")

        self.flag_circle = self.flag_canvas.create_oval(
            4, 4, self.flag_size - 4, self.flag_size - 4,
            outline="#FF6B81", width=2, fill="#FFF0F2")

        self.flag_text = self.flag_canvas.create_text(
            self.flag_size / 2, self.flag_size / 2,
            text="🏳", font=("Segoe UI Emoji", 14),
            fill="#FF6B81")

        self.flag_canvas.bind("<Button-1>", lambda e: self.surrender())
        self.flag_canvas.bind("<Enter>", self._flag_hover_in)
        self.flag_canvas.bind("<Leave>", self._flag_hover_out)

        bottom = tk.Frame(self.init_view, bg="#FFFFFF")
        bottom.pack(side="bottom", fill="x", pady=(0, 30))

        tk.Label(bottom, text="红石生电优化26.3",
                 font=("Microsoft YaHei", 10), fg="#888888",
                 bg="#FFFFFF").pack()

        btn_row = tk.Frame(bottom, bg="#FFFFFF")
        btn_row.pack(pady=(10, 0))
        tk.Button(btn_row, text="版本选择",
                  font=("Microsoft YaHei", 10),
                  bg="#FFFFFF", fg="#333333", relief="solid", bd=1,
                  cursor="hand2", width=14,
                  command=lambda: self.on_nav_clicked("版本选择")
                  ).pack(side="left", padx=(0, 5))
        tk.Button(btn_row, text="版本设置",
                  font=("Microsoft YaHei", 10),
                  bg="#FFFFFF", fg="#333333", relief="solid", bd=1,
                  cursor="hand2", width=14,
                  command=lambda: self.on_nav_clicked("版本设置")
                  ).pack(side="right", padx=(5, 0))

        self.start_btn = tk.Button(
            self.init_view, text=self.BTN_TEXT,
            font=self.BTN_FONT,
            bg=self.BTN_BG, fg=self.BTN_FG,
            activebackground=self.BTN_ABG, activeforeground=self.BTN_AFG,
            relief="solid", bd=self.BTN_BD, cursor="hand2",
            command=self.on_main_clicked)

        self.btn_x = float((self.WIN_W - self.BTN_W) // 2)
        self.btn_y = float((self.WIN_H - self.TOP_H) - self.BTN_H - 140)
        self.start_btn.place(x=int(self.btn_x), y=int(self.btn_y),
                             width=self.BTN_W, height=self.BTN_H)

    def place_flag(self):
        try:
            self.flag_canvas.place(
                x=self.WIN_W - self.flag_size - 15,
                y=(self.WIN_H - self.TOP_H) - self.flag_size - 15)
        except tk.TclError:
            pass

    def _flag_hover_in(self, event=None):
        self.flag_canvas.itemconfig(self.flag_circle,
                                    fill="#FFD1DC", outline="#EC407A", width=3)

    def _flag_hover_out(self, event=None):
        self.flag_canvas.itemconfig(self.flag_circle,
                                    fill="#FFF0F2", outline="#FF6B81", width=2)

    def surrender(self):
        if self.starting or self.dialog_open:
            return
        self.dodge_enabled = False
        self.flag_canvas.itemconfig(self.flag_circle,
                                    fill="#FFE0E6", outline="#EC407A", width=3)
        self.flag_canvas.itemconfig(self.flag_text, fill="#EC407A")

        messagebox.showinfo(
            "投降成功",
            "启动按钮放弃了抵抗。\n\n"
            "现在它乖乖待在原地不动了。"
        )

    def setup_launch_view(self):
        self.arrow_canvas = tk.Canvas(self.launch_view, width=100, height=100,
                                      bg="#FFFFFF", highlightthickness=0)
        self.arrow_canvas.pack(pady=(30, 10))
        self.arrow_canvas.create_line(50, 88, 50, 25, fill="#FF8C9A",
                                      width=8, capstyle=tk.ROUND)
        self.arrow_canvas.create_line(50, 25, 20, 56, fill="#FF8C9A",
                                      width=8, capstyle=tk.ROUND)
        self.arrow_canvas.create_line(50, 25, 80, 56, fill="#FF8C9A",
                                      width=8, capstyle=tk.ROUND)
        self.arrow_canvas.create_line(22, 92, 78, 92, fill="#FF8C9A",
                                      width=7, capstyle=tk.ROUND)

        tk.Label(self.launch_view, text="正在启动游戏",
                 font=("Microsoft YaHei", 20, "bold"),
                 fg="#FF6B81", bg="#FFFFFF").pack(pady=(6, 0))
        tk.Label(self.launch_view, text="红石生电优化26.3",
                 font=("Microsoft YaHei", 12),
                 fg="#FF8C9A", bg="#FFFFFF").pack(pady=(4, 18))

        style = ttk.Style()
        style.theme_use('default')
        style.configure("Pink.Horizontal.TProgressbar",
                        troughcolor="#F0F0F0", background="#FF8C9A",
                        thickness=10, bordercolor="#FFFFFF",
                        lightcolor="#FF8C9A", darkcolor="#FF8C9A")

        ttk.Progressbar(self.launch_view, orient="horizontal", length=420,
                        mode="determinate",
                        style="Pink.Horizontal.TProgressbar",
                        variable=self.progress_var).pack(pady=12)

        info_frame = tk.Frame(self.launch_view, bg="#FFFFFF")
        info_frame.pack(pady=20, fill="x")
        info_frame.columnconfigure(0, weight=1)
        info_frame.columnconfigure(1, weight=0)
        info_frame.columnconfigure(2, weight=1)

        inner = tk.Frame(info_frame, bg="#FFFFFF")
        inner.grid(row=0, column=1)

        for i, (label, var) in enumerate([
            ("当前步骤", self.step_var),
            ("登录方式", self.auth_var),
            ("启动进度", self.progress_text_var),
        ]):
            tk.Label(inner, text=label, font=("Microsoft YaHei", 10),
                     fg="#888888", bg="#FFFFFF").grid(row=i, column=0,
                                                       sticky="w", pady=4)
            tk.Label(inner, textvariable=var,
                     font=("Microsoft YaHei", 10), fg="#333333",
                     bg="#FFFFFF", anchor="w", width=30).grid(
                row=i, column=1, sticky="w", pady=4, padx=(20, 0))

        tk.Button(self.launch_view, text="取消",
                  font=("Microsoft YaHei", 12),
                  bg="#FFFFFF", fg="#333333",
                  activebackground="#F0F0F0",
                  relief="solid", bd=1, cursor="hand2", height=2,
                  command=self.cancel_launch
                  ).pack(side="bottom", fill="x", padx=200, pady=25)

    def start_move(self, event):
        self.drag_x, self.drag_y = event.x, event.y

    def do_move(self, event):
        x = self.root.winfo_x() + event.x - self.drag_x
        y = self.root.winfo_y() + event.y - self.drag_y
        self.root.geometry(f"+{x}+{y}")

    def chase_tick(self):
        try:
            if not self.root.winfo_exists():
                return
            if self.dialog_open:
                self.root.after(30, self.chase_tick)
                return
            if (not self.starting and not self.is_flying_back
                    and self.dodge_enabled
                    and (self.float_win is None or not self.float_win.winfo_exists())):
                self.check_panel_dodge()
            self.root.after(30, self.chase_tick)
        except tk.TclError:
            pass

    def check_panel_dodge(self):
        now = time.time()
        if now < self.dodge_cooldown:
            return

        mx = self.root.winfo_pointerx()
        my = self.root.winfo_pointery()

        panel_ox = self.root.winfo_rootx()
        panel_oy = self.root.winfo_rooty() + self.TOP_H
        rx = mx - panel_ox
        ry = my - panel_oy
        panel_w = self.WIN_W
        panel_h = self.WIN_H - self.TOP_H

        if rx < 0 or ry < 0 or rx > panel_w or ry > panel_h:
            return

        cx = self.btn_x + self.BTN_W / 2
        cy = self.btn_y + self.BTN_H / 2
        dx = cx - rx
        dy = cy - ry
        dist = max((dx * dx + dy * dy) ** 0.5, 1)

        if dist > self.NEAR_DIST:
            return

        step = max(80, 300 - dist)
        new_x = self.btn_x + (dx / dist) * step
        new_y = self.btn_y + (dy / dist) * step

        max_x = panel_w - self.BTN_W
        max_y = panel_h - self.BTN_H
        new_x = max(0, min(max_x, new_x))
        new_y = max(0, min(max_y, new_y))

        if abs(new_x - self.btn_x) < 2 and abs(new_y - self.btn_y) < 2:
            new_x = random.uniform(0, max_x)
            new_y = random.uniform(0, max_y)

        self.btn_x = new_x
        self.btn_y = new_y
        try:
            self.start_btn.place(x=int(new_x), y=int(new_y),
                                 width=self.BTN_W, height=self.BTN_H)
        except tk.TclError:
            return

        self.dodge_cooldown = now + 0.05

    def on_main_clicked(self):
        if self.starting or self.is_flying_back or self.dialog_open:
            return
        if self.float_win is not None and self.float_win.winfo_exists():
            return

        try:
            self.start_btn.place_forget()
        except tk.TclError:
            pass

        self.spawn_floating_button()

    def spawn_floating_button(self):
        panel_w = self.WIN_W
        panel_h = self.WIN_H - self.TOP_H
        margin = 30
        fx = random.uniform(margin, panel_w - self.BTN_W - margin)
        fy = random.uniform(margin, panel_h - self.BTN_H - margin)
        self.float_x = fx
        self.float_y = fy

        root_x = self.root.winfo_rootx()
        root_y = self.root.winfo_rooty() + self.TOP_H
        abs_x = root_x + fx
        abs_y = root_y + fy

        self.float_win = tk.Toplevel(self.root)
        self.float_win.overrideredirect(True)
        self.float_win.attributes("-topmost", True)
        self.float_win.geometry(
            f"{self.BTN_W}x{self.BTN_H}+{int(abs_x)}+{int(abs_y)}")
        self.float_win.configure(bg=self.BTN_BG)

        float_btn = tk.Button(
            self.float_win, text=self.BTN_TEXT,
            font=self.BTN_FONT,
            bg=self.BTN_BG, fg=self.BTN_FG,
            activebackground=self.BTN_ABG, activeforeground=self.BTN_AFG,
            relief="solid", bd=self.BTN_BD, cursor="hand2",
            command=self.on_float_clicked)
        float_btn.pack(fill="both", expand=True)

        self.float_timer = self.root.after(self.FLOAT_LIFETIME_MS,
                                           self.float_timeout)

    def on_float_clicked(self):
        if self.float_win is None or not self.float_win.winfo_exists():
            return

        if self.float_timer is not None:
            try:
                self.root.after_cancel(self.float_timer)
            except Exception:
                pass
            self.float_timer = None

        try:
            self.float_win.destroy()
        except tk.TclError:
            pass
        self.float_win = None

        self.reset_main_button()
        self.start_game()

    def float_timeout(self):
        self.float_timer = None
        if self.float_win is None or not self.float_win.winfo_exists():
            return

        fx, fy = self.float_x, self.float_y

        try:
            self.float_win.destroy()
        except tk.TclError:
            pass
        self.float_win = None

        self.fly_home(fx, fy)

    def fly_home(self, from_x, from_y):
        target_x = float((self.WIN_W - self.BTN_W) // 2)
        target_y = float((self.WIN_H - self.TOP_H) - self.BTN_H - 140)

        try:
            self.start_btn.place(x=int(from_x), y=int(from_y),
                                 width=self.BTN_W, height=self.BTN_H)
        except tk.TclError:
            return

        self.is_flying_back = True

        steps = 22
        delay_ms = 14

        def step(i):
            if not self.root.winfo_exists():
                return
            t = i / steps
            ease = 1 - (1 - t) ** 3
            cur_x = from_x + (target_x - from_x) * ease
            cur_y = from_y + (target_y - from_y) * ease
            try:
                self.start_btn.place(x=int(cur_x), y=int(cur_y),
                                     width=self.BTN_W, height=self.BTN_H)
            except tk.TclError:
                return

            if i < steps:
                self.root.after(delay_ms, lambda: step(i + 1))
            else:
                self.btn_x = target_x
                self.btn_y = target_y
                try:
                    self.start_btn.place(x=int(target_x), y=int(target_y),
                                         width=self.BTN_W, height=self.BTN_H)
                except tk.TclError:
                    pass
                self.is_flying_back = False

        step(0)

    def start_game(self, event=None):
        if self.starting:
            return
        self.starting = True
        self.dodge_enabled = False
        self.is_flying_back = False

        self.launch_count += 1

        if self.float_timer is not None:
            try:
                self.root.after_cancel(self.float_timer)
            except Exception:
                pass
            self.float_timer = None
        if self.float_win is not None and self.float_win.winfo_exists():
            try:
                self.float_win.destroy()
            except tk.TclError:
                pass
            self.float_win = None

        self.init_view.pack_forget()
        self.launch_view.pack(fill="both", expand=True)
        self.progress_var.set(0.0)
        self.progress_text_var.set("0.00 %")
        self.step_var.set("准备启动...")
        self.auth_var.set("Authlib-Injector")

        self.root.after(500, lambda: self.run_stage(0))

    def run_stage(self, stage_index):
        if stage_index >= len(self.LAUNCH_STAGES):
            self.progress_var.set(99.0)
            self.progress_text_var.set("99.00 %")
            self.step_var.set("等待游戏窗口出现...")
            self.root.after(2500, self.fake_watcher_timeout)
            return

        stage_name, _ = self.LAUNCH_STAGES[stage_index]
        self.step_var.set(stage_name)

        start_pct = stage_index / len(self.LAUNCH_STAGES) * 99
        end_pct = (stage_index + 1) / len(self.LAUNCH_STAGES) * 99

        self.animate_stage(start_pct, end_pct, stage_index)

    def animate_stage(self, current, target, stage_index):
        stage_name, _ = self.LAUNCH_STAGES[stage_index]

        if current < target:
            current += random.uniform(0.5, 1.8)
            if current > target:
                current = target
            self.progress_var.set(current)
            self.progress_text_var.set(f"{current:.2f} %")

            if random.random() < 0.35:
                detail = random.choice(self.STAGE_DETAILS.get(stage_name, [""]))
                self.step_var.set(detail)

            self.root.after(random.randint(60, 140),
                            lambda: self.animate_stage(current, target, stage_index))
        else:
            self.root.after(random.randint(200, 600),
                            lambda: self.run_stage(stage_index + 1))

    def fake_watcher_timeout(self):
        self.shake_window()
        reason = random.choice(self.FAKE_CRASH_REASONS)
        messagebox.showerror(
            "启动失败 - CrashAnalyzer",
            f"错误代码：MOD_WATCHER_TIMEOUT\n\n"
            f"ModWatcher 监听超时，未找到 Minecraft 窗口。\n\n"
            f"疑似崩溃原因：\n{reason}\n\n"
            f"但是……这个启动器根本没有游戏文件。"
        )
        self.step_var.set("CrashAnalyzer 正在分析...")
        self.root.after(1000, self.rollback_progress)

    def rollback_progress(self):
        current = 99

        def step():
            nonlocal current
            if current > 0:
                current -= random.uniform(3, 10)
                if current < 0:
                    current = 0
                self.progress_var.set(current)
                self.progress_text_var.set(f"{current:.2f} %")
                self.step_var.set("回滚进度条...")
                self.root.after(50, step)
            else:
                self.step_var.set("重新尝试启动...")
                self.root.after(600, lambda: self.fast_forward(0, 100, 30))

        step()

    def fast_forward(self, current, target, delay):
        if current < target:
            current += random.uniform(3, 8)
            if current > target:
                current = target
            self.progress_var.set(current)
            self.progress_text_var.set(f"{current:.2f} %")
            self.step_var.set("正在启动... 别眨眼。")
            self.root.after(delay, lambda: self.fast_forward(current, target, delay))
        else:
            self.progress_var.set(100)
            self.progress_text_var.set("100.00 %")
            self.step_var.set("启动成功！")
            self.root.after(500, self.finish)

    def cancel_launch(self):
        messagebox.showwarning("取消失败",
                               "你已经被绑定了，无法取消！\n\n"
                               "请继续享受被玩弄的过程吧。")

    def finish(self):
        self.starting = False
        self.dodge_enabled = True
        self.dodge_cooldown = 0
        self.is_flying_back = False

        try:
            self.flag_canvas.itemconfig(self.flag_circle,
                                        fill="#FFF0F2", outline="#FF6B81", width=2)
            self.flag_canvas.itemconfig(self.flag_text, fill="#FF6B81")
        except tk.TclError:
            pass

        self.launch_view.pack_forget()
        self.init_view.pack(fill="both", expand=True)
        self.root.after(80, self.place_flag)
        self.reset_main_button()
        self.start_btn.config(text=self.BTN_TEXT)

        if self.launch_count == 1:
            messagebox.showinfo(
                "启动成功",
                "其实没有游戏。\n"
                "这个启动器的唯一功能，就是玩玩家。\n\n"
                "你被玩了 😄\n\n"
                "（再玩一次试试？）"
            )
        elif self.launch_count == 2:
            self.root.after(300, self.fake_shutdown)
        else:
            self.root.after(300, self.third_strike)

    # ==================== 第二次：假关机（现在改成假注销） ====================
    def fake_shutdown(self):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        self.shutdown_overlay = tk.Toplevel(self.root)
        self.shutdown_overlay.overrideredirect(True)
        self.shutdown_overlay.attributes("-topmost", True)
        self.shutdown_overlay.configure(bg="#000000")
        self.shutdown_overlay.geometry(f"{sw}x{sh}+0+0")

        # ⭐ 文案改成"正在注销..."
        tk.Label(self.shutdown_overlay, text="正在注销...",
                 font=("Microsoft YaHei", 32),
                 fg="#FFFFFF", bg="#000000").place(
            relx=0.5, rely=0.45, anchor="center")

        tk.Label(self.shutdown_overlay, text="正在保存你的设置",
                 font=("Microsoft YaHei", 14),
                 fg="#AAAAAA", bg="#000000").place(
            relx=0.5, rely=0.52, anchor="center")

        self._shutdown_dots_label = tk.Label(
            self.shutdown_overlay, text="·",
            font=("Microsoft YaHei", 20),
            fg="#FFFFFF", bg="#000000")
        self._shutdown_dots_label.place(relx=0.5, rely=0.58, anchor="center")
        self._animate_shutdown_dots(0)

        tk.Label(self.shutdown_overlay, text="按 ESC 取消",
                 font=("Microsoft YaHei", 9),
                 fg="#555555", bg="#000000").place(
            relx=0.5, rely=0.95, anchor="center")

        self.shutdown_overlay.bind("<Escape>",
                                   lambda e: self.end_fake_shutdown(canceled=True))

        self.root.after(4500,
                        lambda: self.end_fake_shutdown(canceled=False))

    def _animate_shutdown_dots(self, i):
        if self.shutdown_overlay is None or not self.shutdown_overlay.winfo_exists():
            return
        try:
            frames = ["·", "··", "···", "····", "···", "··"]
            self._shutdown_dots_label.config(text=frames[i % len(frames)])
            self.root.after(180, lambda: self._animate_shutdown_dots(i + 1))
        except tk.TclError:
            pass

    def end_fake_shutdown(self, canceled=False):
        if self.shutdown_overlay is not None and self.shutdown_overlay.winfo_exists():
            try:
                self.shutdown_overlay.destroy()
            except tk.TclError:
                pass
        self.shutdown_overlay = None

        if canceled:
            messagebox.showinfo(
                "逃生成功",
                "你居然发现了 ESC 可以取消……\n\n"
                "好吧，这次就放过你。\n\n"
                "但是别以为下一次也有这么好运 😏"
            )
        else:
            messagebox.showinfo(
                "注销完成（并没有）",
                "恭喜你！你被玩到了第二次。\n\n"
                "这只是一个假注销画面。\n\n"
                "再玩一次试试？"
            )

    # ==================== 第三次：桌面小按钮 → 真注销 ====================
    def third_strike(self):
        try:
            self.root.withdraw()
        except tk.TclError:
            return

        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        size = self.DESKTOP_BTN_SIZE
        margin = self.DESKTOP_BTN_MARGIN

        x = sw - size - margin
        y = sh - size - margin - 50

        self.desktop_btn = tk.Toplevel(self.root)
        self.desktop_btn.overrideredirect(True)
        self.desktop_btn.attributes("-topmost", True)
        self.desktop_btn.geometry(f"{size}x{size}+{x}+{y}")
        self.desktop_btn.configure(bg="#FF8C9A")

        btn = tk.Label(
            self.desktop_btn, text=self.DESKTOP_BTN_TEXT,
            font=("Microsoft YaHei", 14, "bold"),
            bg="#FF8C9A", fg="white", cursor="hand2")
        btn.pack(fill="both", expand=True)

        def on_enter(e):
            btn.config(bg="#FF6B81")

        def on_leave(e):
            btn.config(bg="#FF8C9A")

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)

        # ⭐ 左键点击 → 真注销
        btn.bind("<Button-1>", lambda e: self.real_logoff())

        # 右键拖动
        def start_drag(e):
            self.desktop_btn._drag_x = e.x
            self.desktop_btn._drag_y = e.y

        def do_drag(e):
            nx = self.desktop_btn.winfo_x() + e.x - self.desktop_btn._drag_x
            ny = self.desktop_btn.winfo_y() + e.y - self.desktop_btn._drag_y
            self.desktop_btn.geometry(f"+{nx}+{ny}")

        # 右键菜单：取消注销 / 退出
        menu = tk.Menu(self.desktop_btn, tearoff=0)
        menu.add_command(label="取消注销", command=self.cancel_logoff)
        menu.add_command(label="关闭小按钮", command=self.root.destroy)

        def show_menu(e):
            menu.tk_popup(e.x_root, e.y_root)

        btn.bind("<Button-3>", start_drag)
        btn.bind("<B3-Motion>", do_drag)
        btn.bind("<Button-3>", show_menu, add="+")

    # ==================== 真注销 ====================
    def real_logoff(self):
        """⚠️ 真的会注销（延迟 LOGOFF_DELAY_SECONDS 秒，可取消）"""
        # 已经点过就忽略
        if self.logoff_timer is not None:
            return

        # 用 tkinter after 实现延迟（Windows 的 shutdown /l 没有 /t 参数）
        self.logoff_timer = self.root.after(
            self.LOGOFF_DELAY_SECONDS * 1000,
            self._do_logoff_now)

        # 弹一个倒计时窗（让用户知道发生了什么）
        self._logoff_countdown(self.LOGOFF_DELAY_SECONDS)

    def _logoff_countdown(self, seconds_left):
        """显示注销倒计时"""
        if seconds_left <= 0:
            return
        try:
            if hasattr(self, "_countdown_win") and self._countdown_win is not None \
                    and self._countdown_win.winfo_exists():
                self._countdown_win.destroy()

            self._countdown_win = tk.Toplevel(self.root)
            self._countdown_win.overrideredirect(True)
            self._countdown_win.attributes("-topmost", True)
            self._countdown_win.configure(bg="#000000")
            self._countdown_win.geometry("380x120+{}+{}".format(
                (self.root.winfo_screenwidth() - 380) // 2,
                (self.root.winfo_screenheight() - 120) // 2))

            tk.Label(self._countdown_win,
                     text=f"{seconds_left} 秒后注销",
                     font=("Microsoft YaHei", 20, "bold"),
                     fg="#FFFFFF", bg="#000000").pack(pady=(20, 5))
            tk.Label(self._countdown_win,
                     text="右键右下角 PCL 按钮 → 取消注销",
                     font=("Microsoft YaHei", 10),
                     fg="#AAAAAA", bg="#000000").pack()

            self.root.after(1000,
                            lambda: self._logoff_countdown(seconds_left - 1))
        except tk.TclError:
            pass

    def _do_logoff_now(self):
        """执行真正的注销命令"""
        self.logoff_timer = None
        try:
            if hasattr(self, "_countdown_win") and self._countdown_win is not None \
                    and self._countdown_win.winfo_exists():
                self._countdown_win.destroy()
        except tk.TclError:
            pass

        try:
            if sys.platform.startswith("win"):
                # Windows：立即注销当前用户
                os.system("shutdown /l")
            elif sys.platform == "darwin":
                # macOS：调用 AppleScript 注销
                os.system(
                    'osascript -e \'tell application "System Events" '
                    'to log out\'')
            else:
                # Linux：尝试几个常见桌面环境的注销命令
                for cmd in [
                    "gnome-session-quit --logout --no-prompt",
                    "qdbus org.kde.ksmserver /KSMServer logout 0 0 0",
                    "xfce4-session-logout --logout",
                    "loginctl terminate-user $USER",
                ]:
                    if os.system(cmd) == 0:
                        break
        except Exception as e:
            print("注销命令执行失败：", e)

    def cancel_logoff(self):
        """取消待执行的注销"""
        if self.logoff_timer is not None:
            try:
                self.root.after_cancel(self.logoff_timer)
            except Exception:
                pass
            self.logoff_timer = None

        try:
            if hasattr(self, "_countdown_win") and self._countdown_win is not None \
                    and self._countdown_win.winfo_exists():
                self._countdown_win.destroy()
        except tk.TclError:
            pass

        messagebox.showinfo(
            "已取消",
            "注销已取消。\n\n"
            "……算你跑得快 😏"
        )

    def shake_window(self, count=8, orig=None):
        if orig is None:
            orig = (self.root.winfo_x(), self.root.winfo_y())
        if count <= 0:
            self.root.geometry(f"+{orig[0]}+{orig[1]}")
            return
        x = orig[0] + random.randint(-10, 10)
        y = orig[1] + random.randint(-10, 10)
        self.root.geometry(f"+{x}+{y}")
        self.root.after(30, lambda: self.shake_window(count - 1, orig))


if __name__ == "__main__":
    root = tk.Tk()
    app = PCL_PlayerLauncher(root)
    root.mainloop()