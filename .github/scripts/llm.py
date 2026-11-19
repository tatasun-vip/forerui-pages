#!/usr/bin/env python3
"""
FORÊ Agent 共用 · 零成本 LLM 客户端

设计原则
--------
1. **零 Key、零成本**：默认走 Pollinations 公开推理接口（OpenAI 兼容），不需要任何 API Key。
2. **永不阻塞**：任何失败都只往 stderr 写原因、退出码 0，调用方据 stdout 是否为空决定是否回退模板。
3. **可替换**：若以后配了 LLM_BASE_URL / LLM_API_KEY / LLM_MODEL 环境变量，会自动优先走自建或商业接口。

用法
----
    echo '{"system":"...","user":"...","max_tokens":600}' | python3 .github/scripts/llm.py --out /tmp/ai.md
    python3 .github/scripts/llm.py --request /tmp/req.json --out /tmp/ai.md --expect-json

退出码恒为 0（除非参数错误），保证 workflow 不会因为模型抖动而失败。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

FREE_ENDPOINT = "https://text.pollinations.ai/openai"
DEFAULT_MODEL = os.environ.get("LLM_MODEL", "openai")


def log(msg: str) -> None:
    print(f"[llm] {msg}", file=sys.stderr)


def post_json(url: str, payload: dict, headers: dict, timeout: int = 90) -> dict:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")
    req.add_header("Accept", "application/json")
    req.add_header("User-Agent", "Fore-Agent/1.0 (+https://forerui.com)")
    for k, v in headers.items():
        req.add_header(k, v)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_text(data: dict) -> str:
    """兼容 OpenAI 风格与 Pollinations 附加字段。"""
    choices = data.get("choices") or []
    if choices:
        msg = choices[0].get("message") or {}
        content = msg.get("content")
        if isinstance(content, list):  # 多段内容
            content = "".join(
                c.get("text", "") for c in content if isinstance(c, dict)
            )
        if content:
            return str(content).strip()
    for key in ("text", "response", "output"):
        if isinstance(data.get(key), str):
            return data[key].strip()
    return ""


def strip_fences(text: str) -> str:
    t = text.strip()
    t = re.sub(r"^```(?:json|markdown|md)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    return t.strip()


def try_free(system: str, user: str, max_tokens: int, temperature: float) -> str:
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "referrer": "forerui.com",
    }
    data = post_json(FREE_ENDPOINT, payload, {})
    return extract_text(data)


def try_custom(system: str, user: str, max_tokens: int, temperature: float) -> str:
    base = os.environ.get("LLM_BASE_URL", "").rstrip("/")
    key = os.environ.get("LLM_API_KEY", "")
    if not base or not key:
        raise RuntimeError("未配置 LLM_BASE_URL / LLM_API_KEY")
    payload = {
        "model": DEFAULT_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    data = post_json(f"{base}/chat/completions", payload, {"Authorization": f"Bearer {key}"})
    return extract_text(data)


def generate(system: str, user: str, max_tokens: int, temperature: float,
             attempts: int = 3, base_wait: int = 18) -> str:
    providers = []
    if os.environ.get("LLM_BASE_URL") and os.environ.get("LLM_API_KEY"):
        providers.append(("custom", try_custom))
    providers.append(("pollinations", try_free))

    for name, fn in providers:
        for i in range(1, attempts + 1):
            try:
                text = strip_fences(fn(system, user, max_tokens, temperature))
                if text:
                    log(f"{name} 成功（第 {i} 次尝试，{len(text)} 字符）")
                    return text
                log(f"{name} 返回空内容（第 {i} 次）")
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    body = e.read().decode("utf-8", "ignore")[:200]
                except Exception:
                    pass
                log(f"{name} HTTP {e.code}（第 {i} 次）{body}")
            except Exception as e:  # noqa: BLE001
                log(f"{name} 异常（第 {i} 次）：{type(e).__name__}: {e}")
            if i < attempts:
                wait = base_wait * i
                log(f"等待 {wait}s 后重试（免费接口限流约 45s/次）")
                time.sleep(wait)
    return ""


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", help="请求 JSON 文件；省略则从 stdin 读")
    ap.add_argument("--out", help="把结果写入文件")
    ap.add_argument("--expect-json", action="store_true", help="尝试抽取合法 JSON")
    args = ap.parse_args()

    raw = open(args.request, encoding="utf-8").read() if args.request else sys.stdin.read()
    req = json.loads(raw)

    text = generate(
        system=req.get("system", "你是福尘 FORÊ 的品牌文案写手。"),
        user=req.get("user", ""),
        max_tokens=int(req.get("max_tokens", 900)),
        temperature=float(req.get("temperature", 0.9)),
        attempts=int(req.get("attempts", 3)),
    )

    if args.expect_json and text:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                text = json.dumps(json.loads(m.group(0)), ensure_ascii=False, indent=2)
            except json.JSONDecodeError:
                log("JSON 解析失败，保留原始文本")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(text)
        log(f"已写入 {args.out}（{len(text)} 字符）")

    if text:
        print(text)
    else:
        log("全部通道失败，调用方应回退到本地模板")
    return 0


if __name__ == "__main__":
    sys.exit(main())
