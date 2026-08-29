"""每日记账：一个简单的本地记账程序（Python + Tkinter + SQLite）"""
import os
import sqlite3
import tkinter as tk
from datetime import date, datetime
from tkinter import messagebox, ttk

# 数据库文件放在程序所在文件夹里
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "records.db")

# 花销分类：一级大类 -> 二级小类列表
CATEGORIES = {
    "餐饮": ["早餐", "午餐", "晚餐", "外卖", "零食饮料", "聚餐"],
    "交通": ["公交地铁", "打车", "加油", "停车", "火车机票", "共享单车"],
    "购物": ["日用品", "服饰", "电子产品", "化妆护肤", "其他购物"],
    "居住": ["房租", "水费", "电费", "燃气费", "物业费", "网费话费"],
    "娱乐": ["电影", "游戏", "旅游", "运动健身", "其他娱乐"],
    "医疗": ["药品", "门诊", "体检", "其他医疗"],
    "教育": ["书籍", "课程培训", "文具", "其他教育"],
    "人情": ["礼物", "红包", "请客", "其他社交"],
    "其他": ["其他"],
}


def _query(sql, params=(), one=False):
    """查数据库，返回结果。用完自动关闭连接。"""
    conn = sqlite3.connect(DB_PATH)
    try:
        cur = conn.execute(sql, params)
        return cur.fetchone() if one else cur.fetchall()
    finally:
        conn.close()


def _execute(sql, params=()):
    """改数据库（新增、删除）。用完自动关闭连接。"""
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(sql, params)
        conn.commit()
    finally:
        conn.close()


def init_db():
    """第一次运行时自动建表。"""
    _execute(
        """
        CREATE TABLE IF NOT EXISTS records (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            amount     REAL NOT NULL,
            category1  TEXT NOT NULL,
            category2  TEXT NOT NULL,
            note       TEXT NOT NULL DEFAULT '',
            date       TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
        """
    )


def add_record(amount, category1, category2, note, date_str):
    _execute(
        "INSERT INTO records (amount, category1, category2, note, date) VALUES (?, ?, ?, ?, ?)",
        (amount, category1, category2, note, date_str),
    )


def get_records(month=None):
    """取记录。month 填 YYYY-MM 时只取那个月，不填取全部。按日期从新到旧排。"""
    if month:
        rows = _query(
            "SELECT id, date, category1, category2, amount, note FROM records "
            "WHERE substr(date, 1, 7) = ? ORDER BY date DESC, id DESC",
            (month,),
        )
    else:
        rows = _query(
            "SELECT id, date, category1, category2, amount, note FROM records "
            "ORDER BY date DESC, id DESC"
        )
    return rows


def delete_record(record_id):
    _execute("DELETE FROM records WHERE id = ?", (record_id,))


def get_available_months():
    """数据库里出现过的月份列表，从新到旧。"""
    rows = _query("SELECT DISTINCT substr(date, 1, 7) FROM records ORDER BY 1 DESC")
    return [r[0] for r in rows]


def get_summary(month):
    """某个月的总支出，以及按一级分类的汇总（金额从多到少）。"""
    total = _query(
        "SELECT COALESCE(SUM(amount), 0) FROM records WHERE substr(date, 1, 7) = ?",
        (month,),
        one=True,
    )[0]
    rows = _query(
        "SELECT category1, SUM(amount), COUNT(*) FROM records "
        "WHERE substr(date, 1, 7) = ? GROUP BY category1 ORDER BY 2 DESC",
        (month,),
    )
    return total, rows


