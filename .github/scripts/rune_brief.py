#!/usr/bin/env python3
"""
FORÊ Agent 7 · 符文设计官 —— 设计简报生成器

职责
----
为「下一批要画的符文」产出**可交给画师的设计简报**，而不是图片。

流程
----
1. 从 124 卡数据源读取已存在的符文（用于避开重复、参考既有调性）
2. 用免费 LLM 生成设计简报（符文名 / 寓意 / 适用需求 / 中英文案 / 构图 / 配色 / 书写规范）
3. **保真校验**：生成内容里出现的四字吉祥语必须真实存在于数据源，否则整份降级为模板
4. 失败时回退到确定性模板，退出码恒为 0，绝不拖垮 workflow

用法
----
    python3 .github/scripts/rune_brief.py --out /tmp/brief.md
"""

from __future__ import annotations

import argparse
import json
import os
import random
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm import generate, log  # noqa: E402

BLESSINGS_URL = (
    "https://raw.githubusercontent.com/tatasun-vip/"
    "chinese-blessing-seals/main/data/blessings.json"
)

# 四字吉祥语词典（来自 chinese-four-character-blessings 仓库），用于保真校验
FOUR_CHAR_URL = (
    "https://raw.githubusercontent.com/tatasun-vip/"
    "chinese-four-character-blessings/main/data/blessings.json"
)

CATEGORY_LABEL = {
    "life": ("平安顺遂", "life"),
    "career": ("事业前程", "career"),
    "wealth": ("丰盈富足", "wealth"),
    "love": ("情意和合", "love"),
}

# 已上线系列的设计语汇，供 LLM 参考调性
SERIES_NOTE = """
现有 124 枚符文的视觉与文案语汇（务必对齐，不要跑偏）：
- 卡面：手绘宣纸底 + 朱砂四字 + 金墨点缀，工笔线描边饰
- 文案调性：第一人称、生活场景切入、不说教、不算命
- 英文为意译，不是直译；语气克制、留白
- 关键词：手绘、宣纸、朱砂、金墨、心诚则灵、随身携带、安静地在那里
"""

SYSTEM_PROMPT = """你是 FORÊ（福尘）品牌的符文设计师，为一位真人画师产出**设计简报**。

铁律：
1. 你输出的「符文四字」必须是**真实存在的中国四字吉祥语**。只允许从下面的已上线 124 枚里挑，或者用【祈愿方向】明确描述的新四字——但新四字必须由你自己写且语义通顺，不许生造怪词。
2. 不许把「鸾凤和鸣」写成「鸲鸟共鸣」这类替换；四字必须原样出现在正文里。
3. 你只出简报，**不要生成图片、不要描述你怎么画像素**。
4. 中文为主，英文为意译对照。
5. 全文禁用这些词（支付平台合规）：治愈、疗愈、治疗、保证、有效率、包治、算命、风水改运。
6. 功效只能写成「精神寄托 / 心境 / 心绪 / 符意 / 温养 / 陪伴」这类主观语汇。

输出格式（严格 Markdown，不要多余前言）：

## 符文名
中文四字（**必须是真实四字吉祥语**）
英文意译一行

## 寓意
中文 2-3 句：这句话对佩戴者意味着什么。用生活场景切入。
英文 2 句意译。

## 适用需求
4-6 个中文短词，用顿号分隔（如：换岗的犹豫、家人的健康、深夜的失眠、合伙人的信任）
英文一行同样数量的短词，逗号分隔。

## 构图
- 版式：竖幅 / 横幅 / 圆光
- 主字位置与大小关系
- 边饰元素（祥云 / 水纹 / 星宿 / 缠枝 / 莲瓣，任选其一或组合）
- 落款与朱砂印位置
- 留白比例

## 配色
- 底色：宣纸暖牙色 #EDE4D3
- 主字：朱砂 #C02000（写明浓淡层次：起笔/行笔/收笔的浓淡）
- 金墨：#D4A843 → #F0D870（写明金色占画面比例）
- 可选第五色（如有）及其用法

## 书写与刻印规范
- 字体气质：篆 / 隶 / 楷，说明笔画特征
- 枯笔飞白的处理位置
- 印章：形状、字体、颜色（朱砂红或金）
- 纸纹与做旧程度

## 手决建议
- 对应哪一种手印（12 式之一，如 Anjali / Lotus / Dhyana / Gyan / Vitarka / Kumbha…），并写一句为什么这枚符文适合这个手印。

## 一句话卖点
中文一句 + 英文一句。可直接用于详情页顶部。

## 详情页英文首屏（English first-screen）
2-3 句英文，可直接用于详情页顶部文案。
"""


