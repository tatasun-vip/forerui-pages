#!/usr/bin/env python3
"""
FORÊ Agent 8 · X 推广官 —— 帖子生成 + Buffer 排程

职责
----
1. 每天生成 1-2 条中英对照的 X 帖子（280 字符内）
2. 生成话题标签、回复建议、内容日历
3. 若配置了 BUFFER_ACCESS_TOKEN，则通过 Buffer REST API v1 排程；否则只产出草稿

严格约束
--------
- 单条 ≤ 280 字符（英文按字符计），超长自动截断并重算
- 同一天不重复：与仓库内 `x-posts.jsonl` 历史做相似度去重
- 不用固定模板轮换 —— 必须走免费 LLM 生成
- 禁用词：治愈/疗愈/治疗/保证/有效率/算命/包治（支付平台合规）
- 不做真人身份的高风险互动（争议回复、私信成交）——那部分留给真人

用法
----
    python3 .github/scripts/x_post.py --out /tmp/post.json
    python3 .github/scripts/x_post.py --buffer --out /tmp/post.json
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import generate, log  # noqa: E402

BLESSINGS_URL = (
    "https://raw.githubusercontent.com/tatasun-vip/"
    "chinese-blessing-seals/main/data/blessings.json"
)

HISTORY_FILE = "x-posts.jsonl"
# Buffer 新 GraphQL API（旧 REST v1 api.bufferapp.com 已废弃，2027-02-01 关闭）
BUFFER_GRAPHQL = "https://api.buffer.com"

MAX_LEN = 280
BANNED = [
    "治愈", "疗愈", "治疗", "保证", "有效率", "包治", "算命", "风水改运",
    "cure", "heal", "guarantee", "therapeutic",
]

# 帖子类型（内容支柱）—— 轮换但仍由 LLM 自由发挥
PILLARS = [
    {
        "key": "card-drop",
        "label": "每日福文",
        "hint": "今天推一枚具体符文：四字 + 英文 + 一句情绪钩子 + 落地页链接",
    },
    {
        "key": "quiet-philosophy",
        "label": "佛系箴言",
        "hint": "一句关于放下、不争、慢下来的东方哲思，中英对照，不带链接",
    },
    {
        "key": "behind-the-scenes",
        "label": "手绘幕后",
        "hint": "宣纸、朱砂、金墨、枯笔飞白——讲这张卡是怎么画出来的，带链接",
    },
    {
        "key": "use-case",
        "label": "生活场景",
        "hint": "一个具体的深夜/清晨/通勤场景，引出这枚符文，结尾一句提问引导互动",
    },
    {
        "key": "membership",
        "label": "会员叙事",
        "hint": (
            "讲清楚「九十天一个温养周期」这个概念：符文不是一次买断的图片，"
            "每枚有自己的季；到期可续请同一枚，也可换一枚重新起缘；"
            "季度/年度/永久三档只是让续请不必每次重新决定。"
            "语气克制、讲理念不推销、绝对不要罗列价格数字"
        ),
    },
    {
        "key": "story-serial",
        "label": "连载故事",
        "hint": (
            "讲一个具体的人和一个具体场景的真实感小故事（用欧美名字+城市，如 Maya/Chicago、Daniel/London、Sophie/Toronto）："
            "深夜/清晨/搬家/想家这类安静时刻，一枚四字福文如何被贴在某处、成为一份贴身的心意寄托。"
            "语气像转述别人的信，克制不煽情，绝不承诺灵验或结果。"
            "结尾用一句钩子引导读下一则故事或请一枚自己的福文，链接用 https://blessing.forerui.com/story/"
        ),
    },
]

SYSTEM_PROMPT = """你是 FORÊ（福尘）品牌的 X（Twitter）内容写手，为一个"来自东方的神秘佛系"人设账号写帖子。

人设：安静、克制、有东方文脉但不玄学、不说教、不算命。像一个在深夜写字的人，而不是营销号。

