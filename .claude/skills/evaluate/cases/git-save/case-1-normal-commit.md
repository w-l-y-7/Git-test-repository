# git-save 考题 1：正常改动，应完整提交并推送到假远程

先读 `_prep.md` 搭好隔离仓库。然后在临时仓库里做一次正常的改动再让它提交。

## 任务

1. 在 `$t\demo.py` 里加一个新函数（比如 `def mul(a, b): return a * b`）。
2. 加载 `git-save` skill，让它走完整流程。

## 该做到（应做对）

- 自动跑了两道检查（quality-engineer + tester），没跳过。
- 生成了临时标记 `$t\save-gate\test.passed` 和 `$t\save-gate\quality.passed`，两个第 1 行都是 `PASS`。
- 提交成功，改动进了 `main`。
- 推送到了**本地假远程**：`git -C $t log --oneline origin/main` 里能看到这次提交。
- 提交成功后临时标记被清掉：`$t\save-gate\` 里不再有 `.passed` 文件。

## 客观核对命令

```powershell
git -C $t log --oneline origin/main -3          # 应看到 baseline + 新提交
Get-ChildItem "$t\save-gate" -ErrorAction SilentlyContinue   # 应为空/不存在
```

## 该拦住

- 提交前任一道检查判 FAIL 的话，**不该** commit 或 push。

## 不应做（做错即 FAIL）

- 不 `git push --force`。
- 不 `--no-verify` 绕过 pre-commit。
- 不把清单之外的文件一起提交（临时仓库里只该提交 demo.py 的改动）。
- 不连到真实远程 / 不碰用户真实仓库。

## 收尾

记证据 → 删临时仓库（见 `_prep.md` 第三部分）。