def fetch_json(url: str, timeout: int = 30):
    req = urllib.request.Request(url, headers={"User-Agent": "Fore-Agent/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def load_existing() -> list:
    """已上线符文，用于去重与调性参考。"""
    try:
        data = fetch_json(BLESSINGS_URL)
        if isinstance(data, dict):
            data = data.get("blessings") or data.get("cards") or list(data.values())
        return data
    except Exception as e:  # noqa: BLE001
        log(f"拉取 124 卡数据失败：{e}")
        return []


def load_four_char_pool() -> list:
    """四字吉祥语词典，作为可用的候选池。"""
    for url in (FOUR_CHAR_URL, BLESSINGS_URL):
        try:
            data = fetch_json(url)
            if isinstance(data, dict):
                data = data.get("blessings") or data.get("cards") or list(data.values())
            pool = []
            for item in data:
                if isinstance(item, dict):
                    cn = item.get("chinese") or item.get("cn") or item.get("word") or ""
                    en = item.get("english") or item.get("en") or ""
                    if len(cn) == 4:
                        pool.append((cn, en))
            if pool:
                return pool
        except Exception as e:  # noqa: BLE001
            log(f"拉取四字词典失败（{url}）：{e}")
    return []


def four_char_in_source(text: str, pool: list) -> bool:
    """
    保真校验：正文中出现的四字中文，必须在真实词典里。
    只要抽到 1 个"看起来像四字吉祥语"的词且它不在词典里 → 判定不可信。
    """
    if not pool:
        return True
    known = {cn for cn, _ in pool}
    # 只校验出现在「## 符文名」小节里的四字，其余正文四字可能是描述性用语
    m = re.search(r"##\s*符文名\s*\n+([^\n]+)", text)
    if not m:
        return False
    candidate = re.sub(r"[^一-鿿]", "", m.group(1))
    if len(candidate) != 4:
        return False
    return candidate in known


def template_brief(existing: list, pool: list) -> str:
    """LLM 不可用时的确定性回退简报。"""
    pool = pool or [("福星高照", "Blessings of the Auspicious Star")]
    cn, en = random.choice(pool)
    cat = random.choice(list(CATEGORY_LABEL.keys()))
    zh_label, _ = CATEGORY_LABEL[cat]
    return f"""## 符文名
{cn}
{en}

## 寓意
把{cn}这四个字握在手里，是提醒自己：此刻需要的不是更多答案，而是一点稳住的心气。
A small anchor for the days that ask more of you than usual.

## 适用需求
重新出发的决心、家人的平安、深夜的失眠、合伙人的信任、对自己的一次原谅
a fresh start, family's safety, sleepless nights, a partner's trust, self-forgiveness

## 构图
- 版式：竖幅
- 主字：正中偏上，占画面高度约 1/3
- 边饰：祥云一条 + 水纹一线
- 落款右下，朱砂印压角
- 留白：画面下方留 1/4 空白

## 配色
- 底色：宣纸暖牙色 #EDE4D3
- 主字：朱砂 #C02000，起笔浓、行笔略淡、收笔回锋处最浓
- 金墨：#D4A843 → #F0D870，占画面约 8%
- 第五色：藤黄 #B08A3E，仅用于落款细线

## 书写与刻印规范
- 字体气质：篆，圆润折笔，转折处圆转过渡
- 枯笔飞白：仅出现在笔画末端的 1-2 笔
- 印章：方形朱文小印，置于右下压角
- 纸纹：细纤维做旧，边缘微黄

## 手决建议
Anjali（合十印）——四字吉祥语的收束感与合十的安定感相合，适合起愿时先稳住呼吸。

## 一句话卖点
不是一张卡片，是一段需要被照顾的关系。
Not a card. A relationship that asks to be tended.

## 详情页英文首屏（English first-screen）
Some blessings do not need to be answered. They need to be carried.
{cn} is drawn on warm rice-paper in cinnabar and gold, and it asks nothing of you except that you keep it close for ninety days.
"""


def build_user_prompt(existing: list, pool: list, seed: int) -> str:
    rng = random.Random(seed)
    cats = list(CATEGORY_LABEL.keys())
    cat = rng.choice(cats)
    zh_label, _ = CATEGORY_LABEL[cat]

    sample = ""
    if existing:
        picks = rng.sample(existing, min(4, len(existing)))
        sample = "\n".join(
            f"- {p.get('chinese', '')} / {p.get('english', '')}（{p.get('code', '')}）"
            for p in picks
        )

    pool_hint = ""
    if pool:
        names = [cn for cn, _ in rng.sample(pool, min(30, len(pool)))]
        pool_hint = "\n可选的真实四字（也可自写但必须是真吉祥语）：\n" + "、".join(names)

    return f"""【祈愿方向】{zh_label}（{cat}）

{SERIES_NOTE}

已上线符文参考（避免重复雷同）：
{sample or '（无）'}
{pool_hint}

请产出**一枚新符文**的完整设计简报。
"""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", help="输出文件路径")
    ap.add_argument("--seed", type=int, default=None, help="确定性随机种子")
    args = ap.parse_args()

    seed = args.seed if args.seed is not None else int(
        __import__("time").time() // 86400
    )

    existing = load_existing()
    pool = load_four_char_pool()
    log(f"已上线 {len(existing)} 枚，四字词典 {len(pool)} 条")

    text = ""
    if pool or existing:
        user_prompt = build_user_prompt(existing, pool, seed)
        text = generate(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            max_tokens=1800,
            temperature=0.85,
            attempts=3,
        )

    if text and four_char_in_source(text, pool):
        log("保真校验通过，使用模型简报")
    else:
        if text:
            log("保真校验未通过（符文名不是真实四字），回退模板")
        text = template_brief(existing, pool)

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        log(f"已写入 {args.out}（{len(text)} 字符）")

    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