class App:
    """程序的主窗口，包含三个页签：记账、明细、汇总。"""

    def __init__(self, root):
        self.root = root
        self.status_var = tk.StringVar(value="就绪")

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self._build_record_tab()
        self._build_list_tab()
        self._build_summary_tab()

        status = ttk.Label(root, textvariable=self.status_var, anchor="w", relief="sunken")
        status.pack(fill="x", side="bottom")

        self._refresh_list()
        self._refresh_summary()

    # ---------- 页签 1：记账 ----------

    def _build_record_tab(self):
        tab = ttk.Frame(self.notebook, padding=24)
        self.notebook.add(tab, text="记账")

        ttk.Label(tab, text="日期（年月日，如 2026-08-29）").grid(row=0, column=0, sticky="w", pady=6)
        self.date_var = tk.StringVar(value=date.today().isoformat())
        ttk.Entry(tab, textvariable=self.date_var, width=24).grid(row=0, column=1, sticky="w", pady=6)

        ttk.Label(tab, text="金额（元）").grid(row=1, column=0, sticky="w", pady=6)
        self.amount_var = tk.StringVar()
        self.amount_entry = ttk.Entry(tab, textvariable=self.amount_var, width=24)
        self.amount_entry.grid(row=1, column=1, sticky="w", pady=6)

        ttk.Label(tab, text="一级分类").grid(row=2, column=0, sticky="w", pady=6)
        self.cat1_var = tk.StringVar()
        self.cat1_combo = ttk.Combobox(
            tab, textvariable=self.cat1_var, state="readonly", width=21,
            values=list(CATEGORIES.keys()),
        )
        self.cat1_combo.grid(row=2, column=1, sticky="w", pady=6)
        self.cat1_combo.bind("<<ComboboxSelected>>", self._on_cat1_change)

        ttk.Label(tab, text="二级分类").grid(row=3, column=0, sticky="w", pady=6)
        self.cat2_var = tk.StringVar()
        self.cat2_combo = ttk.Combobox(tab, textvariable=self.cat2_var, state="readonly", width=21)
        self.cat2_combo.grid(row=3, column=1, sticky="w", pady=6)

        ttk.Label(tab, text="备注（可不填）").grid(row=4, column=0, sticky="w", pady=6)
        self.note_var = tk.StringVar()
        ttk.Entry(tab, textvariable=self.note_var, width=32).grid(row=4, column=1, sticky="w", pady=6)

        ttk.Button(tab, text="保存这笔花销", command=self._save_record).grid(
            row=5, column=0, columnspan=2, pady=18
        )
        ttk.Label(
            tab,
            text="提示：选完一级分类，二级分类会自动换成对应的小类。",
            foreground="#888888",
        ).grid(row=6, column=0, columnspan=2, sticky="w")

    def _on_cat1_change(self, _event=None):
        cat1 = self.cat1_var.get()
        self.cat2_combo["values"] = CATEGORIES.get(cat1, [])
        self.cat2_var.set("")

    def _save_record(self):
        date_str = self.date_var.get().strip()
        amount_str = self.amount_var.get().strip()
        cat1 = self.cat1_var.get()
        cat2 = self.cat2_var.get()
        note = self.note_var.get().strip()

        try:
            datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("日期不对", "日期请按 2026-08-29 这样的格式填（年月日用横杠隔开）。")
            return

        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("金额不对", "金额要是大于 0 的数字，比如 12.5。")
            return

        if not cat1 or not cat2:
            messagebox.showerror("分类没选", "请先选一级分类和二级分类。")
            return

        add_record(amount, cat1, cat2, note, date_str)
        self.status_var.set(f"已保存：{date_str}  {cat1}-{cat2}  {amount:.2f} 元")
        self.amount_var.set("")
        self.note_var.set("")
        self.amount_entry.focus_set()
        self._refresh_list()
        self._refresh_summary()

    # ---------- 页签 2：明细 ----------

    def _build_list_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="明细")

        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="查看月份").pack(side="left")
        self.month_var_list = tk.StringVar(value="全部")
        self.month_combo_list = ttk.Combobox(
            top, textvariable=self.month_var_list, state="readonly", width=12, values=["全部"]
        )
        self.month_combo_list.pack(side="left", padx=8)
        self.month_combo_list.bind("<<ComboboxSelected>>", lambda _e: self._refresh_list())

        self.tree = ttk.Treeview(
            tab, columns=("date", "c1", "c2", "amount", "note", "id"),
            show="headings", selectmode="browse",
        )
        self.tree.heading("date", text="日期")
        self.tree.heading("c1", text="一级分类")
        self.tree.heading("c2", text="二级分类")
        self.tree.heading("amount", text="金额（元）")
        self.tree.heading("note", text="备注")
        self.tree.column("date", width=110, anchor="center")
        self.tree.column("c1", width=90, anchor="center")
        self.tree.column("c2", width=100, anchor="center")
        self.tree.column("amount", width=100, anchor="e")
        self.tree.column("note", width=260, anchor="w")
        self.tree.column("id", width=0, stretch=False)
        self.tree.pack(fill="both", expand=True)

        bar = ttk.Frame(tab)
        bar.pack(fill="x", pady=(6, 0))
        ttk.Button(bar, text="删除选中的记录", command=self._delete_selected).pack(side="left")
        ttk.Label(bar, text="先点选一行，再点删除", foreground="#888888").pack(side="left", padx=10)

    def _refresh_list(self):
        months = get_available_months()
        self.month_combo_list["values"] = ["全部"] + months
        if self.month_var_list.get() not in ["全部"] + months:
            self.month_var_list.set("全部")

        month = self.month_var_list.get()
        rows = get_records(month if month != "全部" else None)

        self.tree.delete(*self.tree.get_children())
        for rid, d, c1, c2, amt, note in rows:
            self.tree.insert("", "end", values=(d, c1, c2, f"{amt:.2f}", note, rid))

    def _delete_selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("没选中", "请先在表格里点选要删除的那一行。")
            return
        item = self.tree.item(selection[0])
        rid = item["values"][-1]
        if messagebox.askyesno("确认删除", "确定要删除这条记录吗？删了就没法恢复了。"):
            delete_record(rid)
            self._refresh_list()
            self._refresh_summary()
            self.status_var.set("已删除一条记录")

    # ---------- 页签 3：汇总 ----------

    def _build_summary_tab(self):
        tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(tab, text="汇总")

        top = ttk.Frame(tab)
        top.pack(fill="x", pady=(0, 6))
        ttk.Label(top, text="查看月份").pack(side="left")
        self.month_var_sum = tk.StringVar()
        self.month_combo_sum = ttk.Combobox(
            top, textvariable=self.month_var_sum, state="readonly", width=12
        )
        self.month_combo_sum.pack(side="left", padx=8)
        self.month_combo_sum.bind("<<ComboboxSelected>>", lambda _e: self._refresh_summary())

        self.summary_label_var = tk.StringVar()
        ttk.Label(
            tab, textvariable=self.summary_label_var,
            font=("Microsoft YaHei UI", 14, "bold"),
        ).pack(anchor="w", pady=(4, 10))

        bottom = ttk.Frame(tab)
        bottom.pack(fill="both", expand=True)

        self.summary_tree = ttk.Treeview(bottom, columns=("c1", "total", "count"), show="headings")
        self.summary_tree.heading("c1", text="一级分类")
        self.summary_tree.heading("total", text="金额（元）")
        self.summary_tree.heading("count", text="笔数")
        self.summary_tree.column("c1", width=140, anchor="w")
        self.summary_tree.column("total", width=140, anchor="e")
        self.summary_tree.column("count", width=80, anchor="center")
        self.summary_tree.pack(side="left", fill="both", expand=True)

        self.chart = tk.Canvas(bottom, width=300, bg="white", highlightthickness=0)
        self.chart.pack(side="right", fill="y", padx=(10, 0))

    def _refresh_summary(self):
        months = get_available_months()
        self.month_combo_sum["values"] = months
        if not months:
            self.month_var_sum.set("")
            self.summary_label_var.set("还没有记录，先到「记账」页记一笔吧")
            self.summary_tree.delete(*self.summary_tree.get_children())
            self._draw_chart([])
            return

        if self.month_var_sum.get() not in months:
            self.month_var_sum.set(months[0])

        month = self.month_var_sum.get()
        total, rows = get_summary(month)
        self.summary_label_var.set(f"{month} 总支出：{total:.2f} 元")

        self.summary_tree.delete(*self.summary_tree.get_children())
        for c1, amt, cnt in rows:
            self.summary_tree.insert("", "end", values=(c1, f"{amt:.2f}", cnt))

        self._draw_chart(rows)

    def _draw_chart(self, rows):
        """用色块画一个简单的横向柱状图，长度代表花销多少。"""
        self.chart.delete("all")
        if not rows:
            return
        max_amt = max(r[1] for r in rows) or 1
        width = int(self.chart["width"])
        height = max(40, len(rows) * 30 + 10)
        self.chart.config(height=height)
        for i, (c1, amt, _cnt) in enumerate(rows):
            y = 12 + i * 30
            bar_w = int((amt / max_amt) * (width - 96))
            self.chart.create_rectangle(96, y, 96 + bar_w, y + 20, fill="#4a90d9", outline="")
            self.chart.create_text(88, y + 10, text=c1, anchor="e", font=("Microsoft YaHei UI", 9))
            self.chart.create_text(
                96 + bar_w + 6, y + 10, text=f"{amt:.0f}",
                anchor="w", font=("Microsoft YaHei UI", 9),
            )


def main():
    init_db()
    root = tk.Tk()
    root.title("每日记账")
    root.geometry("920x640")
    root.minsize(800, 560)

    style = ttk.Style()
    try:
        style.theme_use("vista")
    except tk.TclError:
        pass
    style.configure(".", font=("Microsoft YaHei UI", 10))
    style.configure("Treeview", rowheight=26)

    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
