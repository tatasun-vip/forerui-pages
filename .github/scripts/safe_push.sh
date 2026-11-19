#!/usr/bin/env bash
# FORÊ Agent 共用 · 安全提交推送
#
# 背景：多个 agent 并发往同一个分支 push 时会互相"抢跑"，
# 直接 git push 会被拒（fetch first）。这里统一做 rebase + 重试。
#
# 用法： safe_push.sh "<commit message>"
set -uo pipefail

MSG="${1:-chore: automated update}"

git config user.name "FORÊ Bot"
git config user.email "bot@forerui.com"

git add -A

if git diff --cached --quiet; then
  echo "无变化，跳过提交"
  exit 0
fi

git commit -m "$MSG"

for attempt in 1 2 3; do
  # 先把远端变化 rebase 进来（只在有远端更新时才动作）
  git pull --rebase --autostash origin main >/dev/null 2>&1 || true

  if git push origin main; then
    echo "已提交并推送：$MSG"
    exit 0
  fi

  echo "push 失败（第 ${attempt} 次），rebase 后重试…"
  git pull --rebase origin main >/dev/null 2>&1 || {
    git rebase --abort 2>/dev/null || true
    git reset --hard origin/main 2>/dev/null || true
  }
  sleep 3
done

echo "::error::推送失败，已重试 3 次"
exit 1
