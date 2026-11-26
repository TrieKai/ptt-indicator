#!/bin/bash
# 負責抓 PTT 的電腦執行（Mac 由 launchd 每 15 分鐘呼叫）：
# 抓 PTT 最新文章 → 併進 data/ptt_latest.json → commit → push。GitHub 收到後會自動重算並更新網站。
# PTT 會擋雲端主機，所以這一段要在一般網路（家用、公司）上的電腦跑。
set -euo pipefail
cd "$(dirname "$0")/.."
export TZ=Asia/Taipei
export PTT_PAGES="${PTT_PAGES:-20}"          # 往回抓幾頁列表（每頁約 16–20 篇）；電腦睡過一陣子也補得回來
PY="${PYTHON:-/usr/bin/python3}"

echo "=== $(date '+%Y-%m-%d %H:%M:%S')"
git pull -q --rebase
"$PY" -I scripts/update_data.py data dashboard/data --only ptt --no-build
git add data/ptt_latest.json
if git diff --cached --quiet; then
  echo "沒有新文章"
  exit 0
fi
git commit -q -m "PTT 文章更新 $(date '+%Y-%m-%d %H:%M')"
git push -q || { git pull -q --rebase && git push -q; }
echo "已推上 GitHub"
