# forerui-pages

GitHub Pages landing page for [FORÊ](https://forerui.com) — 124 Chinese blessing seals (福文).

Serves at `https://blessing.forerui.com/`.

This is a free, indexable marketing landing page. All CTAs point back to forerui.com.

## 自动化协同体系

本仓库同时运行 6 个 GitHub Actions agent，24 小时无人值守维护站点、生产内容、加速收录。

| # | Agent | 频率 | 产出 |
|---|-------|------|------|
| 1 | 健康哨兵 | 每 3 小时 | 站点异常告警 Issue |
| 2 | 内容更新官 | 每天 | 每日福文页 `daily/` |
| 3 | 索引加速官 | 每天 | sitemap 刷新 + 搜索引擎通知 |
| 4 | SEO 巡检官 | 每周一 | SEO 体检 Issue |
| 5 | 网站优化官 | 每周三 | `[COPY]` 文案/商业提案 |
| 6 | 美术官 | 每月 1/15 日 | `[ART]` 设计提案 |

**完整分工、能力边界与协作流程见 → [AGENTS.md](./AGENTS.md)**

> 说明：社交运营（X 发帖、互动涨粉、真人成交）不在自动化范围内，需真人执行。

## 结构

```
index.html           英文落地页
zh/index.html        中文落地页
daily/index.html     每日福文（agent2 自动生成）
cards/               精选福文卡面
sitemap.xml          站点地图（agent2/3 自动维护）
robots.txt
CNAME                blessing.forerui.com
google*.html         Google Search Console 验证文件
AGENTS.md            agent 协同章程
.github/workflows/   6 个 agent 定义
```
