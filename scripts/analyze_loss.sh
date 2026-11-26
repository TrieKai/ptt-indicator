#!/bin/bash
# 負責「畢業文內文判斷」的電腦執行（Mac 由 launchd 每 30 分鐘呼叫）：
# 拉最新的 PTT 標題 → 找還沒判斷的畢業文候選 → 讀內文送 Groq → 存進 data/loss_labels.json → commit → push。
# 推上去不會觸發網站重算（第一階段只存結果、不影響分數）。
# 想一次多補一些舊文章：ANALYZE_MAX=200 bash scripts/analyze_loss.sh（會跑到當天免費額度用完為止）
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export TZ=Asia/Taipei
  local PY="${PYTHON:-/usr/bin/python3}"
  local MAX="${ANALYZE_MAX:-20}"     # 一輪最多判斷幾篇；免費額度有每日上限，舊文章會分好幾天補完
  local LOCK="${TMPDIR:-/tmp}/ptt-indicator-analyze.lock"

  echo "=== $(date '+%Y-%m-%d %H:%M:%S')"
  if ! mkdir "$LOCK" 2>/dev/null; then   # 排程和手動補跑不要同時跑
    if [ -n "$(find "$LOCK" -maxdepth 0 -mmin +180 2>/dev/null)" ]; then rmdir "$LOCK"; mkdir "$LOCK"; else echo "上一輪還在跑，這一輪略過"; return 0; fi
  fi
  trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT

  git pull -q --rebase
  "$PY" -I scripts/analyze_loss_groq.py data --max "$MAX"
  [ -f data/loss_labels.json ] && git add data/loss_labels.json
  if git diff --cached --quiet; then
    echo "沒有新的判斷結果"
    return 0
  fi
  git commit -q -m "畢業文內文判斷 $(date '+%Y-%m-%d %H:%M')"
  git push -q || { git pull -q --rebase && git push -q; }
  echo "已推上 GitHub"
}
# 整個檔案先讀完再執行：git pull 更新這支腳本時，不會讀到一半的新內容
main "$@"; exit
