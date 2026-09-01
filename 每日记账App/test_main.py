# -*- coding: utf-8 -*-
"""每日记账 App 的单元测试。
用临时数据库跑，绝不会碰到真实的 records.db。
"""
import os
import tempfile
import unittest
from datetime import date

import main


class RecordTest(unittest.TestCase):
    """花销部分：记账、查账、删账、汇总。"""

    def setUp(self):
        # 把数据库指到临时文件夹，测完自动清理，不碰真实账本
        self._tmp = tempfile.TemporaryDirectory()
        main.DB_PATH = os.path.join(self._tmp.name, "test_records.db")
        main.init_db()

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_and_get_record(self):
        main.add_record(12.5, "餐饮", "午餐", "吃了个面", "2026-08-30")
        rows = main.get_records()
        self.assertEqual(len(rows), 1)
        rid, d, c1, c2, amt, note = rows[0]
        self.assertEqual(d, "2026-08-30")
        self.assertEqual(c1, "餐饮")
        self.assertEqual(c2, "午餐")
        self.assertEqual(amt, 12.5)
        self.assertEqual(note, "吃了个面")

    def test_get_records_empty(self):
        self.assertEqual(main.get_records(), [])

    def test_get_records_filter_by_month(self):
        main.add_record(10, "餐饮", "早餐", "", "2026-08-01")
        main.add_record(20, "交通", "打车", "", "2026-07-15")
        rows = main.get_records("2026-08")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "2026-08-01")

    def test_get_records_order_newest_first(self):
        main.add_record(1, "餐饮", "早餐", "", "2026-08-01")
        main.add_record(2, "餐饮", "早餐", "", "2026-08-02")
        rows = main.get_records()
        self.assertEqual(rows[0][1], "2026-08-02")
        self.assertEqual(rows[1][1], "2026-08-01")

    def test_delete_record(self):
        main.add_record(5, "餐饮", "午餐", "", "2026-08-30")
        rid = main.get_records()[0][0]
        main.delete_record(rid)
        self.assertEqual(main.get_records(), [])

    def test_delete_nonexistent_record(self):
        # 删一条不存在的记录，不应该报错
        main.delete_record(99999)

    def test_available_months(self):
        main.add_record(1, "餐饮", "早餐", "", "2026-08-01")
        main.add_record(2, "餐饮", "早餐", "", "2026-07-01")
        self.assertEqual(main.get_available_months(), ["2026-08", "2026-07"])

    def test_available_months_empty(self):
        self.assertEqual(main.get_available_months(), [])

    def test_summary(self):
        main.add_record(10, "餐饮", "早餐", "", "2026-08-01")
        main.add_record(30, "餐饮", "午餐", "", "2026-08-02")
        main.add_record(20, "交通", "打车", "", "2026-08-03")
        total, rows = main.get_summary("2026-08")
        self.assertEqual(total, 60)
        # 按金额从多到少：餐饮 40 在前，交通 20 在后
        self.assertEqual([r[0] for r in rows], ["餐饮", "交通"])
        self.assertEqual(rows[0][1], 40)
        self.assertEqual(rows[0][2], 2)  # 餐饮两笔
        self.assertEqual(rows[1][1], 20)

    def test_summary_empty_month(self):
        total, rows = main.get_summary("2026-01")
        self.assertEqual(total, 0)
        self.assertEqual(rows, [])

    def test_daily_expenses(self):
        main.add_record(10, "餐饮", "早餐", "", "2026-08-01")
        main.add_record(5, "餐饮", "午餐", "", "2026-08-01")
        main.add_record(20, "交通", "打车", "", "2026-08-03")
        rows = main.get_daily_expenses("2026-08-01", "2026-08-31")
        self.assertEqual(rows, [("2026-08-01", 15.0), ("2026-08-03", 20.0)])

    def test_daily_expenses_empty_range(self):
        self.assertEqual(main.get_daily_expenses("2026-01-01", "2026-01-31"), [])


class IncomeTest(unittest.TestCase):
    """收入部分：记收入、查收入、删收入、统计。"""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        main.DB_PATH = os.path.join(self._tmp.name, "test_records.db")
        main.init_db()

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_and_get_income(self):
        main.add_income(100, "生活费", "爸妈给的生活费", "2026-08-30")
        rows = main.get_incomes()
        self.assertEqual(len(rows), 1)
        rid, d, src, amt, note = rows[0]
        self.assertEqual(d, "2026-08-30")
        self.assertEqual(src, "生活费")
        self.assertEqual(amt, 100)
        self.assertEqual(note, "爸妈给的生活费")

    def test_get_incomes_empty(self):
        self.assertEqual(main.get_incomes(), [])

    def test_get_incomes_filter_by_month(self):
        main.add_income(100, "生活费", "", "2026-08-01")
        main.add_income(200, "红包", "", "2026-07-10")
        rows = main.get_incomes("2026-08")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][1], "2026-08-01")

    def test_delete_income(self):
        main.add_income(100, "生活费", "", "2026-08-30")
        rid = main.get_incomes()[0][0]
        main.delete_income(rid)
        self.assertEqual(main.get_incomes(), [])

    def test_delete_nonexistent_income(self):
        main.delete_income(99999)

    def test_income_summary(self):
        main.add_income(100, "生活费", "", "2026-08-01")
        main.add_income(50, "红包", "", "2026-08-02")
        self.assertEqual(main.get_income_summary("2026-08"), 150)

    def test_income_summary_empty_month(self):
        self.assertEqual(main.get_income_summary("2026-01"), 0)

    def test_available_income_months(self):
        main.add_income(100, "生活费", "", "2026-08-01")
        main.add_income(200, "红包", "", "2026-07-10")
        self.assertEqual(main.get_available_income_months(), ["2026-08", "2026-07"])

    def test_income_total_by_range(self):
        main.add_income(100, "生活费", "", "2026-08-01")
        main.add_income(50, "红包", "", "2026-08-31")
        main.add_income(999, "红包", "", "2027-01-01")
        self.assertEqual(main.get_income_total_by_range("2026-08-01", "2026-08-31"), 150)

    def test_income_total_by_range_empty(self):
        self.assertEqual(main.get_income_total_by_range("2026-01-01", "2026-01-31"), 0)


class WeekTest(unittest.TestCase):
    """每周功能：算某天所在周的周一。"""

    def test_week_start_sunday(self):
        # 2026-08-30 是周日，所在周的周一是 08-24
        self.assertEqual(main._week_start(date(2026, 8, 30)).isoformat(), "2026-08-24")

    def test_week_start_monday_itself(self):
        # 本身就是周一，返回它自己
        self.assertEqual(main._week_start(date(2026, 8, 24)).isoformat(), "2026-08-24")

    def test_week_start_friday(self):
        # 2026-08-28 是周五，所在周的周一还是 08-24
        self.assertEqual(main._week_start(date(2026, 8, 28)).isoformat(), "2026-08-24")


if __name__ == "__main__":
    unittest.main()
