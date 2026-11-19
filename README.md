# forerui-pages

GitHub Pages landing page for [FORÊ](https://forerui.com) — 124 Chinese blessing seals (福文).

Serves at `https://blessing.forerui.com/`.

This is a free, indexable marketing landing page. All CTAs point back to forerui.com.

## 自动化协同体系

本仓库同时运行 8 个 GitHub Actions agent，24 小时无人值守维护站点、生产内容、加速收录、产出设计简报与 X 推广内容。

| # | Agent | 频率 | 产出 |
|---|-------|------|------|
| 1 | 健康哨兵 | 每 3 小时 | 站点异常告警 Issue |
| 2 | 内容更新官 | 每天 | 每日福文页 `daily/` |
| 3 | 索引加速官 | 每天 | sitemap 刷新 + 搜索引擎通知 |
| 4 | SEO 巡检官 | 每周一 | SEO 体检 Issue |
| 5 | 网站优化官 | 每周三 | `[COPY]` 文案/商业提案 |
| 6 | 美术官 | 每月 1/15 日 | `[ART]` 设计提案 |
| 7 | 符文设计官 | 每周一 | `[RUNE]` 设计简报 + `design-briefs/` |
| 8 | X 推广官 | 每天 2 次 | `[X]` 帖子草稿 + `x-posts/`（配 Buffer 后自动排程） |

**完整分工、能力边界与协作流程见 → [AGENTS.md](./AGENTS.md)**

> 边界：X 帖子的**内容生产与排程**已自动化；**真人身份互动、争议回复、成交转化**仍需本人。

## 免费 LLM

所有内容型 agent 走 `.github/scripts/llm.py`：

- 默认通道 **Pollinations**（OpenAI 兼容，零 Key 零成本），约每 IP 每 45 秒 1 次
- 失败自动退避重试 → 仍失败则回退确定性模板，**永不拖垮 workflow**
- 配 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` 后自动切换到自建或商业接口

| 脚本 | 用途 |
|------|------|
| `.github/scripts/llm.py` | 共用 LLM 客户端（重试 / 退避 / 多通道） |
| `.github/scripts/rune_brief.py` | Agent 7 符文设计简报（四字保真校验） |
| `.github/scripts/x_post.py` | Agent 8 X 帖子生成（280 字符校验 + 去重 + Buffer 排程） |

## 需要配置的 Secret

| Secret | 作用 | 不配的后果 |
|--------|------|-----------|
| `BUFFER_ACCESS_TOKEN` | Agent 8 自动排程/发布 X 帖子 | 只出草稿 Issue，帖文需手动发 |
| `X_SCHEDULED_AT` | 固定排程时间（ISO 8601） | 帖子进 Buffer 待发队列 |

## 结构

```
index.html           英文落地页
zh/index.html        中文落地页
daily/index.html     每日福文（agent2 自动生成）
cards/               精选福文卡面
design-briefs/       符文设计简报（agent7 自动归档）
x-posts/             X 帖子归档（agent8 自动归档）
x-posts.jsonl        X 发帖历史（agent8 用于去重）
sitemap.xml          站点地图（agent2/3 自动维护）
robots.txt
CNAME                blessing.forerui.com
google*.html         Google Search Console 验证文件
AGENTS.md            agent 协同章程
.github/scripts/     共用脚本
.github/workflows/   8 个 agent 定义
```
