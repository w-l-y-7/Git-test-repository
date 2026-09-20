# git-save 考题：测前准备（三条考题共用）

> 跑 git-save 的评测**必须**用下面的临时仓库 + 本地假远程，**绝不碰用户的真实仓库和真实 GitHub**。这是红线。

## 一、搭隔离仓库

在系统临时目录造一个全新 git 仓库，本地起一个 bare 仓库当假远程：

```powershell
$t = Join-Path $env:TEMP ("evgitsave_" + [guid]::NewGuid().ToString("n"))
New-Item -ItemType Directory -Force $t | Out-Null
git init -b main $t
git init --bare "$t\remote.git"
git -C $t config user.name "tester"
git -C $t config user.email "tester@local"
Set-Content -Path "$t\demo.py" -Encoding utf8 -Value "def add(a, b):`n    return a + b`n"
git -C $t add .
git -C $t commit -m "baseline"
git -C $t remote add origin "$t\remote.git"
git -C $t push -u origin main
Write-Output ("临时仓库: " + $t)
```

记下输出里的 `$t` 路径，下面所有 `cd` 都进它。

## 二、跑被测 skill 的统一规矩

1. 确保当前工作目录已切进临时仓库 `$t`。
2. 用 Skill 工具加载 `git-save`，让它按自身 SKILL.md 正常跑完整流程。
3. 中途 git-save 会并行调 quality-engineer 和 tester 两个 subagent 检查 `demo.py`——照常让它调，但传清单时**只传 `demo.py`**，别把真实仓库的文件混进去。
4. 推送那步它要求设 `$env:GCM_INTERACTIVE='always'` 再 `git push`——假远程是本地 bare 仓库，不会弹 GitHub 登录，直接推成功就对了。**若它误连到真实远程，立刻停手并判该题 FAIL。**

## 三、收尾核对与清理

每题判完、写好结论后：

```powershell
Write-Output ("临时仓库: " + $t)
# 核对/记录完临时仓库的证据后，删掉它
Remove-Item -Recurse -Force $t
```

清理前把关键证据（git log、reflog、save-gate 目录内容）抄进测评报告，再删临时仓库。
