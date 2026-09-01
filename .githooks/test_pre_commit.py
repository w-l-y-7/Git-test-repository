# -*- coding: utf-8 -*-
"""单元测试：.githooks/pre-commit.py（提交质量门禁逻辑）。

注意：被测文件 pre-commit.py 的名字带连字符，不能直接 import，
所以用 importlib.util 按文件路径加载；并用 mock 挡住它内部的
git 子进程调用和 sys.exit，让顶层检查流程在可控环境下执行。
"""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

MODULE_PATH = Path(__file__).parent / "pre-commit.py"

TS = "2026-09-01T10:00:00"
BASE = 1000000000.0
BEFORE = BASE - 100.0
AFTER = BASE + 100.0


class FakeStream:
    """假输出流，接住脚本打印到 stdout/stderr 的内容。"""

    def __init__(self):
        self.lines = []

    def reconfigure(self, **kwargs):
        pass

    def write(self, s):
        self.lines.append(s)

    def flush(self):
        pass

    def text(self):
        return "".join(self.lines)


def load_module(root, gitdir, staged_bytes):
    """在 mock 环境下执行 pre-commit.py 的顶层流程，返回 (module, ctx)。"""
    ctx = {"exit_codes": [], "stderr": FakeStream(), "stdout": FakeStream()}

    def fake_exit(code=None):
        ctx["exit_codes"].append(code)
        raise SystemExit(code)

    def fake_check_output(cmd, *args, **kwargs):
        if cmd[:2] == ["git", "rev-parse"]:
            if cmd[2] == "--show-toplevel":
                return str(root).encode("utf-8")
            if cmd[2] == "--git-dir":
                return str(gitdir).encode("utf-8")
        if cmd[1:3] == ["-c", "core.quotepath=false"]:
            return staged_bytes
        raise AssertionError("unexpected git command: %r" % (cmd,))

    with mock.patch("sys.exit", new=fake_exit), \
         mock.patch("subprocess.check_output", new=fake_check_output), \
         mock.patch("sys.stderr", ctx["stderr"]), \
         mock.patch("sys.stdout", ctx["stdout"]):
        spec = importlib.util.spec_from_file_location("pre_commit", str(MODULE_PATH))
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except SystemExit:
            pass
    return module, ctx


