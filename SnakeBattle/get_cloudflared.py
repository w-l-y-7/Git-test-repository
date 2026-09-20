"""
下载 cloudflared.exe（Cloudflare 的隧道工具，约 55MB）。

国内直连 GitHub 下不动，所以挨个试镜像，哪个通用哪个。
支持断点续传：中途断了再跑一次会接着下。
"""

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).parent
DEST = BASE / "cloudflared.exe"
MIN_MB = 40                      # 小于这个大小说明没下完

TARGET = "github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe"
MIRRORS = [
    f"https://ghproxy.net/https://{TARGET}",
    f"https://ghfast.top/https://{TARGET}",
    f"https://gh.llkk.cc/https://{TARGET}",
    f"https://github.com/{TARGET}",          # 直连，留给网络好的时候
]


def size_mb(path):
    return path.stat().st_size / 1024 / 1024 if path.exists() else 0


def main():
    if DEST.exists() and size_mb(DEST) >= MIN_MB:
        print(f"  已经下好了（{size_mb(DEST):.1f} MB），不用重复下。")
        return 0

    if DEST.exists():
        print(f"  发现上次没下完的文件（{size_mb(DEST):.1f} MB），从断点继续。")

    for mirror in MIRRORS:
        print(f"  尝试：{mirror.split('/')[2]}")
        result = subprocess.run(
            ["curl.exe", "-L", "--fail", "--silent", "--show-error",
             "-C", "-",                       # 断点续传
             "--connect-timeout", "15",
             "-o", str(DEST), mirror],
            cwd=BASE,
        )
        if result.returncode == 0 and size_mb(DEST) >= MIN_MB:
            print()
            print(f"  下载完成（{size_mb(DEST):.1f} MB）")
            print("  现在可以双击「启动公网.bat」了。")
            print()
            return 0
        print(f"    这个源不行，换下一个（当前 {size_mb(DEST):.1f} MB）")

    print()
    print("  所有镜像都失败了。可能是网络问题，过一会儿再试。")
    print(f"  已经下到的部分还留着（{size_mb(DEST):.1f} MB），下次会接着下。")
    print()
    return 1


if __name__ == "__main__":
    sys.exit(main())
