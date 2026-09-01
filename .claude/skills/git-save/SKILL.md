---
name: git-save
description: 纯 git add + git commit + git push 的底层动作，不做质量检查。当用户明确说"直接提交、跳过检查"（不走质量门禁）时使用，或 gitcommit 代理内部调用。注意：提交可能被 pre-commit 质量门禁 hook 拦截。
---

# git-save：一键保存并推送代码

## 这个技能做什么

把当前仓库的所有改动自动完成三步：

1. **git add** —— 把所有改动加进暂存区
2. **git commit** —— 用一句话存档
3. **git push** —— 推送到 GitHub 远程仓库

适合"改完代码想存个档"的场景，一条命令全搞定。

## 使用前要知道的

- 只推本仓库的 `main` 分支到 GitHub（origin 已配置好）
- `records.db`、`__pycache__/` 等已经在 `.gitignore` 里，不会被误提交，放心

## 执行步骤

### 第一步：定提交信息

- 如果用户输入了提交信息（比如 `/git-save 修复了登录bug`），直接用这句话
- 否则问用户：「这次改动做了什么，用一句话说清楚」
- 提交信息要简短，说"做了什么"，别塞细节

### 第二步：看一眼要提交哪些文件

先运行 `git status` 看看有哪些改动。如果里面混进了不该提交的文件（比如密钥、私人数据），先提醒用户处理，别闷头提交。

### 第三步：git add + commit

```powershell
git add -A
git commit -m "提交信息"
```

`git add -A` 会把新增、修改、删除的文件都加进来，比 `git add .` 更全。

如果 commit 提示"没有要提交的内容"，说明没有改动，告诉用户"代码没变化，不用存档"就行。

### 第四步：推送到 GitHub

关键一步：直接 `git push` 会因为无法弹出登录窗口而失败，**必须先设置环境变量**：

```powershell
$env:GCM_INTERACTIVE='always'
git push
```

推送时屏幕上会弹出 GitHub 登录窗口，提醒用户登录一下。

## 注意事项

- **绝对不要用 `git push --force`**，会覆盖远程已有的提交，很危险
- 如果 `git push` 报错（比如远程有冲突），别自己乱处理，把报错信息告诉用户再想办法
- **如果 `git commit` 被 pre-commit hook 拦截**（报 save-gate/test.passed 或 quality.passed 相关的错误），说明单元测试或质量审查没通过（或标记过期）。**不要用 `--no-verify` 绕过**，把拦截原因转告用户，提示他用 gitcommit 流程重新检查后再提交。
- 推送成功后跟用户说一句「已存好档并推送」，确认完成
