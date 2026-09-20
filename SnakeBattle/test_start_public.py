# -*- coding: utf-8 -*-
"""SnakeBattle/start_public.py 的单元测试。

网络、子进程、浏览器一律用替身顶掉，测试过程中不会真的联网、
不会真的启动服务器、也不会真的开浏览器。
"""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import start_public


class TestUrlPattern(unittest.TestCase):
    """公网网址的正则提取（从 cloudflared 的日志里捞网址）。"""

    def test_extracts_typical_url(self):
        line = "2024-01-01 INF +--------------------+ |  https://bold-river-7a3c.trycloudflare.com  |"
        m = start_public.URL_PATTERN.search(line)
        self.assertIsNotNone(m)
        self.assertEqual(m.group(0), "https://bold-river-7a3c.trycloudflare.com")

    def test_extracts_digits_and_dashes(self):
        line = "url is https://a1-b2-c3.trycloudflare.com\n"
        self.assertEqual(
            start_public.URL_PATTERN.search(line).group(0),
            "https://a1-b2-c3.trycloudflare.com",
        )

    def test_no_match_for_unrelated_line(self):
        self.assertIsNone(start_public.URL_PATTERN.search("just a log line, no link"))

    def test_no_match_for_other_domain(self):
        self.assertIsNone(
            start_public.URL_PATTERN.search("https://example.com/tunnel")
        )

    def test_uppercase_not_matched(self):
        # 边界：cloudflared 给的都是小写子域名
        self.assertIsNone(
            start_public.URL_PATTERN.search("https://ABC.trycloudflare.com")
        )


class TestWaitReachable(unittest.TestCase):
    """反复探测网址是否真的能打开。"""

    def test_returns_true_when_200(self):
        class _Resp:
            status = 200

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

        with mock.patch.object(start_public.urllib.request, "urlopen", return_value=_Resp()):
            self.assertTrue(start_public.wait_reachable("https://x.trycloudflare.com", timeout=5))

    def test_gives_up_when_timeout_zero(self):
        # 边界：超时设成 0，一次都不该试，直接返回 False
        with mock.patch.object(start_public.urllib.request, "urlopen") as m:
            self.assertFalse(start_public.wait_reachable("https://x.trycloudflare.com", timeout=0))
        m.assert_not_called()

    def test_returns_false_when_always_erroring(self):
        # 异常情况：每次都连不上，等到超时就放弃（用假时钟避免真的等 45 秒）
        times = iter([0, 1, 2, 100])
        calls = {"n": 0}

        def fake_time():
            calls["n"] += 1
            return next(times)

        with mock.patch.object(start_public.urllib.request, "urlopen", side_effect=OSError("boom")), \
                mock.patch.object(start_public.time, "time", side_effect=fake_time), \
                mock.patch.object(start_public.time, "sleep", lambda *_: None):
            self.assertFalse(start_public.wait_reachable("https://x.trycloudflare.com", timeout=45))


class TestClipboard(unittest.TestCase):
    """复制到剪贴板。"""

    def test_success(self):
        with mock.patch.object(start_public.subprocess, "run", return_value=object()):
            self.assertTrue(start_public.copy_to_clipboard("hello"))

    def test_failure_is_swallowed(self):
        # 异常情况：剪贴板命令失败，应该返回 False 而不是崩掉
        with mock.patch.object(start_public.subprocess, "run", side_effect=OSError("no clip")):
            self.assertFalse(start_public.copy_to_clipboard("hello"))


class _FakeProc:
    """假进程：stderr 给几行日志，terminate 只做记录。"""

    def __init__(self, lines):
        self.stderr = iter(lines)
        self.terminated = False

    def terminate(self):
        self.terminated = True


class TestStartTunnel(unittest.TestCase):
    """建立隧道（子进程与网络全部替身化）。"""

    def test_success_returns_process_and_url(self):
        proc = _FakeProc([
            "INF Requesting new quick Tunnel",
            "INF |  https://happy-cat-99.trycloudflare.com  |",
        ])
        with mock.patch.object(start_public.subprocess, "Popen", return_value=proc), \
                mock.patch.object(start_public, "wait_reachable", return_value=True):
            tunnel, url = start_public.start_tunnel()
        self.assertIs(tunnel, proc)
        self.assertEqual(url, "https://happy-cat-99.trycloudflare.com")
        self.assertFalse(proc.terminated)

    def test_no_url_in_output_gives_up(self):
        # 边界：日志里始终没有网址，应放弃并杀掉进程
        proc = _FakeProc(["INF starting", "INF no link here"])
        with mock.patch.object(start_public.subprocess, "Popen", return_value=proc), \
                mock.patch.object(start_public, "wait_reachable", return_value=True):
            tunnel, url = start_public.start_tunnel()
        self.assertIsNone(tunnel)
        self.assertIsNone(url)
        self.assertTrue(proc.terminated)

    def test_url_found_but_not_reachable_gives_up(self):
        # 有网址但外网访问不到（死隧道），也应放弃换一条
        proc = _FakeProc(["INF | https://dead-node-1.trycloudflare.com |"])
        with mock.patch.object(start_public.subprocess, "Popen", return_value=proc), \
                mock.patch.object(start_public, "wait_reachable", return_value=False):
            tunnel, url = start_public.start_tunnel()
        self.assertIsNone(tunnel)
        self.assertIsNone(url)
        self.assertTrue(proc.terminated)


class TestConstants(unittest.TestCase):

    def test_port(self):
        self.assertEqual(start_public.PORT, 8000)

    def test_max_tries(self):
        self.assertEqual(start_public.MAX_TRIES, 5)


class TestMainMissingTool(unittest.TestCase):
    """缺少 cloudflared.exe 时，应直接提示并返回错误码，不起服务、不联网。"""

    def test_missing_cloudflared_returns_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(start_public, "BASE", Path(tmp)), \
                    mock.patch.object(start_public.subprocess, "Popen") as popen:
                code = start_public.main()
        self.assertEqual(code, 1)
        popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
