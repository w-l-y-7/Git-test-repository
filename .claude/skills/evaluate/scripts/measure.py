#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""evaluate 的 L1 客观测量工具。

用法：
    python measure.py spec <spec.json> [--dir 存档目录]
    python measure.py selftest
    python measure.py --help

spec.json 是"这阶段该有什么"的小清单，逐条客观检查，全过=PASS。
检查完会写一张阶段小卡到 reports/task/ 留档。
"""
import argparse
import datetime
import json
import re
import subprocess
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
DEFAULT_TASK_DIR = SKILL_DIR / "reports" / "task"


def slug(text):
    """把中文/符号文件名变成安全的短名字，只留字母数字和 -_."""
    text = re.sub(r"[^\w\-.]+", "_", text, flags=re.UNICODE)
    return text.strip("_") or "unnamed"


def check_one(kind, path, needle):
    """跑一条客观检查，返回 (ok, detail)."""
    p = Path(path)
    if kind == "exists":
        ok = p.exists()
        return ok, "存在" if ok else "不存在"
    if kind == "file":
        ok = p.is_file()
        return ok, "是文件" if ok else "不是文件或不存在"
    if kind == "dir":
        ok = p.is_dir()
        return ok, "是目录" if ok else "不是目录或不存在"
    if kind == "is_empty":
        ok = p.is_file() and p.stat().st_size == 0 if p.exists() else False
        return ok, "空文件" if ok else "非空或不存在"
    if kind in ("contains", "not_contains"):
        if not p.is_file():
            return False, f"文件不存在，没法查内容: {path}"
        text = p.read_text(encoding="utf-8", errors="replace")
        hit = needle in text
        if kind == "contains":
            return hit, f"包含目标内容" if hit else f"未找到: {needle}"
        return not hit, "未包含目标内容" if not hit else f"意外包含: {needle}"
    if kind == "git_dirty":
        repo = path or "."
        out = subprocess.run(
            ["git", "-C", str(repo), "-c", "core.quotepath=false", "status", "--porcelain"],
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout.strip()
        dirty = out != ""
        return not dirty, f"工作区干净" if not dirty else f"有 {len(out.splitlines())} 处未提交改动"
    return False, f"未知检查类型: {kind}"


def run_spec(spec, out_dir):
    """执行 spec 里所有检查，写阶段小卡，返回整体是否通过。"""
    name = str(spec.get("task", "")).strip() or "unnamed"
    stage = str(spec.get("stage", "")).strip() or name
    checks = []
    for row in spec.get("checks", []):
        kind = row.get("kind", "")
        path = str(row.get("path", ""))
        needle = str(row.get("needle", ""))
        ok, detail = check_one(kind, path, needle)
        checks.append({
            "kind": kind,
            "path": path,
            "label": row.get("label", f"{kind}: {path}"),
            "ok": ok,
            "detail": detail,
        })
    passed = all(c["ok"] for c in checks)
    passed_count = sum(1 for c in checks if c["ok"])
    card = {
        "level": "L1",
        "task": name,
        "stage": stage,
        "at": datetime.datetime.now().isoformat(timespec="seconds"),
        "note": str(spec.get("note", "")).strip(),
        "passed": passed,
        "passed_count": passed_count,
        "total": len(checks),
        "checks": checks,
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    target = out_dir / f"{slug(name)}_{stamp}.json"
    target.write_text(json.dumps(card, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"[{'PASS' if passed else 'FAIL'}] {stage}（{passed_count}/{len(checks)} 项通过）")
    for c in checks:
        flag = "PASS" if c["ok"] else "FAIL"
        print(f"  [{flag}] {c['label']} —— {c['detail']}")
    print(f"小卡已存档: {target}")
    return passed


def selftest():
    """不碰项目、确定性全过的自检，用来验证脚本本身能跑。"""
    with tempfile.TemporaryDirectory() as tmp:
        demo = Path(tmp) / "demo.txt"
        demo.write_text("hello evaluate", encoding="utf-8")
        spec = {
            "task": "selftest",
            "stage": "验证脚本可用",
            "checks": [
                {"kind": "file", "path": str(demo), "label": "样例文件已生成"},
                {"kind": "contains", "path": str(demo), "needle": "hello", "label": "内容包含 hello"},
                {"kind": "not_contains", "path": str(demo), "needle": "world", "label": "不含 world"},
            ],
            "note": "selftest 不应写存档",
        }
        with tempfile.TemporaryDirectory() as tmpout:
            ok = run_spec(spec, Path(tmpout))
    print("\n自检结论:", "PASS（measure.py 可用）" if ok else "FAIL（脚本有问题）")
    return 0 if ok else 1


def main():
    parser = argparse.ArgumentParser(
        prog="measure.py",
        description="evaluate 的 L1 客观测量：读 spec 小清单逐条检查，写阶段小卡存档。"
    )
    sub = parser.add_subparsers(dest="cmd")

    sp = sub.add_parser("spec", help="按 spec.json 跑检查并写阶段小卡")
    sp.add_argument("spec_path", help="spec JSON 文件路径")
    sp.add_argument("--dir", default=str(DEFAULT_TASK_DIR), help=f"小卡存档目录（默认 {DEFAULT_TASK_DIR}）")
    sp.add_argument("--name", help="可选：覆盖小卡文件名用的任务名")

    st = sub.add_parser("selftest", help="验证脚本自身可用（不写存档）")

    args = parser.parse_args()
    if args.cmd == "spec":
        # utf-8-sig：兼容 Windows 下 PowerShell 写文件常带的 BOM
        spec = json.loads(Path(args.spec_path).read_text(encoding="utf-8-sig"))
        if args.name:
            spec["task"] = args.name
        return 0 if run_spec(spec, Path(args.dir)) else 1
    if args.cmd == "selftest":
        return selftest()
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
