# -*- coding: utf-8 -*-
"""system_check.py 的单元测试。

测纯逻辑：git 调用封装、仓库根目录探测、文件"年龄"计算、
信息收集 collect()，以及把收集结果拼成人看的报告 human_report()。
用临时目录/临时仓库，不碰真实仓库内容，不联网。
"""
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

import system_check


def _make_git_repo(tmp):
    subprocess.run(["git", "init", "-q", tmp], capture_output=True, text=True)
    return Path(tmp)


class TestGitWrapper(unittest.TestCase):

    def test_rev_parse_in_temp_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_git_repo(tmp)
            out, err = system_check.git(repo, "rev-parse", "--is-inside-work-tree")
            self.assertEqual(out, "true")

    def test_clean_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = _make_git_repo(tmp)
            out, _ = system_check.git(repo, "status", "--porcelain")
            self.assertEqual(out, "")


class TestRepoRoot(unittest.TestCase):

    def test_hint_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(system_check.repo_root(tmp), Path(tmp).resolve())

    def test_detected_from_git(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = str(Path(tmp).resolve())
            with mock.patch.object(system_check, "git", return_value=(out, "")):
                self.assertEqual(system_check.repo_root(None), Path(tmp).resolve())

    def test_falls_back_to_cwd(self):
        # 边界：git 探测不到时退回到当前目录
        with mock.patch.object(system_check, "git", return_value=("", "boom")):
            self.assertEqual(system_check.repo_root(None), Path.cwd().resolve())


class TestAgeMinutes(unittest.TestCase):

    def test_three_minutes_old(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "x.txt"
            f.write_text("x", encoding="utf-8")
            old = time.time() - 180
            os.utime(f, (old, old))
            self.assertEqual(system_check.age_minutes(f), 3)

    def test_fresh_file_is_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "y.txt"
            f.write_text("y", encoding="utf-8")
            self.assertEqual(system_check.age_minutes(f), 0)


class TestCollect(unittest.TestCase):

    def test_collect_with_gitignore_and_save_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_git_repo(tmp)
            (root / ".gitignore").write_text(
                system_check.GITIGNORE_NEEDED + "\n", encoding="utf-8"
            )
            sg = root / "save-gate"
            sg.mkdir()
            (sg / "test.passed").write_text("PASS\n", encoding="utf-8")

            s = system_check.collect(root)

            self.assertTrue(s["gitignore_exists"])
            self.assertTrue(s["gitignore_has_reports_rule"])
            self.assertTrue(s["save_gate_exists"])
            self.assertIn("test.passed", s["save_gate"])
            self.assertIsInstance(s["save_gate"]["test.passed"]["age_minutes"], int)
            self.assertIn("checked_at", s)
            self.assertEqual(s["repo"], str(root))

    def test_collect_without_gitignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            s = system_check.collect(root)
            self.assertFalse(s["gitignore_exists"])
            self.assertFalse(s["gitignore_has_reports_rule"])
            self.assertFalse(s["save_gate_exists"])
            self.assertEqual(s["save_gate"], {})

    def test_collect_reports_dirty_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_git_repo(tmp)
            (root / "stray.py").write_text("x", encoding="utf-8")
            s = system_check.collect(root)
            self.assertTrue(any("stray.py" in line for line in s["git_dirty"]))


def _base_state(**over):
    s = {
        "repo": ".",
        "checked_at": "2026-01-01T00:00:00",
        "git_dirty": [],
        "gitignore_exists": True,
        "gitignore_has_reports_rule": True,
        "save_gate": {},
        "save_gate_exists": False,
        "task_cards_count": 3,
        "system_reports_count": 1,
        "measure_script_ok": True,
    }
    s.update(over)
    return s


class TestHumanReport(unittest.TestCase):

    def test_all_good(self):
        out = system_check.human_report(_base_state())
        self.assertIn("[PASS] 工作区干净", out)
        self.assertIn("[PASS] .gitignore 已忽略 evaluate", out)
        self.assertIn("[PASS] 没有 save-gate 残留标记", out)
        self.assertIn("[PASS] L1 阶段小卡现有 3 张", out)
        self.assertIn("[PASS] measure.py 脚本自身可运行", out)

    def test_dirty_only_evaluate_reports(self):
        out = system_check.human_report(
            _base_state(git_dirty=[".claude/skills/evaluate/reports/x.json"])
        )
        self.assertIn("[WARN] 工作区不干净", out)
        self.assertNotIn("其中有不属于 evaluate 存档的改动", out)

    def test_dirty_with_foreign_files_warns_extra(self):
        out = system_check.human_report(_base_state(git_dirty=["some_code.py"]))
        self.assertIn("其中有不属于 evaluate 存档的改动", out)

    def test_missing_gitignore_is_fail(self):
        out = system_check.human_report(_base_state(gitignore_exists=False))
        self.assertIn("[FAIL] .gitignore 不存在", out)

    def test_gitignore_missing_rule_is_fail(self):
        out = system_check.human_report(
            _base_state(gitignore_exists=True, gitignore_has_reports_rule=False)
        )
        self.assertIn("[FAIL] .gitignore 漏了", out)

    def test_stale_save_gate_warns(self):
        out = system_check.human_report(
            _base_state(save_gate={"test.passed": {"age_minutes": 42}})
        )
        self.assertIn("[WARN] save-gate 标记有残留且过期", out)

    def test_fresh_save_gate_passes(self):
        out = system_check.human_report(
            _base_state(save_gate={"test.passed": {"age_minutes": 2}})
        )
        self.assertIn("[PASS] save-gate 标记存在且新鲜", out)

    def test_many_task_cards_warns(self):
        out = system_check.human_report(_base_state(task_cards_count=250))
        self.assertIn("[WARN] L1 阶段小卡已攒 250 张", out)

    def test_measure_script_broken_is_fail(self):
        out = system_check.human_report(_base_state(measure_script_ok=False))
        self.assertIn("[FAIL] measure.py 跑不起来", out)


class TestMeasureScriptWiring(unittest.TestCase):
    """确认体检的"测 measure.py 能不能跑"确实指向 measure.py，而不是测自己。"""

    def test_measure_constant_points_to_measure_py(self):
        self.assertEqual(system_check.MEASURE, system_check.HERE / "measure.py")
        self.assertEqual(system_check.MEASURE.name, "measure.py")
        self.assertTrue(system_check.MEASURE.exists())

    def test_collect_runs_measure_py(self):
        # 把 subprocess.run 换成替身，记下每次调用的命令。
        # git 调用第一项是 "git"，体检调用第二项应是 measure.py。
        class _Result:
            def __init__(self):
                self.stdout = ""
                self.stderr = ""
                self.returncode = 0

        seen = []

        def fake_run(cmd, *args, **kwargs):
            seen.append(list(cmd))
            return _Result()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with mock.patch.object(system_check.subprocess, "run", side_effect=fake_run):
                s = system_check.collect(root)

        measure_calls = [
            c for c in seen if len(c) > 1 and str(c[1]).endswith("measure.py")
        ]
        self.assertEqual(len(measure_calls), 1)
        self.assertEqual(
            measure_calls[0], [sys.executable, str(system_check.MEASURE), "--help"]
        )
        self.assertTrue(s["measure_script_ok"])


if __name__ == "__main__":
    unittest.main()