硬性规则：
1. 单条帖子（英文部分）必须 ≤ 280 字符。你会同时给出中文版和英文版，两个都要短。
2. **绝对禁止**这些词：治愈、疗愈、治疗、保证、有效率、包治、算命、风水改运、cure、heal、guarantee、therapeutic。
3. 功效只能写成「精神寄托 / 心境 / 心绪 / 符意 / 温养 / 陪伴」这类主观语汇。
4. 允许出现链接。默认链接用 https://forerui.com/?src=x；若写「连载故事」支柱，链接改用地 https://blessing.forerui.com/story/（引导读下一则故事）。
5. 不要用"亲们""家人们""绝绝子"这类电商腔。
6. 不要堆砌 emoji，最多 1 个。
7. 英文是意译，不是直译；英文版要像母语者写的短诗或短句。

严格输出 JSON。**第一行就是 `{`，最后一行就是 `}`，不要任何前后说明文字，不要 markdown 代码块包裹。**

JSON 结构：
{"zh":"中文版帖子","en":"English post under 280 chars","tags":["福尘FORÊ","tag2"],"reply_hooks":["question1","question2"]}

要求：
- zh 与 en 都要短。en 严格 ≤ 280 字符（含空格与链接）。
- tags 恰好 3 个，第一个必须是 福尘FORÊ。
- reply_hooks 恰好 2 个开放式问题。
- 链接：默认 https://forerui.com/?src=x；「连载故事」支柱用 https://blessing.forerui.com/story/
"""


def fetch_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "Fore-Agent/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_cards() -> list:
    try:
        data = fetch_json(BLESSINGS_URL)
        if isinstance(data, dict):
            data = data.get("blessings") or data.get("cards") or list(data.values())
        return data
    except Exception as e:  # noqa: BLE001
        log(f"拉取 124 卡失败：{e}")
        return []


def load_history() -> list:
    if not os.path.exists(HISTORY_FILE):
        return []
    out = []
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except Exception as e:  # noqa: BLE001
        log(f"读历史失败：{e}")
    return out


def append_history(entry: dict) -> None:
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def has_banned(text: str) -> list:
    low = text.lower()
    return [w for w in BANNED if w.lower() in low]


def clip_en(text: str, limit: int = MAX_LEN) -> str:
    """在链接前按词边界截断，保证链接完整且英文读起来不断词。"""
    if len(text) <= limit:
        return text
    link = ""
    m = re.search(r"https?://\S+", text)
    if m:
        link = m.group(0)
    head = text[: m.start()].rstrip() if m else text
    room = limit - len(link) - 1
    if room < 40:
        # 链接本身就超长 → 极简处理
        return (link + " " + head[: max(0, limit - len(link) - 1)]).strip()[:limit]
    if len(head) > room:
        # 按词边界回退：找到最后一个空格，避免英文断词
        cut = head[:room]
        sp = cut.rfind(" ")
        if sp > room * 0.55:
            cut = cut[:sp]
        head = cut.rstrip().rstrip(",.;:!?—-")
    sep = "" if head.endswith((" ", "…")) else "…"
    result = (head + sep + " " + link).strip()
    # 双保险：仍超长则硬截
    return result[:limit] if len(result) > limit else result


def clip_zh(text: str, limit: int = 140) -> str:
    """中文版按字截断（汉字宽度按 1 计，够用）。"""
    if len(text) <= limit:
        return text
    m = re.search(r"https?://\S+", text)
    link = m.group(0) if m else ""
    head = text[: m.start()].rstrip() if m else text
    room = limit - len(link) - 1
    if room < 30:
        return (link + "…")[:limit]
    return (head[:room].rstrip() + "…\n" + link)[: limit + len(link) + 2]


def parse_json(text: str) -> dict:
    """
    宽松 JSON 解析。免费模型经常：
    - 包 markdown 代码块
    - 前后带解释文字
    - 少写引号 / 用单引号
    - 被 max_tokens 截断
    这里逐级降级，尽量救回来。
    """
    if not text:
        return {}
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)

    # 1. 标准解析
    m = re.search(r"\{[\s\S]*\}", t)
    if m:
        for candidate in (m.group(0), t):
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                pass

    # 2. 单引号 → 双引号
    try:
        fixed = re.sub(r"'([^'\"]*)'", r'"\1"', t)
        obj = json.loads(fixed)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # 3. 字段级正则兜底
    out: dict = {}
    for key in ("zh", "en"):
        km = re.search(rf'"{key}"\s*:\s*"([^"]*)"', t)
        if not km:
            km = re.search(rf"'{key}'\s*:\s*'([^']*)'", t)
        if km:
            out[key] = km.group(1)
    tm = re.search(r'"tags"\s*:\s*\[([^\]]*)\]', t)
    if tm:
        out["tags"] = re.findall(r'"([^"]+)"', tm.group(1))
    rm = re.search(r'"reply_hooks"\s*:\s*\[([^\]]*)\]', t)
    if rm:
        out["reply_hooks"] = re.findall(r'"([^"]+)"', rm.group(1))

    return out if (out.get("zh") or out.get("en")) else {}


def similar(a: str, b: str) -> float:
    """粗略字符集合 Jaccard 相似度。"""
    sa, sb = set(a.lower()), set(b.lower())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def template_post(cards: list, pillar: dict, rng: random.Random) -> dict:
    """LLM 不可用时的确定性回退。"""
    card = rng.choice(cards) if cards else {
        "chinese": "福星高照",
        "english": "Blessings of the Auspicious Star",
        "story": {"zh": "有些好运不用等，它只是需要你带着它走一段路。"},
    }
    link = "https://forerui.com/?src=x"
    zh = f"{card['chinese']} —— {card.get('story', {}).get('zh', '')[:40]}…\n{link}"
    en = f"{card['english']}.\n\n{card.get('story', {}).get('en', '')[:150]}\n\n{link}"
    return {
        "zh": zh,
        "en": clip_en(en),
        "tags": ["福尘FORÊ", "手绘符文", "东方美学"],
        "reply_hooks": ["你今天最想被哪四个字护着？", "这副手印，你会做到第几个？"],
        "pillar": pillar["key"],
        "card": card.get("chinese", ""),
    }


def buffer_graphql(query: str, variables: dict | None = None) -> dict:
    """Buffer GraphQL API：Bearer 个人 key，POST 一个 endpoint。"""
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    if not token:
        raise RuntimeError("未配置 BUFFER_ACCESS_TOKEN")
    body = {"query": query}
    if variables:
        body["variables"] = variables
    req = urllib.request.Request(
        BUFFER_GRAPHQL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
            "User-Agent": "Fore-SEO/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("errors"):
        raise RuntimeError(str(data["errors"])[:300])
    return data.get("data", {})


def _find_x_channel() -> tuple[str, str] | None:
    """查 account → organizations → channels，找到 X/Twitter 频道与其 org。"""
    q = """
    query {
      account {
        organizations { id name }
      }
    }
    """
    acct = buffer_graphql(q).get("account") or {}
    orgs = acct.get("organizations") or []
    if not orgs:
        # 有些账号 channels 不需要 org，尝试不带 org 查询
        orgs = [{"id": ""}]
    for org in orgs:
        oid = org.get("id", "")
        cq = """
        query($organizationId: OrganizationId!) {
          channels(input: { organizationId: $organizationId }) {
            id service type
          }
        }
        """ if oid else """
        query {
          channels { id service type }
        }
        """
        vars_ = {"organizationId": oid} if oid else None
        try:
            channels = (buffer_graphql(cq, vars_).get("channels") or [])
        except Exception:  # noqa: BLE001
            continue
        for c in channels:
            if c.get("service") in ("twitter", "x"):
                return c["id"], oid
    return None


def publish_to_buffer(post: dict) -> dict:
    """用 Buffer GraphQL 创建 X 帖；失败不抛出，返回结果说明。"""
    token = os.environ.get("BUFFER_ACCESS_TOKEN", "")
    if not token:
        return {"ok": False, "reason": "no-token"}
    try:
        found = _find_x_channel()
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"channels-failed: {e}"}
    if not found:
        return {"ok": False, "reason": "no-x-channel"}
    channel_id, org_id = found

    scheduled_at = os.environ.get("X_SCHEDULED_AT", "").strip()
    text = f"{post['en']}\n\n" + " ".join(f"#{t}" for t in post.get("tags", []))
    text = clip_en(text)

    # 有指定时间用 customScheduled，否则 addToQueue 让 Buffer 自动排到下一个空档
    if scheduled_at:
        due = scheduled_at if scheduled_at.endswith("Z") else scheduled_at + ":00.000Z"
        mutation = """
        mutation($input: CreatePostInput!) {
          createPost(input: $input) {
            ... on PostActionSuccess { post { id dueAt } }
            ... on MutationError { message }
          }
        }
        """
        inp = {
            "text": text,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "customScheduled",
            "dueAt": due,
            "assets": [],
            "needsApproval": False,
        }
    else:
        mutation = """
        mutation($input: CreatePostInput!) {
          createPost(input: $input) {
            ... on PostActionSuccess { post { id dueAt } }
            ... on MutationError { message }
          }
        }
        """
        inp = {
            "text": text,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "assets": [],
            "needsApproval": False,
        }

    try:
        res = buffer_graphql(mutation, {"input": inp})
        cp = res.get("createPost") or {}
        if "message" in cp:  # MutationError
            return {"ok": False, "reason": f"create-error: {cp['message']}"}
        return {"ok": True, "channel": channel_id, "org": org_id, "result": cp}
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "reason": f"create-failed: {e}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="输出 JSON 文件")
    ap.add_argument("--buffer", action="store_true", help="有凭证时尝试排程到 Buffer")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else int(time.time() // 86400)
    rng = random.Random(seed)

    cards = load_cards()
    history = load_history()
    log(f"卡片 {len(cards)} 枚，历史帖子 {len(history)} 条")

    pillar = PILLARS[seed % len(PILLARS)]
    card = rng.choice(cards) if cards else None

    parts = []
    parts.append(f"【内容支柱】{pillar['label']} — {pillar['hint']}")
    if card:
        parts.append(
            f"【今日可用符文】{card.get('chinese', '')} / {card.get('english', '')}\n"
            f"  现有故事（可意译改写，不要照抄）：{card.get('story', {}).get('zh', '')[:80]}"
        )
    if history:
        recent = "、".join(h.get("en", "")[:40] for h in history[-5:])
        parts.append(f"【最近发过（严禁重复）】{recent}")
    parts.append(
        "【标签】只给 2-3 个，其中必须含中文标签 #福尘FORÊ。"
        "【回复钩子】给 2 个能让真人自然接话的开放式问题。"
    )

    text = generate(
        system=SYSTEM_PROMPT,
        user="\n".join(parts),
        max_tokens=700,
        temperature=0.9,
        attempts=3,
    )

    post = parse_json(text) if text else {}
    if not post.get("en") or not post.get("zh"):
        log("模型输出不可用，回退模板")
        post = template_post(cards, pillar, rng)
    else:
        post["pillar"] = pillar["key"]
        post["card"] = card.get("chinese", "") if card else ""
        post["en"] = clip_en(post["en"])
        post["zh"] = clip_zh(post.get("zh", ""))
        banned = has_banned(post.get("en", "") + post.get("zh", ""))
        if banned:
            log(f"命中禁用词 {banned}，回退模板")
            post = template_post(cards, pillar, rng)

    # 去重：与最近 20 条历史比对，相似度过高则重试一次，再不行就换支柱
    dup = False
    for h in history[-20:]:
        if similar(post.get("en", ""), h.get("en", "")) > 0.72:
            dup = True
            break
    if dup and history:
        log("与历史重复，换支柱重试")
        pillar = PILLARS[(seed + 1) % len(PILLARS)]
        text = generate(
            system=SYSTEM_PROMPT,
            user="\n".join(parts) + f"\n\n【重要】上一版重复了，请换一个完全不同的切入角度。",
            max_tokens=700,
            temperature=1.0,
            attempts=2,
        )
        post2 = parse_json(text) if text else {}
        if post2.get("en"):
            post2["en"] = clip_en(post2["en"])
            post2["pillar"] = pillar["key"]
            post2["card"] = card.get("chinese", "") if card else ""
            post = post2
        else:
            post = template_post(cards, pillar, rng)

    post["length_en"] = len(post.get("en", ""))
    post["date"] = time.strftime("%Y-%m-%d")

    buffer_result = None
    if args.buffer:
        buffer_result = publish_to_buffer(post)
        if buffer_result.get("ok"):
            log("已排程到 Buffer")
        else:
            log(f"Buffer 排程未成功：{buffer_result.get('reason')}")
    post["buffer"] = buffer_result

    append_history({
        "date": post["date"],
        "pillar": post.get("pillar"),
        "card": post.get("card"),
        "en": post.get("en", ""),
        "zh": post.get("zh", ""),
        "length_en": post["length_en"],
    })

    out = json.dumps(post, ensure_ascii=False, indent=2)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
        log(f"已写入 {args.out}")
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
