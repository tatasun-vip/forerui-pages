# FORÊ 自动化协同体系 · Agent 分工与边界

> 本文件是这个协同项目的**正式章程**。所有 agent 的职责、产出、边界以此为准。
> 服务对象：[forerui.com](https://forerui.com) 与 [blessing.forerui.com](https://blessing.forerui.com)

---

## 一、八个 Agent 分工

| # | Agent | 频率 | 职责 | 产出形式 |
|---|-------|------|------|---------|
| 1 | **健康哨兵** Health Sentinel | 每 3 小时 | 探测主站/落地页/sitemap/验证文件共 5 个关键 URL | 异常自动开 Issue（24h 去重） |
| 2 | **内容更新官** Daily Blessing | 每天 UTC 01:00 | 从 124 张福文按日期抽一张，生成中英双语每日福文页 | 自动提交 `daily/index.html` + 更新 sitemap |
| 3 | **索引加速官** Index Booster | 每天 UTC 02:00 | 刷新 sitemap `lastmod`，通知 Bing IndexNow / Google | 自动提交 sitemap |
| 4 | **SEO 巡检官** SEO Auditor | 每周一 UTC 03:00 | 校验 9 项 SEO 要素（meta/canonical/JSON-LD/XML/CNAME） | 异常开 Issue 报告 |
| 5 | **网站优化官** Narrative & Offers | 每周三 UTC 04:00 | 轮换产出：符文即精神寄托 / 时效与功效 / 会员制方案 | `[COPY]` Issue 提案 |
| 6 | **美术官** Art Director | 每月 1 日、15 日 | 轮换产出：符文视觉迭代 / 网站视觉与体验 | `[ART]` Issue 提案 |
| 7 | **符文设计官** Rune Designer | 每周一 UTC 06:00 | 产出下一批符文的**可执行设计简报**（名/寓意/需求/构图/配色/书写/手决） | `[RUNE]` Issue + `design-briefs/` 归档 |
| 8 | **X 推广官** X Promoter | 每天 UTC 07:10 / 15:10 | 生成中英 X 帖子、话题标签、回复钩子；配 Buffer 后可排程 | `[X]` Issue + `x-posts/` 归档 |

### 免费模型接入

所有内容型 agent（2 / 5 / 6 / 7 / 8）统一走 `.github/scripts/llm.py`：

- **默认通道**：Pollinations 公开推理接口（OpenAI 兼容，**零 Key 零成本**）
- **限流**：约每 IP 每 45 秒 1 次 → 各 agent 的 cron 刻意错开，脚本内含退避重试
- **永不阻塞**：任何失败都回退确定性模板，退出码恒为 0，不拖垮 workflow
- **可替换**：配 `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` 后自动优先走自建或商业接口
- **保真校验**：Agent 7 的符文四字必须真实存在于 124 卡词典，否则整份简报回退模板

---

## 二、能力边界（重要）

### ✅ 这套自动化负责
- **站点维护**：可用性监控、异常告警
- **内容生产**：每日福文、SEO 文案提案、设计提案、符文设计简报
- **收录加速**：sitemap 刷新、搜索引擎通知
- **SEO 巡检**：结构化数据与关键标签不退化
- **X 内容生产与排程**：生成中英帖子、话题标签、回复钩子；配置 Buffer 凭证后可自动排程/发布

### ❌ 这套自动化不负责（需真人）
- **真人身份互动**：回复粉丝、私信、争论、把账号当成"真人"去经营信任
- **争议与高风险回复**：涉及退款、投诉、法律、健康承诺的对话
- **成交转化**：临门一脚的谈判、客户关系维护、承诺交付
- **最终发布决策**：X 帖子在无 Buffer 凭证时只出草稿，由老板亲自按下发送
- **支付与产品逻辑**：会员制、时效校验、定价改动需人工决策后单独开发
- **实际绘制与制图**：Agent 7 只出简报，符文一律真人手绘

> **一句话**：机器人做确定性的、可重复的、无需判断的工作；需要临时判断、需要真人身份、涉及金钱与关系的动作，一律留给真人。

---

## 三、安全与权限原则

1. **不自动改线上产品代码**。agent5/agent6/agent7 只产出 Issue 提案，老板审阅采纳后才由人工落地。
2. **不碰支付**。所有涉及金额、订阅、退款的改动都不在自动化范围内。
3. **不使用 AI 生成图**。美术官与符文设计官只给配色/构图/文字方向，实际符文一律真人手绘——避免 AI 水印与版权风险。
4. **合规红线**。所有对外文案禁用「治愈/疗愈/治疗/保证/有效率/算命/风水改运」及英文 cure/heal/guarantee/therapeutic；功效只写精神寄托、心境、符意、温养、陪伴。
5. **凭证不落库**。Buffer access token 只存 GitHub Actions Secret，绝不写进仓库或 Issue。
6. **运行时不消耗个人 token**。GitHub Actions 使用自动生成的 `GITHUB_TOKEN`，每次运行后失效。
7. **public 仓库零成本**。标准 runner 免费不限分钟。

---

## 四、人机协作流程

```
Agent 定时运行
   ↓
产出（自动提交 / Issue 提案 / Buffer 排程）
   ↓
老板在 GitHub Issues 或对话中审阅
   ↓
采纳 → 人工（或我）落地到主站
   ↓
真人身份互动、成交、争议回复由老板本人完成
```

**提案类 Issue 的处理方式：**
- `[COPY]` 标签 = 网站优化官的文案/商业方案提案
- `[ART]` 标签 = 美术官的设计提案
- `[RUNE]` 标签 = 符文设计官的符文设计简报
- `[X]` 标签 = X 推广官的帖子草稿
- `[HEALTH]` 标签 = 站点异常告警（恢复后手动关闭）
- `[SEO]` 标签 = SEO 巡检问题

---

## 五、商业化构想（状态同步）

按老板 2026-11-20 提出的方向，以下内容已分批落地：

| 构想 | 核心逻辑 | 状态 |
|------|---------|------|
| 福文 = 精神寄托 | 不是普通卡片，是可随身携带的祝愿 | ✅ 已上线（文案 + 详情页区块） |
| 时效 + 功效 | 每张符文对应特定需求，按当下心境自选 | ✅ 已上线（`src/data/rune-efficacy.ts`） |
| 3 个月时效 | 到期需续请方继续生效（心诚则灵的东方逻辑） | ✅ 已上线文案，**支付逻辑待接** |
| 会员制 | 季度 / 年度 / 永久三档 | ✅ 已上线展示页 `/membership`，**支付待接** |
| 符文设计流水线 | Agent 7 出简报 → 真人画师出稿 | 🔄 Agent 7 已上线 |
| X 推广流水线 | Agent 8 出稿 → Buffer 排程 → 真人互动 | 🔄 Agent 8 已上线，**待配 Buffer 凭证** |

---

## 六、待老板手动完成的事

| 事项 | 说明 |
|------|------|
| Buffer access token | Buffer 仪表板 → Settings → Apps → Developer App → 复制 token，设为仓库 Secret `BUFFER_ACCESS_TOKEN` |
| X channel 确认 | 在 Buffer 里确认 X 账号已连接（Agent 8 会自动找 `service == twitter` 的 profile） |
| `X_SCHEDULED_AT`（可选） | 想固定排程时间就设，格式 ISO 8601；不设则进 Buffer 待发队列 |
| Google Search Console | 手动验证 + 提交 `https://blessing.forerui.com/sitemap.xml` |
| 真人 X 互动 | 回复、争议处理、成交仍需本人 |

---

*最后更新：2026-11-20 · 由 GitHub Actions 协同体系维护*
