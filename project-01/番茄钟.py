# -*- coding: utf-8 -*-
"""桌面番茄钟：学习 50 分钟 -> 休息 10 分钟，自动循环，到点弹窗+声音提醒。"""
import threading
import tkinter as tk
from tkinter import ttk
import winsound

BG = "#1E272E"
FG = "#ECF0F1"
STUDY_COLOR = "#FF6B6B"
REST_COLOR = "#2ECC71"
MUTED = "#7F8C8D"
MAX_DOTS = 8

STUDY_MIN_DEFAULT = 50
REST_MIN_DEFAULT = 10


def play_alarm():
    # 到点提醒音：按 880Hz、660Hz、880Hz、990Hz 的顺序响"叮咚叮咚"
    for freq, dur in ((880, 250), (660, 250), (880, 250), (990, 400)):
        winsound.Beep(freq, dur)


class PomodoroApp:
    """番茄钟主程序：学习/休息两阶段自动循环，带倒计时、进度圆点和到点提醒。"""

    def __init__(self, root):
        self.root = root
        root.title("番茄钟")
        root.configure(bg=BG)
        root.resizable(False, False)
        root.attributes("-topmost", True)  # 窗口置顶，别被其他窗口挡住

        self.study_secs = STUDY_MIN_DEFAULT * 60
        self.rest_secs = REST_MIN_DEFAULT * 60
        self.phase = "study"
        self.remaining = self.study_secs
        self.running = False
        self.completed = 0
        self.timer_id = None

        self._build_ui()
        self._update_display()
        self._schedule_tick()

    # ---------- 界面 ----------
    def _build_ui(self):
        pad = dict(padx=16, pady=6)

        self.phase_label = tk.Label(
            self.root, text="", font=("Microsoft YaHei UI", 16, "bold"),
            bg=BG, fg=FG)
        self.phase_label.grid(row=0, column=0, **pad)

        self.time_label = tk.Label(
            self.root, text="", font=("Consolas", 40, "bold"),
            bg=BG, fg=FG)
        self.time_label.grid(row=1, column=0, **pad)

        self.dots_label = tk.Label(
            self.root, text="", font=("Microsoft YaHei UI", 11),
            bg=BG, fg=MUTED)
        self.dots_label.grid(row=2, column=0, **pad)

        # 按钮行
        btn_row = tk.Frame(self.root, bg=BG)
        btn_row.grid(row=3, column=0, **pad)
        self.start_btn = self._button(btn_row, "开始", self.toggle)
        self.start_btn.pack(side="left", padx=3)
        self.skip_btn = self._button(btn_row, "跳过", self.skip)
        self.skip_btn.pack(side="left", padx=3)
        self._button(btn_row, "重置", self.reset).pack(side="left", padx=3)

        # 时长设置行
        set_row = tk.Frame(self.root, bg=BG)
        set_row.grid(row=4, column=0, **pad)
        tk.Label(set_row, text="学习", bg=BG, fg=FG,
                 font=("Microsoft YaHei UI", 10)).pack(side="left")
        self.study_spin = ttk.Spinbox(set_row, from_=1, to=240, width=4,
                                      font=("Microsoft YaHei UI", 10))
        self.study_spin.set(STUDY_MIN_DEFAULT)
        self.study_spin.pack(side="left", padx=(2, 4))
        tk.Label(set_row, text="分", bg=BG, fg=FG,
                 font=("Microsoft YaHei UI", 10)).pack(side="left")
        tk.Label(set_row, text=" 休息", bg=BG, fg=FG,
                 font=("Microsoft YaHei UI", 10)).pack(side="left")
        self.rest_spin = ttk.Spinbox(set_row, from_=1, to=120, width=4,
                                     font=("Microsoft YaHei UI", 10))
        self.rest_spin.set(REST_MIN_DEFAULT)
        self.rest_spin.pack(side="left", padx=(2, 4))
        tk.Label(set_row, text="分", bg=BG, fg=FG,
                 font=("Microsoft YaHei UI", 10)).pack(side="left")
        self._button(set_row, "应用", self.apply_settings).pack(
            side="left", padx=(8, 0))

    def _button(self, parent, text, command):
        return tk.Button(
            parent, text=text, command=command,
            bg="#2F3A44", fg=FG, activebackground="#3D4A56",
            activeforeground=FG, relief="flat", bd=0, padx=10, pady=4,
            font=("Microsoft YaHei UI", 10))

    # ---------- 计时 ----------
    def _schedule_tick(self):
        """安排 1 秒后的下一次倒计时跳动，形成循环。"""
        if self.timer_id:
            self.root.after_cancel(self.timer_id)
        self.timer_id = self.root.after(1000, self._tick)

    def _tick(self):
        """每秒减 1 秒；时间到 0 就切换学习/休息阶段。"""
        if self.running:
            self.remaining -= 1
            if self.remaining <= 0:
                self.remaining = 0
                self._update_display()
                self._on_time_up()
                return  # _on_time_up 会重新安排下一次 tick
        self._update_display()
        self._schedule_tick()

    def _on_time_up(self):
        """时间到：学习结束弹休息提醒，休息结束弹继续学习提醒。"""
        if self.phase == "study":
            self.completed += 1
            self._remind("该休息啦",
                         f"已完成 {self.completed} 轮，站起来活动 {self.rest_secs // 60} 分钟吧！")
            self.phase = "rest"
            self.remaining = self.rest_secs
        else:
            self._remind("休息结束",
                         "继续学习，保持专注！")
            self.phase = "study"
            self.remaining = self.study_secs
        self._update_display()
        self._schedule_tick()  # 自动进入下一阶段，继续倒计时

    # ---------- 提醒 ----------
    def _remind(self, title, message):
        # 声音在后台线程里播，不然 Beep 响的时候提醒窗口会卡住
        threading.Thread(target=play_alarm, daemon=True).start()
        win = tk.Toplevel(self.root)
        win.title(title)
        win.configure(bg=BG)
        win.resizable(False, False)
        win.attributes("-topmost", True)
        color = STUDY_COLOR if self.phase == "study" else REST_COLOR
        tk.Label(win, text=title, font=("Microsoft YaHei UI", 26, "bold"),
                 bg=BG, fg=color).pack(padx=40, pady=(24, 4))
        tk.Label(win, text=message, font=("Microsoft YaHei UI", 13),
                 bg=BG, fg=FG).pack(padx=40, pady=(0, 8))
        tk.Button(win, text="知道了", command=win.destroy,
                  bg="#2F3A44", fg=FG, activebackground="#3D4A56",
                  activeforeground=FG, relief="flat", bd=0,
                  padx=28, pady=6,
                  font=("Microsoft YaHei UI", 11)).pack(pady=(4, 22))
        win.grab_set()  # 锁住其他窗口，不点"知道了"就不能操作主界面

    # ---------- 按钮动作 ----------
    def toggle(self):
        self.running = not self.running
        self.start_btn.config(text="暂停" if self.running else "开始")

    def skip(self):
        if self.phase == "study":
            self.phase = "rest"
            self.remaining = self.rest_secs
        else:
            self.phase = "study"
            self.remaining = self.study_secs
        self._update_display()

    def reset(self):
        self.running = False
        self.start_btn.config(text="开始")
        self.remaining = self.study_secs if self.phase == "study" else self.rest_secs
        self._update_display()

    def apply_settings(self):
        try:
            study_min = int(self.study_spin.get())
            rest_min = int(self.rest_spin.get())
        except ValueError:
            return
        # 最少 1 分钟，防止把时长设成 0 或负数导致倒计时异常
        self.study_secs = max(1, study_min) * 60
        self.rest_secs = max(1, rest_min) * 60
        # 更新当前阶段计时为新的时长
        self.remaining = self.study_secs if self.phase == "study" else self.rest_secs
        self._update_display()

    # ---------- 显示 ----------
    def _fmt(self, secs):
        """把秒数转成 mm:ss 或 h:mm:ss 的显示格式。"""
        m, s = divmod(max(0, secs), 60)
        h, m = divmod(m, 60)
        return f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def _update_display(self):
        is_study = self.phase == "study"
        color = STUDY_COLOR if is_study else REST_COLOR
        self.phase_label.config(
            text="🍅 学习" if is_study else "☕ 休息",
            fg=color)
        self.time_label.config(text=self._fmt(self.remaining), fg=color)

        # 用圆点显示进度：8 个为一圈，满 8 轮后从头再数
        cycle = self.completed % MAX_DOTS
        if cycle == 0 and self.completed > 0:
            cycle = MAX_DOTS  # 刚满 8 轮时显示 8 个实心点，而不是 0 个
        dots = "● " * cycle + "○ " * (MAX_DOTS - cycle)
        self.dots_label.config(text=f"{dots.strip()}   已完成 {self.completed} 轮")


if __name__ == "__main__":
    root = tk.Tk()
    PomodoroApp(root)
    root.mainloop()
