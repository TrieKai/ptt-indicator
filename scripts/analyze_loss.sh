#!/bin/bash
# 負責「畢業文內文判斷」的電腦執行（Mac 由 launchd 每 30 分鐘呼叫）：
# 拉最新的 PTT 標題 → 找還沒判斷的畢業文候選 → 讀內文送 Groq → 存進 data/loss_labels.json → commit → push。
# 推上去不會觸發網站重算（第一階段只存結果、不影響分數）。
set -euo pipefail
cd "$(dirname "$0")/.."
export TZ=Asia/Taipei
PY="${PYTHON:-/usr/bin/python3}"
MAX="${ANALYZE_MAX:-20}"            # 一輪最多判斷幾篇；免費額度有每日上限，舊文章會分好幾天補完

echo "=== $(date '+%Y-%m-%d %H:%M:%S')"
git pull -q --rebase
"$PY" -I scripts/analyze_loss_groq.py data --max "$MAX"
[ -f data/loss_labels.json ] && git add data/loss_labels.json
if git diff --cached --quiet; then
  echo "沒有新的判斷結果"
  exit 0
fi
git commit -q -m "畢業文內文判斷 $(date '+%Y-%m-%d %H:%M')"
git push -q || { git pull -q --rebase && git push -q; }
echo "已推上 GitHub"
