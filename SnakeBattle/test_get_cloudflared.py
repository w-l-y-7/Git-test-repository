# -*- coding: utf-8 -*-
"""SnakeBattle/get_cloudflared.py 的单元测试。

核心是"文件大小够不够""残留文件要不要续传"这类纯逻辑。
真正的下载（curl、镜像、55MB）全部用替身顶掉，测试不会联网。
"""
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

import get_cloudflared


class TestSizeMb(unittest.TestCase):

    def test_missing_file_is_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(get_cloudflared.size_mb(Path(tmp) / "nope.exe"), 0)

    def test_existing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "a.bin"
            f.write_bytes(b"x" * (2 * 1024 * 1024))
            self.assertAlmostEqual(get_cloudflared.size_mb(f), 2.0, places=3)

    def test_empty_file_is_zero(self):
        # 边界：文件存在但是空的
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "empty.bin"
            f.write_bytes(b"")
            self.assertEqual(get_cloudflared.size_mb(f), 0)


class TestConfig(unittest.TestCase):

    def test_min_size(self):
        self.assertEqual(get_cloudflared.MIN_MB, 40)

    def test_mirrors_count(self):
        self.assertEqual(len(get_cloudflared.MIRRORS), 4)

    def test_last_mirror_is_direct_github(self):
        self.assertTrue(get_cloudflared.MIRRORS[-1].startswith("https://github.com/"))

    def test_target_name(self):
        self.assertIn("cloudflared-windows-amd64.exe", get_cloudflared.TARGET)


def _fake_result(code):
    return types.SimpleNamespace(returncode=code)


class TestMain(unittest.TestCase):
    """main() 的分支逻辑，subprocess / size_mb 全部替身化。"""

    def test_already_downloaded_skips_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "cloudflared.exe"
            dest.write_bytes(b"x")
            with mock.patch.object(get_cloudflared, "DEST", dest), \
                    mock.patch.object(get_cloudflared, "size_mb", return_value=50), \
                    mock.patch.object(get_cloudflared.subprocess, "run") as run:
                code = get_cloudflared.main()
        self.assertEqual(code, 0)
        run.assert_not_called()          # 已下好，不该再去下载

    def test_successful_download(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "cloudflared.exe"     # 不存在 → 走下载分支
            with mock.patch.object(get_cloudflared, "DEST", dest), \
                    mock.patch.object(get_cloudflared, "size_mb", return_value=50), \
                    mock.patch.object(get_cloudflared.subprocess, "run", return_value=_fake_result(0)) as run:
                code = get_cloudflared.main()
        self.assertEqual(code, 0)
        self.assertEqual(run.call_count, 1)          # 第一个镜像就成了

    def test_resume_from_partial_file(self):
        # 边界：DEST 已存在但太小 → 提示续传，然后继续尝试下载
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "cloudflared.exe"
            dest.write_bytes(b"x")
            with mock.patch.object(get_cloudflared, "DEST", dest), \
                    mock.patch.object(get_cloudflared, "size_mb", return_value=50), \
                    mock.patch.object(get_cloudflared.subprocess, "run", return_value=_fake_result(0)):
                code = get_cloudflared.main()
        self.assertEqual(code, 0)

    def test_all_mirrors_fail(self):
        # 异常情况：每个镜像都返回失败码，最终应返回 1，并且每个镜像都试过
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "cloudflared.exe"
            with mock.patch.object(get_cloudflared, "DEST", dest), \
                    mock.patch.object(get_cloudflared, "size_mb", return_value=0), \
                    mock.patch.object(get_cloudflared.subprocess, "run", return_value=_fake_result(1)) as run:
                code = get_cloudflared.main()
        self.assertEqual(code, 1)
        self.assertEqual(run.call_count, len(get_cloudflared.MIRRORS))

    def test_download_reported_ok_but_file_too_small(self):
        # 边界：curl 说成功，但文件大小仍不达标（没下全）→ 应继续换源
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp) / "cloudflared.exe"
            with mock.patch.object(get_cloudflared, "DEST", dest), \
                    mock.patch.object(get_cloudflared, "size_mb", return_value=5), \
                    mock.patch.object(get_cloudflared.subprocess, "run", return_value=_fake_result(0)) as run:
                code = get_cloudflared.main()
        self.assertEqual(code, 1)
        self.assertEqual(run.call_count, len(get_cloudflared.MIRRORS))


if __name__ == "__main__":
    unittest.main()
