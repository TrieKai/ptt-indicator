#!/bin/bash
# 換模型試跑：用同一套提示詞判斷對照樣本（data/loss_overlap.json），結果另存在 data/model_trials/，不影響網站分數。
# 在有 Groq 金鑰的電腦執行：bash scripts/try_model.sh qwen/qwen3.8-27b
# 每分鐘額度到了會自動等；每日額度用完會先停，之後再執行同一行會從沒判斷的接著跑。
main() {
  set -euo pipefail
  cd "$(dirname "$0")/.."
  export TZ=Asia/Taipei
  local PY="${PYTHON:-/usr/bin/python3}"
  local MODEL="${1:?請給模型名稱，例如 bash scripts/try_model.sh qwen/qwen3.8-27b}"
  local OUT="data/model_trials/$(printf '%s' "$MODEL" | tr '/:' '__').json"
  mkdir -p data/model_trials
  git pull -q --rebase --autostash
  GROQ_MODEL="$MODEL" "$PY" -I scripts/analyze_loss_groq.py data --overlap-only --out "$OUT" --max "${ANALYZE_MAX:-200}"
  [ -f "$OUT" ] || { echo "沒有產生結果"; return 1; }
  git add "$OUT"
  if git diff --cached --quiet; then echo "沒有新的判斷結果"; return 0; fi
  git commit -q -m "模型試跑 $MODEL $(date '+%Y-%m-%d %H:%M')"
  git push -q || { git pull -q --rebase --autostash && git push -q; }
  echo "已推上 GitHub：$OUT"
}
# 整個檔案先讀完再執行：git pull 更新這支腳本時，不會讀到一半的新內容
main "$@"; exit
