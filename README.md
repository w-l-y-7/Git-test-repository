# 仓库总览

这是一个个人练习仓库，里面装了一堆互不相干的小项目：几个能直接用的桌面 / 网页程序、一个完整的 RAG 问答系统、一套给 Claude Code 用的技能配置，还有几个画数据图的小脚本。

没有统一的主题，也不打算做成一个产品——就是边学边做，做完的项目攒在这里。

## 目录地图

```
Git-test-repository/
├── .claude/                  # Claude Code 的技能和子代理配置
├── .githooks/                # 提交质量门禁（pre-commit 钩子）
├── Academic PPT/             # 学术 PPT 制作工作区（Marp 流程）
├── LangChainRAG/             # 金融知识库问答系统（毕业设计级完整项目）
├── paper writing/            # LaTeX 中文编译测试
├── smartphone app/           # 手机网页版应用
│   └── 日程规划app/           # 打卡 PWA
├── SnakeBattle/              # 联机双人贪吃蛇
├── 每日记账App/               # Windows 桌面记账软件
├── 番茄钟项目/                # Windows 桌面番茄钟
├── save-gate/                # 空目录，门禁标记的存放处（不入库）
├── chart_econ.py             # 画中国 GDP 增速图
├── chart_pop.py              # 画中国人口金字塔
├── fetch_pop.py              # 下载联合国人口数据
├── TODO.md                   # 任务清单，配合 /loop 用
├── .gitignore
└── .gitattributes
```

---

## 各项目说明

### LangChainRAG —— RAG 知识库问答系统

最完整的一个项目。FastAPI + LangChain + Milvus + Vue 3 + MySQL，上传资料后可以像聊天一样提问，回答带引用来源。

- **详细介绍**：见 [LangChainRAG/README.md](LangChainRAG/README.md)，里面有大白话的使用说明、技术栈解释、目录地图、优化方向和上线安全清单。
- **前端说明**：见 [LangChainRAG/frontend/README.md](LangChainRAG/frontend/README.md)（Vue 3 + Vite 默认模板说明）。
- **一键启动**：双击 `LangChainRAG/启动系统.bat`。

### 每日记账App —— 桌面记账软件

Python + Tkinter + SQLite，全本地运行不联网。支持两级花销分类、按月明细、收支汇总、周视图柱状图。

- **使用说明**：见 [每日记账App/README.md](每日记账App/README.md)。
- **需求与协作规则**：见 [每日记账App/claude.md](每日记账App/claude.md)。
- **一键启动**：双击 `每日记账App/启动记账.bat`。
- *账本数据存在 `每日记账App/records.db`，已被 .gitignore 忽略，不会上传。*

### SnakeBattle —— 联机双人贪吃蛇

服务器跑游戏逻辑，浏览器只负责显示和发送按键，所以两台电脑看到的画面永远一致。

| 文件 | 作用 |
|------|------|
| `server.py` | FastAPI + WebSocket 游戏服务器，棋盘逻辑、食物生成、碰撞判定都在这里 |
| `index.html` | 游戏页面（画面 + 键盘操作） |
| `start_public.py` | 一条命令同时启动本机服务器和 Cloudflare 临时隧道，把游戏暴露到公网 |
| `get_cloudflared.py` | 下载云隧道工具，带多个镜像回退和断点续传 |
| `cloudflared.exe` | 隧道工具本体（约 55 MB），由上面那个脚本下载 |
| `安装环境.bat` | 首次使用：建虚拟环境 + 装依赖 |
| `启动游戏.bat` | 局域网对战：启动服务器，并显示本机 IP 给朋友连 |
| `下载隧道工具.bat` | 下载 `cloudflared.exe` |
| `启动公网.bat` | 公网对战：需要先下载好隧道工具 |

首次使用顺序：`安装环境.bat` → `启动游戏.bat`（局域网）或 `下载隧道工具.bat` → `启动公网.bat`（公网）。

### 番茄钟项目

单个 Python 文件 `番茄钟.py`。Tkinter 桌面程序，学习 50 分钟、休息 10 分钟自动循环，到点弹窗加系统提示音。直接 `python 番茄钟.py` 运行。

### smartphone app / 日程规划app

网页版日程打卡应用，用 PWA 技术做成了手机上能添加到桌面的样子。

| 文件 | 作用 |
|------|------|
| `index.html` | 整个应用（页面、样式、逻辑都在一个文件里） |
| `manifest.webmanifest` | PWA 配置：竖屏、独立窗口、应用名和图标 |
| `icon.svg` | 应用图标 |

直接双击 `index.html` 就能在浏览器里打开。

### Academic PPT

Marp 学术 PPT 制作工作区，按七阶段流程走：内容分析 → 初稿 → 审阅 → 导出 → 终稿。

