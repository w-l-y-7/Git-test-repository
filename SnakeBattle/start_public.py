"""
一条命令启动两样东西：
  1. 本机的游戏服务器
  2. Cloudflare 临时隧道，把本机服务器暴露到公网

隧道连上后会把公网网址打印出来，并自动复制到剪贴板。
按 Ctrl+C 就能一起关掉。

注意：很多校园网/公司网会封掉 cloudflared 用的 7844 端口，
所以隧道时好时坏。连不上会自动换一条重试。
"""

import re
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser
from pathlib import Path

BASE = Path(__file__).parent
PORT = 8000
URL_PATTERN = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")
MAX_TRIES = 5


def wait_reachable(url, timeout=45):
    """反复访问这个网址，直到它真的能打开（或等够了放弃）。"""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=8) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(3)
    return False


def copy_to_clipboard(text):
    """把文字塞进剪贴板，失败就算了。"""
    try:
        subprocess.run("clip", input=text, text=True, shell=True, check=True)
        return True
    except Exception:
        return False


def start_tunnel():
    """起一个 cloudflared，等它真的能从外网访问到。成功返回 (进程, 网址)，失败返回 (None, None)。"""
    # 用 TCP（http2）而不是默认的 QUIC：很多校园网/公司网封了 QUIC 用的 UDP 7844，
    # 封了就会一直连不上。TCP 走 443，基本上哪都能通。
    tunnel = subprocess.Popen(
        [str(BASE / "cloudflared.exe"), "tunnel", "--url", f"http://127.0.0.1:{PORT}",
         "--protocol", "http2"],
        cwd=BASE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    # cloudflared 把网址打在错误输出里。必须一直读、不能读完就走：
    # 管道缓冲区塞满后 cloudflared 会卡在写日志上，隧道就永远建不起来。
    found_url = {}
    ready = threading.Event()

    def drain_stderr():
        for line in tunnel.stderr:
            if "url" not in found_url:
                m = URL_PATTERN.search(line)
                if m:
                    found_url["url"] = m.group(0)
                    ready.set()
        ready.set()          # 进程结束了也别让主线程干等

    threading.Thread(target=drain_stderr, daemon=True).start()

    if not ready.wait(timeout=60) or not found_url.get("url"):
        tunnel.terminate()
        return None, None

    url = found_url["url"]
    if not wait_reachable(url):
        tunnel.terminate()          # 这条是死的，扔掉换一条
        return None, None
    return tunnel, url


def main():
    if not (BASE / "cloudflared.exe").exists():
        print()
        print("  找不到 cloudflared.exe。")
        print("  请先双击「下载隧道工具.bat」把它下载下来。")
        print()
        return 1

    print()
    print("  正在启动游戏服务器...")
    server = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "server:app",
         "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=BASE,
    )

    print("  正在建立公网隧道...")
    tunnel, public_url = None, None
    for attempt in range(1, MAX_TRIES + 1):
        if attempt > 1:
            print(f"  这条没通，换一条再试（第 {attempt}/{MAX_TRIES} 次）...")
        tunnel, public_url = start_tunnel()
        if public_url:
            break

    if not public_url:
        print()
        print("  试了 %d 次都没连上 Cloudflare。" % MAX_TRIES)
        print("  多半是这个网络把 cloudflared 用的端口封了（校园网/公司网常见）。")
        print("  换个网络试试（比如手机热点），或者过一会儿再来。")
        print()
        server.terminate()
        return 1

    copied = copy_to_clipboard(public_url)

    print()
    print("  " + "=" * 58)
    print("   公网网址（发给朋友，他打开就能玩）：")
    print()
    print("     " + public_url)
    print()
    print("   已经复制到剪贴板了，直接粘贴发给朋友就行。"
          if copied else "   请手动复制上面这个网址发给朋友。")
    print("  " + "=" * 58)
    print()
    print("  你现在可以：")
    print("    - 自己在浏览器里建房，再把房间号告诉朋友")
    print("    - 朋友打开网址后输房间号加入")
    print()
    print("  按 Ctrl+C 关闭（关掉后网址就失效了）")
    print()

    webbrowser.open(f"http://127.0.0.1:{PORT}")

    # 谁先退出就一起收拾掉
    def watch():
        server.wait()
        tunnel.terminate()

    threading.Thread(target=watch, daemon=True).start()

    try:
        tunnel.wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.terminate()
        tunnel.terminate()
        print()
        print("  已关闭。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
