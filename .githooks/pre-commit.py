#!/usr/bin/env python3
# gitcommit 质量门禁：pre-commit hook 的实际逻辑。
# 检查 save-gate/ 下的两个"通过标记"（test.passed、quality.passed），
# 每个待提交的 .py 文件都必须被检查过、且检查后没再被改动，否则拦下提交。
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def git(*args):
    # git 输出的路径是 UTF-8 字节，必须按 UTF-8 解码，否则中文路径（如"仓库"）会变乱码
    return subprocess.check_output(["git", *args]).decode("utf-8", errors="surrogateescape").strip()


def block(msg):
    print("⛔ 拦截：", msg, file=sys.stderr)
    print("   请先运行 gitcommit：单元测试和质量审查通过后会自动生成标记。", file=sys.stderr)
    sys.exit(1)


def load_marker(path):
    """读标记文件，返回 [PASS, 时间戳, 文件...]；不存在返回 None。"""
    if not path.exists():
        return None
    # utf-8-sig：兼容 Windows 工具写文件时带上的 BOM（﻿PASS 也能识别成 PASS）
    return path.read_text(encoding="utf-8-sig").splitlines()


def norm(path):
    """路径统一为正斜杠相对路径（Windows 路径分隔符 \\ 换成 /）。"""
    return path.replace("\\", "/")


ROOT = Path(git("rev-parse", "--show-toplevel"))
GIT_DIR = Path(git("rev-parse", "--git-dir")).resolve()

# 合并提交收尾阶段不拦，避免合并被误伤
if (GIT_DIR / "MERGE_HEAD").exists():
    sys.exit(0)

GATE = ROOT / "save-gate"
test_marker = load_marker(GATE / "test.passed")
quality_marker = load_marker(GATE / "quality.passed")

if test_marker is None:
    block("还没有单元测试通过的标记（save-gate/test.passed 不存在）")
if quality_marker is None:
    block("还没有质量审查通过的标记（save-gate/quality.passed 不存在）")
if test_marker[0] != "PASS" or quality_marker[0] != "PASS":
    block("标记内容不是 PASS，上次检查可能失败了")

test_files = {norm(f) for f in test_marker[2:] if f}
quality_files = {norm(f) for f in quality_marker[2:] if f}

# 待提交文件：过滤掉删除的（没法检查），并排除标记文件自身
out = subprocess.check_output(
    ["git", "-c", "core.quotepath=false", "diff", "--cached", "--diff-filter=AM", "--name-only", "-z"],
    cwd=ROOT,
)
staged = [norm(f) for f in out.decode("utf-8", errors="surrogateescape").split("\0") if f]
staged_py = [f for f in staged if f.endswith(".py")]

if not staged_py:
    sys.exit(0)  # 没有需要门禁的 Python 文件，放行

test_mtime = (GATE / "test.passed").stat().st_mtime
quality_mtime = (GATE / "quality.passed").stat().st_mtime

for f in staged_py:
    in_test = f in test_files
    in_quality = f in quality_files
    if not in_test and not in_quality:
        block(f"文件 {f} 既没被单元测试也没被质量审查覆盖，请运行 gitcommit 重新检查")
    if in_test:
        if (ROOT / f).stat().st_mtime > test_mtime:
            block(f"文件 {f} 在单元测试之后又被改动过，标记已失效，请运行 gitcommit 重新检查")
    if in_quality:
        if (ROOT / f).stat().st_mtime > quality_mtime:
            block(f"文件 {f} 在质量审查之后又被改动过，标记已失效，请运行 gitcommit 重新检查")

print("✅ 单元测试和质量审查都通过，放行。")
sys.exit(0)