- `inbox/` —— 放待处理的论文原文（目前是一篇金融科技与数字化转型的论文）
- `slides_fintech-digital-transformation/` —— 这份 PPT 的完整工作区
- **详细介绍**：见 [Academic PPT/slides_fintech-digital-transformation/README.md](Academic%20PPT/slides_fintech-digital-transformation/README.md)，里面有项目信息、文件夹说明、制作进度和重新导出的命令。

### paper writing

LaTeX 中文编译测试草稿。`test.tex` 是一份最小的 ctex 文档，用来验证中文能不能正常编译；其余是编译产物。整个文件夹基本已废弃，`.gitignore` 里把 `test.tex` 和各类编译产物都忽略了。

### .claude —— Claude Code 配置

| 路径 | 说明 |
|------|------|
| `skills/unit-test/` | `/unit-test` —— 给 Python 代码写单元测试并出报告 |
| `skills/comment-check/` | `/comment-check` —— 检查注释够不够、和代码对不对得上 |
| `skills/security-audit/` | `/security-audit` —— 查硬编码密钥、SQL 注入、危险写法 |
| `skills/git-save/` | `/git-save` —— 扫垃圾文件 + 跑检查，通过后自动提交推送 |
| `skills/run-app/` | `/run-app` —— 打开每日记账 App |
| `skills/evaluate/` | `/evaluate` —— 三层评估体系，给 skill / 工作流做体检 |
| `agents/quality-engineer.md` | 代码质量检查专员（子代理） |
| `agents/tester.md` | 单元测试专员（子代理） |

每个技能的具体用法都写在自己的 `SKILL.md` 开头，这里不重复。

### .githooks —— 提交质量门禁

提交前自动检查的一道关卡：只有当 `save-gate/` 下存在"测试通过"和"质量通过"两个标记，且标记生成后代码没再被改动过，才允许提交。

| 文件 | 作用 |
|------|------|
| `pre-commit` | shell 入口，只负责转发给 Python 版本（绕开 Windows 下中文路径和换行的坑） |
| `pre-commit.py` | 门禁的实际逻辑 |
| `test_pre_commit.py` | 门禁自身的单元测试 |

启用方式：`git config core.hooksPath .githooks`。

### save-gate

空目录。它是 pre-commit 门禁的"通行证存放处"——`/git-save` 检查通过后会往这里写标记文件，门禁读到标记才放行提交。整个目录被 `.gitignore` 忽略，不入库。

---

## 根目录脚本

三个画图脚本，主题都是宏观经济数据。

| 文件 | 作用 |
|------|------|
| `fetch_pop.py` | 从联合国 WPP2024 下载中国分年龄人口数据，筛出 2016 / 2026 / 2036 三个年份，存成 CSV |
| `chart_pop.py` | 读上面那个 CSV，画三张对比的人口金字塔 |
| `chart_econ.py` | 画中国 GDP 增速图：2016–2025 是统计局实际值，2026–2046 是按社科院潜在增速做的平滑测算 |

产出文件：

- `china_pop_2016_2026_2036.csv` —— 人口数据（fetch_pop.py 的产物）
- `china_pop_pyramid_2016_2026_2036.png` —— 人口金字塔图（chart_pop.py 的产物）
- `china_gdp_growth_2016_2046.png` —— GDP 增速图（chart_econ.py 的产物）

> 运行顺序：先 `fetch_pop.py` 拿数据，再 `chart_pop.py` 画图。`chart_econ.py` 的数据直接写在脚本里，可以单独跑。

**注意**：`fetch_pop.py` 和 `chart_pop.py` 里的输出路径是写死的旧路径（`d:\git仓库\Git test repository\...`），和仓库现在的实际位置对不上。要跑的话得先把这两处路径改成当前目录。

---

## 其他文件

| 文件 | 说明 |
|------|------|
| `TODO.md` | 任务清单模板，写清任务状态后配合 Claude Code 的 `/loop` 反复推进。文件开头有完整用法说明 |
| `.gitignore` | 忽略规则：LaTeX 编译产物、Python 缓存、记账数据、门禁标记、脚本生成的图片和 CSV |
| `.gitattributes` | 换行符和编码相关配置 |

---

## 想用哪个，从这里找

| 想做什么 | 去哪里 |
|----------|--------|
| 记账 | `每日记账App/启动记账.bat` |
| 专注学习 | `番茄钟项目/番茄钟.py` |
| 和朋友联机打游戏 | `SnakeBattle/启动游戏.bat` |
| 手机上打卡 | `smartphone app/日程规划app/index.html` |
| 问自己资料库的问题 | `LangChainRAG/启动系统.bat` |
| 做学术 PPT | `Academic PPT/inbox/` 放论文，然后走 Marp 流程 |
| 画数据图 | 根目录那三个脚本 |
