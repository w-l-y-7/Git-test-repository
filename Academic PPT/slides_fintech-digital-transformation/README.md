# 金融科技与企业数字化转型 Slides

## 项目信息

- 创建时间：2026-09-12
- 输入材料：`inbox/金融科技与企业数字化转型——结构特征、渠道机制与三螺旋体系下的政策优化研究_胡妍 (1).docx`
- 出处：华南师范大学学报（社会科学版）2025 年第 6 期
- 场景：课堂 / 组会汇报，约 20 分钟
- **使用主题**：academic

## 文件夹说明

- `01_analysis/` — 内容分析和大纲
- `02_drafts/` — Slides 初稿
- `03_reviews/` — 审阅报告
- `04_exports/` — PNG 和 HTML 导出
- `05_final/` — 最终版本
- `assets/` — 架构图 SVG 等素材
- `themes/` — Marp 主题文件

## 制作进度

- [x] 阶段零：工作空间初始化
- [x] 阶段一：内容分析
- [x] 阶段二：初稿制作
- [x] 阶段三：多维度审阅（内容/格式/密度/视觉）
- [x] 阶段三B：中文语言规范审阅
- [x] 阶段四：PNG 转换检查（25 页逐页目视）
- [x] 阶段五：问题修复与终稿导出

## 终稿文件

`05_final/` 目录下：

| 文件 | 用途 |
|------|------|
| `presentation.md` | Markdown 源文件，改内容改这个 |
| `slides.pptx` | PowerPoint 可编辑版，能改文字、加备注 |
| `slides.pdf` | 放映与打印，公式图表最保真 |
| `slides.html` | 浏览器直接打开翻页 |

## 需要自己填的地方

封面（第 1 页）和尾页（第 25 页）的「汇报人：____」占位符，替换成姓名即可。

## 修改方式

改 `05_final/presentation.md` 后重新导出：

```powershell
npx @marp-team/marp-cli "05_final/presentation.md" -o "05_final/slides.pptx" --pptx-editable --html --theme-set "./themes/" --allow-local-files
```

把 `--pptx-editable` 换成 `--pdf` 出 PDF、换成 `--images png -o 04_exports/slides.png` 出逐页图片检查版式。
