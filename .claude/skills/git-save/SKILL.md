---
name: git-save
description: 一键提交并推送：先并行检查（单元测试 + 质量审查），都通过后才 git add + git commit + git push 到 GitHub。用户输入 /git-save、或说"提交"、"保存代码"、"存档"、"推送"、"保存到 GitHub" 的时候使用。检查没通过会拦下，不提交。
---

# git-save：先检查，再保存并推送代码

## 这个技能做什么

把当前所有改动自动完成四步：

1. **拿改动清单**
2. **并行跑两道检查**：质量审查（quality-engineer）+ 单元测试（tester）
3. **都通过** → git add + git commit
4. **git push** 推送到 GitHub

检查没通过就拦下来、不提交。这是项目现在唯一的提交方式，也受 pre-commit hook 双重保护。

## 执行步骤

### 第一步：拿改动清单

用两条命令拿所有改动（已改的跟踪文件 + 未跟踪的新文件），去并集：

```powershell
git -c core.quotepath=false diff --name-only
git -c core.quotepath=false ls-files --others --exclude-standard
```

- 合并结果，路径统一成**正斜杠相对路径**（`\` 换成 `/`）。
- 清单是空的 → 告诉用户「没有改动，不用提交」，结束。
- `save-gate/` 下的标记文件被 gitignore 了，不会出现在清单里。

### 第二步：并行跑两个检查 agent

用 Agent 工具，在**同一条消息**里同时调用两个 subagent，把清单传给它们：

- `subagent_type: quality-engineer`，审查清单里所有文件
- `subagent_type: tester`，测试清单里所有文件

它们并行执行。**传清单时明确告诉每个 agent：清单里有这些文件，全部检查，别再问用户。**

### 第三步：确认两道检查都通过

等两个 agent 都完成后，读 `save-gate/test.passed` 和 `save-gate/quality.passed`：

- 两个文件都在、且第 1 行都是 `PASS` → 通过，进入第四步。
- 任一文件缺失或不是 `PASS` → **不提交**，把没通过的那个 agent 的结论告诉用户，说明「改完再重新提交」。

### 第四步：提交并推送

1. 问提交信息（或触发时就带了）——一句话说清"这次做了什么"。
2. `git add -A`
3. `git commit -m "提交信息"`
4. 推送（关键：先设环境变量，否则登录窗口弹不出来）：

```powershell
$env:GCM_INTERACTIVE='always'
git push
```

推送时屏幕会弹 GitHub 登录窗口，提醒用户登录。

### 第五步：推送成功后，清掉旧通行证

提交和推送都成功后，**立刻删除两张旧通行证**（`save-gate/test.passed` 和 `save-gate/quality.passed`）。不然下一轮提交会拿旧标记冒充，跟新改动对不上：

```powershell
Remove-Item -Force save-gate/test.passed, save-gate/quality.passed
```

删不掉或文件不在没关系，下一轮检查会自动重新生成。

## 注意事项

- **如果 `git commit` 被 pre-commit hook 拦截**（报 save-gate/test.passed 或 quality.passed 相关错误），说明标记没对上或过期。**不要用 `--no-verify` 绕过**，把原因告诉用户，重新提交跑一次完整流程。
- **绝对不要用 `git push --force`**，会覆盖远程已有的提交，很危险。
- 如果 `git push` 报错（比如远程有冲突），别自己乱处理，把报错信息告诉用户。
- 推送成功后跟用户说一句「已存好档并推送」，确认完成。
