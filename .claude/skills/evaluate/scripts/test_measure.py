# -*- coding: utf-8 -*-
"""measure.py 的单元测试。

只测纯逻辑：文件名清洗、单条检查、按 spec 跑检查并写小卡。
涉及 git 的检查用临时仓库；不碰项目本身、不联网。
"""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import measure


def _make_git_repo(tmp):
    subprocess.run(["git", "init", "-q", tmp], capture_output=True, text=True)
    return Path(tmp)


class TestSlug(unittest.TestCase):

    def test_plain_text(self):
        self.assertEqual(measure.slug("hello"), "hello")

    def test_spaces_become_underscore(self):
        self.assertEqual(measure.slug("my file.txt"), "my_file.txt")

    def test_path_separators(self):
        self.assertEqual(measure.slug("a/b\\c"), "a_b_c")

    def test_chinese_kept(self):
        # 中文属于 \w，应保留；其中的空格变下划线
        self.assertEqual(measure.slug("中文 标题"), "中文_标题")

    def test_all_symbols_becomes_unnamed(self):
        # 边界：全是符号 → 兜底 "unnamed"
        self.assertEqual(measure.slug("!!!"), "unnamed")

    def test_empty_becomes_unnamed(self):
        self.assertEqual(measure.slug(""), "unnamed")


class TestCheckOne(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = Path(self._tmp.name)
        self.file = self.d / "f.txt"
        self.file.write_text("hello world", encoding="utf-8")
        self.empty = self.d / "empty.txt"
        self.empty.write_text("", encoding="utf-8")
        self.missing = self.d / "nope.txt"

    def test_exists(self):
        self.assertEqual(measure.check_one("exists", str(self.file), ""), (True, "存在"))
        self.assertEqual(measure.check_one("exists", str(self.missing), ""), (False, "不存在"))

    def test_file(self):
        self.assertEqual(measure.check_one("file", str(self.file), ""), (True, "是文件"))
        ok, detail = measure.check_one("file", str(self.d), "")
        self.assertFalse(ok)

    def test_dir(self):
        self.assertEqual(measure.check_one("dir", str(self.d), ""), (True, "是目录"))
        ok, _ = measure.check_one("dir", str(self.file), "")
        self.assertFalse(ok)

    def test_is_empty(self):
        self.assertEqual(measure.check_one("is_empty", str(self.empty), ""), (True, "空文件"))
        ok, _ = measure.check_one("is_empty", str(self.file), "")
        self.assertFalse(ok)
        ok, _ = measure.check_one("is_empty", str(self.missing), "")
        self.assertFalse(ok)

    def test_contains(self):
        self.assertEqual(measure.check_one("contains", str(self.file), "hello"), (True, "包含目标内容"))
        ok, detail = measure.check_one("contains", str(self.file), "worldx")
        self.assertFalse(ok)
        self.assertIn("未找到", detail)

    def test_not_contains(self):
        self.assertEqual(measure.check_one("not_contains", str(self.file), "worldx"), (True, "未包含目标内容"))
        ok, detail = measure.check_one("not_contains", str(self.file), "hello")
        self.assertFalse(ok)
        self.assertIn("意外包含", detail)

    def test_contains_on_missing_file(self):
        # 异常情况：文件不存在，没法查内容
        ok, detail = measure.check_one("contains", str(self.missing), "x")
        self.assertFalse(ok)
        self.assertIn("文件不存在", detail)

    def test_unknown_kind(self):
        ok, detail = measure.check_one("no_such_kind", str(self.file), "")
        self.assertFalse(ok)
        self.assertIn("未知检查类型", detail)

    def test_git_dirty_clean(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_git_repo(tmp)
            self.assertEqual(measure.check_one("git_dirty", str(repo), ""), (True, "工作区干净"))

    def test_git_dirty_with_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_git_repo(tmp)
            (repo / "new.txt").write_text("x", encoding="utf-8")
            ok, detail = measure.check_one("git_dirty", str(repo), "")
            self.assertFalse(ok)
            self.assertIn("1 处未提交改动", detail)


class TestRunSpec(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.d = Path(self._tmp.name)

    def test_passing_spec_returns_true_and_writes_card(self):
        f = self.d / "ok.txt"
        f.write_text("abc", encoding="utf-8")
        out = self.d / "out"
        spec = {
            "task": "demo",
            "stage": "阶段一",
            "checks": [
                {"kind": "file", "path": str(f), "label": "文件在"},
                {"kind": "contains", "path": str(f), "needle": "abc", "label": "含 abc"},
            ],
        }
        self.assertTrue(measure.run_spec(spec, out))
        cards = list(out.glob("*.json"))
        self.assertEqual(len(cards), 1)
        card = json.loads(cards[0].read_text(encoding="utf-8"))
        self.assertTrue(card["passed"])
        self.assertEqual(card["passed_count"], 2)
        self.assertEqual(card["total"], 2)
        self.assertEqual(card["level"], "L1")

    def test_failing_spec_returns_false(self):
        out = self.d / "out"
        spec = {
            "task": "demo2",
            "checks": [
                {"kind": "file", "path": str(self.d / "ghost.txt"), "label": "缺文件"},
            ],
        }
        self.assertFalse(measure.run_spec(spec, out))
        card = json.loads(next(out.glob("*.json")).read_text(encoding="utf-8"))
        self.assertFalse(card["passed"])
        self.assertEqual(card["passed_count"], 0)

    def test_empty_checks_is_trivially_pass(self):
        # 边界：一条检查都没有
        out = self.d / "out"
        self.assertTrue(measure.run_spec({"task": "empty", "checks": []}, out))
        card = json.loads(next(out.glob("*.json")).read_text(encoding="utf-8"))
        self.assertEqual(card["total"], 0)


class TestSelftest(unittest.TestCase):

    def test_selftest_passes(self):
        self.assertEqual(measure.selftest(), 0)


if __name__ == "__main__":
    unittest.main()
