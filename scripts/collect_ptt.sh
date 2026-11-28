#!/bin/bash
# 負責抓 PTT 的電腦執行（Mac 由 launchd 在每小時 00 分、30 分呼叫）：
# 抓 PTT 最新文章 → 併進 data/ptt_latest.json →（有 Groq 金鑰時）判斷新的畢業文候選內文 → commit → push。
# GitHub 收到後會自動重算並更新網站。PTT 會擋雲端主機，所以這一段要在一般網路（家用、公司）上的電腦跑。
# Groq 金鑰放在 ~/.config/ptt-indicator/groq.env（GROQ_API_KEY=...，不進 repo）；沒有金鑰就只抓文章。
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export TZ=Asia/Taipei
  export PTT_PAGES="${PTT_PAGES:-20}"         # 往回抓幾頁列表（每頁約 16–20 篇）；電腦睡過一陣子也補得回來
  local PY="${PYTHON:-/usr/bin/python3}"

  echo "=== $(date '+%Y-%m-%d %H:%M:%S')"
  git pull -q --rebase --autostash
  "$PY" -I scripts/update_data.py data dashboard/data --only ptt --no-build

  # 畢業文內文判斷：新文章優先，一輪最多 ANALYZE_MAX 篇；失敗或額度用完都不影響抓文章，下一輪再補
  if [ -s "$HOME/.config/ptt-indicator/groq.env" ] || [ -n "${GROQ_API_KEY:-}" ]; then
    "$PY" -I scripts/analyze_loss_groq.py data --max "${ANALYZE_MAX:-10}" || echo "畢業文判斷這一輪沒完成，下一輪再試"
  fi

  git add data/ptt_latest.json
  [ -f data/loss_labels.json ] && git add data/loss_labels.json
  if git diff --cached --quiet; then
    echo "沒有新文章"
    return 0
  fi
  git commit -q -m "PTT 文章更新 $(date '+%Y-%m-%d %H:%M')"
  git push -q || { git pull -q --rebase --autostash && git push -q; }
  echo "已推上 GitHub"
}
# 整個檔案先讀完再執行：git pull 更新這支腳本時，不會讀到一半的新內容
main "$@"; exit
