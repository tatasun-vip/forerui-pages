#!/usr/bin/env python3
"""FORÊ SEO 矩阵生成器：把 124 枚福文各生成一个独立可收录页面。

- 数据来源：chinese-blessing-seals/data/blessings.json（含中英故事）
- 每枚一个 URL：/seal/<CODE>/  （如 /seal/Y01/）
- 每页：独立 title/description + JSON-LD Product + 中英故事 + 下单 CTA
- 有卡图用卡图，无卡图用 CSS 印章占位（不影响文字收录）
"""

from __future__ import annotations
import html
import json
import os
import urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BLESSINGS_URL = (
    "https://raw.githubusercontent.com/tatasun-vip/"
    "chinese-blessing-seals/main/data/blessings.json"
)
CATEGORY_EN = {
    "life": "Life & Wellbeing", "love": "Love & Relationships",
    "career": "Career & Purpose", "wealth": "Wealth & Abundance",
}
SITE = "https://blessing.forerui.com"


def esc(s: str) -> str:
    return html.escape(s or "", quote=True)


def has_img(code: str) -> bool:
    return os.path.exists(os.path.join(BASE, "cards", f"{code}.png"))


def page(b: dict) -> str:
    code = b["code"]
    cn = b["chinese"]
    en = b["english"]
    cat = CATEGORY_EN.get(b.get("category", ""), "Blessings")
    story = b.get("story") or {}
    zh_story = story.get("zh", "")
    en_story = story.get("en", "")
    img = f'<img src="../../cards/{code}.png" alt="{esc(cn)} Chinese blessing seal" width="900" height="1257">' if has_img(code) else (
        f'<div class="seal-css"><span>{esc(cn)}</span></div>'
    )
    desc_en = (en_story[:150] or f"{en} — a hand-drawn Chinese blessing seal by FORÊ.").replace("\n", " ")
    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "Product",
        "name": f"{cn} — {en}",
        "image": f"{SITE}/cards/{code}.png" if has_img(code) else f"{SITE}/cards/Y01.png",
        "description": desc_en,
        "brand": {"@type": "Brand", "name": "FORÊ"},
        "category": cat,
        "sku": code,
        "offers": {
            "@type": "Offer",
            "price": "6.99", "priceCurrency": "USD",
            "url": "https://forerui.com/products?src=seo-seal",
            "availability": "https://schema.org/InStock",
        },
    }, ensure_ascii=False)

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{esc(cn)} · {esc(en)} — FORÊ Blessing Seal {code}</title>
<meta name="description" content="{esc(desc_en)}">
<link rel="canonical" href="{SITE}/seal/{code}/">
<link rel="icon" type="image/svg+xml" href="../../favicon.svg">
<meta name="theme-color" content="#EDE4D3">
<script type="application/ld+json">{ld}</script>
<style>
:root{{--paper:#EDE4D3;--paper2:#F5EFE2;--ink:#2B2118;--verm:#C02000;--gold:#B08A3E;--muted:#7A6A56}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--paper);color:var(--ink);font-family:Georgia,"Songti SC",serif;line-height:1.75}}
body::before{{content:"";position:fixed;inset:0;z-index:-1;opacity:.3;pointer-events:none;background-image:radial-gradient(#b9a888 .5px,transparent .5px);background-size:5px 5px}}
.wrap{{max-width:720px;margin:auto;padding:0 22px}}
header{{padding:22px 0;text-align:center;border-bottom:1px solid rgba(176,138,62,.3)}}
header a{{font-size:24px;letter-spacing:6px;color:var(--verm);text-decoration:none}}
.sealwrap{{text-align:center;padding:40px 0 20px}}
.sealwrap img,.seal-css{{width:220px;height:auto;display:block;margin:0 auto 18px;border:1px solid rgba(176,138,62,.4)}}
.seal-css{{height:280px;background:var(--paper2);display:flex;align-items:center;justify-content:center;border:2px solid var(--verm)}}
.seal-css span{{font-size:38px;letter-spacing:6px;color:var(--verm);writing-mode:vertical-rl}}
.kicker{{font-size:11px;letter-spacing:4px;color:var(--gold);text-transform:uppercase}}
h1{{font-size:clamp(28px,6vw,42px);font-weight:400;margin:12px 0 6px;letter-spacing:2px}}
.zh{{font-size:15px;color:var(--gold);letter-spacing:5px;margin-bottom:20px}}
.meta{{font-size:12px;color:var(--muted);letter-spacing:2px}}
.story{{padding:30px 0;border-top:1px solid rgba(176,138,62,.25)}}
.story h2{{font-size:12px;letter-spacing:4px;color:var(--verm);text-transform:uppercase;margin-bottom:14px}}
.story p{{font-size:16px;color:#3A2E23;margin-bottom:16px}}
.story p.zh{{font-size:14px;color:#6B5B48;line-height:1.9}}
.cta{{display:block;text-align:center;padding:15px;background:var(--verm);color:#F5EFE2;text-decoration:none;font-size:14px;letter-spacing:2px;margin:20px 0 10px}}
.sub{{display:block;text-align:center;font-size:11px;color:var(--muted)}}
nav{{text-align:center;padding:24px 0;font-size:13px}}
nav a{{color:var(--verm);text-decoration:none;margin:0 10px}}
footer{{text-align:center;padding:26px 0;color:var(--muted);font-size:11px;border-top:1px solid rgba(176,138,62,.25)}}
.disc{{font-size:10px;color:#9A8B76;margin-top:10px}}
@media(max-width:600px){{.sealwrap img,.seal-css{{width:180px}}}}
</style>
</head>
<body>
<header><div class="wrap"><a href="../../">FORÊ</a></div></header>
<main class="wrap">
  <div class="sealwrap">
    {img}
    <div class="kicker">Seal {code} · {esc(cat)}</div>
    <h1>{esc(en)}</h1>
    <div class="zh">{esc(cn)}</div>
    <div class="meta">Hand-drawn · Vermilion &amp; gold on rice paper · Instant digital download</div>
  </div>
  <section class="story">
    <h2>The story behind this seal</h2>
    <p>{esc(en_story)}</p>
    <p class="zh">{esc(zh_story)}</p>
  </section>
  <a class="cta" href="https://forerui.com/products?src=seo-seal">Make this seal yours · 请这一枚福文 →</a>
  <span class="sub">from $6.99 · instant download · forerui.com</span>
  <nav><a href="../">← All 124 seals</a><a href="../../story/">Stories</a><a href="../../">Home</a></nav>
</main>
<footer><div class="wrap">
  <p>FORÊ · 福尘 · 124 seals, one blessing</p>
  <p class="disc">A hand-drawn collectible artwork and a personal reminder — not fortune-telling, not a prediction. 手绘收藏艺术品与心意寄托，不是算命，不是预言。</p>
</div></footer>
</body>
</html>
'''


def main():
    req = urllib.request.Request(BLESSINGS_URL, headers={"User-Agent": "Fore-SEO/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        cards = json.loads(r.read().decode("utf-8"))
    outdir = os.path.join(BASE, "seal")
    os.makedirs(outdir, exist_ok=True)
    for b in cards:
        d = os.path.join(outdir, b["code"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "index.html"), "w", encoding="utf-8") as f:
            f.write(page(b))

    # 生成 index 列表页
    links = "\n".join(
        f'<a class="s" href="{b["code"]}/"><b>{esc(b["chinese"])}</b><span>{esc(b["english"])}</span><i>{b["code"]}</i></a>'
        for b in cards
    )
    idx = f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>124 Chinese Blessing Seals — Complete Collection — FORÊ</title>
<meta name="description" content="Browse all 124 hand-drawn Chinese blessing seals (福文) by FORÊ. Four characters, one wish. Each with its own story, in English and Chinese.">
<link rel="canonical" href="{SITE}/seal/"><link rel="icon" href="../../favicon.svg" type="image/svg+xml">
<style>:root{{--paper:#EDE4D3;--verm:#C02000;--gold:#B08A3E;--ink:#2B2118;--muted:#7A6A56}}
*{{box-sizing:border-box;margin:0;padding:0}}body{{background:var(--paper);color:var(--ink);font-family:Georgia,serif;line-height:1.7}}
.wrap{{max-width:1000px;margin:auto;padding:0 22px}}header{{text-align:center;padding:30px 0;border-bottom:1px solid rgba(176,138,62,.3)}}
header a{{font-size:26px;letter-spacing:6px;color:var(--verm);text-decoration:none}}
h1{{font-size:clamp(26px,5vw,40px);font-weight:400;text-align:center;margin:36px 0 8px}}
.sub{{text-align:center;color:var(--gold);letter-spacing:4px;font-size:14px;margin-bottom:30px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(200px,1fr));gap:12px;padding-bottom:50px}}
.s{{display:block;background:#F5EFE2;border:1px solid rgba(176,138,62,.3);padding:14px;text-decoration:none;color:var(--ink)}}
.s b{{display:block;font-size:19px;color:var(--verm);letter-spacing:3px}}
.s span{{display:block;font-size:11px;color:var(--muted);margin-top:5px;min-height:28px}}
.s i{{display:block;font-size:10px;color:var(--gold);font-style:normal;margin-top:8px;letter-spacing:1px}}
footer{{text-align:center;padding:26px 0;color:var(--muted);font-size:11px;border-top:1px solid rgba(176,138,62,.3)}}</style>
</head><body><header><div class="wrap"><a href="../">FORÊ</a></div></header>
<main class="wrap"><h1>All 124 Blessing Seals</h1><div class="sub">一二四枚福文 · 每一枚，一个愿</div>
<div class="grid">
{links}
</div></main>
<footer>FORÊ · forerui.com · A wish, not a prediction.</footer></body></html>
'''
    with open(os.path.join(outdir, "index.html"), "w", encoding="utf-8") as f:
        f.write(idx)

    # 生成 sitemap（含全部 seal 页）
    urls = [("/", "1.0"), ("/zh/", "0.8"), ("/story/", "0.8"),
            ("/daily/", "0.6"), ("/seal/", "0.9")] + [(f"/seal/{b['code']}/", "0.6") for b in cards]
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for p, pri in urls:
        lines.append(f"  <url><loc>{SITE}{p}</loc><changefreq>weekly</changefreq><priority>{pri}</priority></url>")
    lines.append("</urlset>")
    with open(os.path.join(BASE, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"生成 {len(cards)} 个福文页 + 列表页 + sitemap（{len(urls)} URL）")


if __name__ == "__main__":
    main()
