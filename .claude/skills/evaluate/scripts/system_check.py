#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evaluate 的 L3 系统体检：收集"能客观测"的信号，打 PASS/WARN/FAIL。

用法：
    python .claude/skills/evaluate/scripts/system_check.py [--repo 仓库根目录]
    python .claude/skills/evaluate/scripts/system_check.py --help

脚本测得了的归脚本；需要判断的项（漂移/回归/失控的判断）见 SKILL.md 的判断项清单。
结果默认只打印；加 --save 会把 JSON 存到 reports/system/。
"""
import argparse
import datetime
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
REPORTS = SKILL_DIR / "reports"
DEFAULT_SYSTEM_DIR = REPORTS / "system"
GITIGNORE_NEEDED = ".claude/skills/evaluate/reports/"
MEASURE = HERE / "measure.py"


def git(repo, *args):
    # 用 git -C 而不是 cwd= 传中文绝对路径，避免 Windows 下目录名无效的坑；
    # git 输出 UTF-8，显式指定解码，否则在 gbk 环境下会读坏中文路径
    r = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    return r.stdout.strip(), r.stderr.strip()


def repo_root(hint):
    if hint:
        return Path(hint).resolve()
    out, _ = git(".", "rev-parse", "--show-toplevel")
    if out:
        return Path(out).resolve()
    return Path.cwd().resolve()


def age_minutes(path):
    now = datetime.datetime.now().timestamp()
    return int((now - path.stat().st_mtime) // 60)


def collect(root):
    s = {"repo": str(root), "checked_at": datetime.datetime.now().isoformat(timespec="seconds")}

    dirty, _ = git(root, "-c", "core.quotepath=false", "status", "--porcelain")
    s["git_dirty"] = [ln for ln in dirty.splitlines() if ln] if dirty else []

    gi = root / ".gitignore"
    gi_text = gi.read_text(encoding="utf-8", errors="replace") if gi.exists() else ""
    s["gitignore_has_reports_rule"] = GITIGNORE_NEEDED in gi_text
    s["gitignore_exists"] = gi.exists()

    sg = root / "save-gate"
    s["save_gate"] = {}
    if sg.exists():
        for f in sorted(sg.iterdir()):
            if f.is_file():
                s["save_gate"][f.name] = {"age_minutes": age_minutes(f)}
    s["save_gate_exists"] = sg.exists()

    task_dir = REPORTS / "task"
    s["task_cards_count"] = len(list(task_dir.glob("*.json"))) if task_dir.exists() else 0
    sys_dir = REPORTS / "system"
    s["system_reports_count"] = len(list(sys_dir.glob("*.json"))) if sys_dir.exists() else 0

    try:
        r = subprocess.run(
            [sys.executable, str(MEASURE), "--help"],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30,
        )
        s["measure_script_ok"] = r.returncode == 0
    except Exception as e:
        s["measure_script_ok"] = False
        s["measure_script_error"] = str(e)
    return s


def human_report(s):
    lines = []
    flag = lambda ok: "PASS" if ok else "FAIL"
    if s["git_dirty"]:
        lines.append(f"[WARN] 工作区不干净，有 {len(s['git_dirty'])} 处改动：{', '.join(s['git_dirty'][:5])}")
        if any(not p.startswith(".claude/skills/evaluate/reports/") for p in s["git_dirty"]):
            lines.append("       其中有不属于 evaluate 存档的改动，提交前请先确认是不是该提交的。")
    else:
        lines.append("[PASS] 工作区干净，没有未提交改动。")

    if not s["gitignore_exists"]:
        lines.append("[FAIL] .gitignore 不存在（应该有的）。")
    elif s["gitignore_has_reports_rule"]:
        lines.append("[PASS] .gitignore 已忽略 evaluate 的 reports/ 存档目录。")
    else:
        lines.append("[FAIL] .gitignore 漏了 " + GITIGNORE_NEEDED + "，存档会被 git-save 误提交。")

    stale = [
        f"{name}({m['age_minutes']}分钟前)" for name, m in s["save_gate"].items() if m["age_minutes"] > 10
    ]
    if s["save_gate"] and stale:
        lines.append("[WARN] save-gate 标记有残留且过期（可能是上次流程没清干净）：" + ", ".join(stale))
    elif s["save_gate"]:
        fresh = ", ".join(s["save_gate"].keys())
        lines.append(f"[PASS] save-gate 标记存在且新鲜：{fresh}")
    else:
        lines.append("[PASS] 没有 save-gate 残留标记。")

    cards = s["task_cards_count"]
    if cards > 200:
        lines.append(f"[WARN] L1 阶段小卡已攒 {cards} 张，越来越多——报告目录是按期清理，还是做滚动上限？")
    else:
        lines.append(f"[PASS] L1 阶段小卡现有 {cards} 张，数量正常。")
    lines.append(f"[INFO] L3 体检报告累计 {s['system_reports_count']} 份（历史留档）。")

    lines.append("[PASS] measure.py 脚本自身可运行。" if s.get("measure_script_ok") else "[FAIL] measure.py 跑不起来，先检查脚本。")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        prog="system_check.py",
        description="evaluate 的 L3 体检：收集可客观测的系统健康信号，按 PASS/WARN/FAIL 打印。"
    )
    parser.add_argument("--repo", help="要体检的仓库根目录（默认自动探测当前仓库）")
    parser.add_argument("--save", action="store_true", help="把 JSON 结果存到 reports/system/")
    args = parser.parse_args()

    root = repo_root(args.repo)
    s = collect(root)
    print(human_report(s))

    if args.save:
        DEFAULT_SYSTEM_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        target = DEFAULT_SYSTEM_DIR / f"system_{stamp}.json"
        target.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\nJSON 已存档: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