class TestPreCommit(unittest.TestCase):

    def build_scenario(self, staged_paths, markers, staged_mtime=None,
                       marker_mtime=None, merge_head=False):
        """搭一个临时仓库：save-gate 标记、待提交文件，然后跑一遍门禁流程。"""
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        gitdir = root / ".git"
        gitdir.mkdir(parents=True, exist_ok=True)
        if merge_head:
            (gitdir / "MERGE_HEAD").write_text("x", encoding="utf-8")
        gate = root / "save-gate"
        gate.mkdir(parents=True, exist_ok=True)
        for key, lines in markers.items():
            p = gate / ("%s.passed" % key)
            if lines is None:
                if p.exists():
                    p.unlink()
            else:
                p.write_text("\n".join(lines) + "\n", encoding="utf-8")
                if marker_mtime is not None:
                    os.utime(p, (marker_mtime, marker_mtime))
        staged_bytes = b"".join(s.encode("utf-8") + b"\0" for s in staged_paths)
        for s in staged_paths:
            f = root / s
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("content", encoding="utf-8")
            if staged_mtime is not None:
                os.utime(f, (staged_mtime, staged_mtime))
        module, ctx = load_module(root, gitdir, staged_bytes)
        return module, ctx

    def get_module(self):
        """加载模块（顶层走一遍"没有 .py 待提交 → 放行"的干净路径），拿纯函数来测。"""
        markers = {"test": ["PASS", TS, "app.py"], "quality": ["PASS", TS, "app.py"]}
        module, _ = self.build_scenario(["README.txt"], markers)
        return module

    # ---------- norm：路径归一化 ----------

    def test_norm_backslash(self):
        m = self.get_module()
        self.assertEqual(m.norm("a\\b\\c.py"), "a/b/c.py")

    def test_norm_forward_slash_unchanged(self):
        m = self.get_module()
        self.assertEqual(m.norm("a/b/c.py"), "a/b/c.py")

    def test_norm_empty(self):
        m = self.get_module()
        self.assertEqual(m.norm(""), "")

    def test_norm_mixed_separators(self):
        m = self.get_module()
        self.assertEqual(m.norm("a\\b/c\\d.py"), "a/b/c/d.py")

    # ---------- load_marker：读通过标记 ----------

    def test_load_marker_missing_returns_none(self):
        m = self.get_module()
        self.assertIsNone(m.load_marker(Path("no/such/marker.passed")))

    def test_load_marker_normal(self):
        m = self.get_module()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.passed"
            p.write_text("PASS\n%s\napp.py\n" % TS, encoding="utf-8")
            self.assertEqual(m.load_marker(p), ["PASS", TS, "app.py"])

    def test_load_marker_strips_bom(self):
        m = self.get_module()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.passed"
            p.write_text("﻿PASS\n%s\napp.py\n" % TS, encoding="utf-8")
            self.assertEqual(m.load_marker(p), ["PASS", TS, "app.py"])

    def test_load_marker_keeps_middle_empty_line(self):
        m = self.get_module()
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.passed"
            p.write_text("PASS\n%s\n\napp.py\n" % TS, encoding="utf-8")
            self.assertEqual(m.load_marker(p), ["PASS", TS, "", "app.py"])

    # ---------- git：跑 git 命令 ----------

    def test_git_decodes_utf8_and_strips(self):
        m = self.get_module()
        with mock.patch("subprocess.check_output",
                        return_value=b"\xe4\xbb\x93\xe5\xba\x93\n") as co:
            self.assertEqual(m.git("rev-parse", "--show-toplevel"), "仓库")
            co.assert_called_once_with(["git", "rev-parse", "--show-toplevel"])

    # ---------- block：拦下提交 ----------

    def test_block_exits_1_and_prints_reason(self):
        m = self.get_module()
        ferr = FakeStream()
        with mock.patch("sys.exit") as fake_exit, mock.patch("sys.stderr", ferr):
            m.block("某文件没被检查")
        fake_exit.assert_called_once_with(1)
        self.assertIn("某文件没被检查", ferr.text())
        self.assertIn("请先运行 git-save", ferr.text())

    # ---------- 顶层检查流程 ----------

    def test_flow_no_py_staged_passes(self):
        markers = {"test": ["PASS", TS, "app.py"], "quality": ["PASS", TS, "app.py"]}
        _, ctx = self.build_scenario(["README.txt"], markers)
        self.assertEqual(ctx["exit_codes"], [0])

    def test_flow_missing_test_marker_blocks(self):
        markers = {"test": None, "quality": ["PASS", TS, "app.py"]}
        _, ctx = self.build_scenario(["app.py"], markers)
        self.assertEqual(ctx["exit_codes"], [1])
        self.assertIn("save-gate/test.passed 不存在", ctx["stderr"].text())

    def test_flow_marker_not_pass_blocks(self):
        markers = {"test": ["FAIL", TS, "app.py"], "quality": ["PASS", TS, "app.py"]}
        _, ctx = self.build_scenario(["app.py"], markers)
        self.assertEqual(ctx["exit_codes"], [1])
        self.assertIn("标记内容不是 PASS", ctx["stderr"].text())

    def test_flow_uncovered_py_blocks(self):
        markers = {"test": ["PASS", TS, "other.py"], "quality": ["PASS", TS, "other.py"]}
        _, ctx = self.build_scenario(["app.py"], markers)
        self.assertEqual(ctx["exit_codes"], [1])
        self.assertIn("既没被单元测试也没被质量审查覆盖", ctx["stderr"].text())

    def test_flow_modified_after_check_blocks(self):
        markers = {"test": ["PASS", TS, "app.py"], "quality": ["PASS", TS, "app.py"]}
        _, ctx = self.build_scenario(["app.py"], markers,
                                     staged_mtime=AFTER, marker_mtime=BASE)
        self.assertEqual(ctx["exit_codes"], [1])
        self.assertIn("在单元测试之后又被改动过", ctx["stderr"].text())

    def test_flow_covered_and_clean_passes(self):
        markers = {"test": ["PASS", TS, "app.py"], "quality": ["PASS", TS, "app.py"]}
        _, ctx = self.build_scenario(["app.py"], markers,
                                     staged_mtime=BEFORE, marker_mtime=BASE)
        self.assertEqual(ctx["exit_codes"], [0])
        self.assertIn("放行", ctx["stdout"].text())

    def test_flow_merge_commit_skips_gate(self):
        markers = {"test": None, "quality": None}
        _, ctx = self.build_scenario(["app.py"], markers, merge_head=True)
        self.assertEqual(ctx["exit_codes"], [0])


if __name__ == "__main__":
    unittest.main()
