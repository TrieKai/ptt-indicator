#!/bin/bash
# 在「負責畢業文內文判斷的 Mac」（電腦 C）上執行（可以重複執行）：
#   1. 建立只限這個 repo 的 deploy key（第一次會請你把公鑰貼到 GitHub，要勾 Allow write access）
#   2. 把 repo clone 到 ~/ptt-indicator
#   3. 輸入 Groq 金鑰（畫面不顯示，只存在這台電腦的 ~/.config/ptt-indicator/groq.env，不會進 repo）
#   4. 先判斷幾篇並推上去
#   5. 安裝 launchd 排程，每 30 分鐘自動執行 scripts/analyze_loss.sh
set -euo pipefail
REPO="${REPO:-TrieKai/ptt-indicator}"
DIR="${DIR:-$HOME/ptt-indicator}"
KEY="$HOME/.ssh/ptt_indicator_analyzer"
LABEL="com.ptt-indicator.analyze"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
ENVF="$HOME/.config/ptt-indicator/groq.env"
SSH="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

# 0) 需要 git 與 Python 3（macOS 內建的 Command Line Tools 就有）
if ! /usr/bin/git --version >/dev/null 2>&1 || ! /usr/bin/python3 -c 'import sys; assert sys.version_info >= (3, 8)' >/dev/null 2>&1; then
  echo "需要 git 與 Python 3：請先執行 xcode-select --install，安裝完成後再執行一次這個腳本。"
  exit 1
fi

# 1) deploy key
if [ ! -f "$KEY" ]; then
  mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
  ssh-keygen -t ed25519 -N "" -C "ptt-indicator analyzer $(scutil --get ComputerName 2>/dev/null || hostname)" -f "$KEY" -q
fi
if ! GIT_SSH_COMMAND="$SSH" git ls-remote "git@github.com:$REPO.git" >/dev/null 2>&1; then
  echo
  echo "第一步：把下面這一整行公鑰加到 GitHub（只要做一次）"
  echo "  1. 打開 https://github.com/$REPO/settings/keys/new"
  echo "  2. Title 隨意（例如：電腦 C 內文判斷），Key 貼上下面這行"
  echo "  3. 勾選「Allow write access」，按 Add key"
  echo
  cat "$KEY.pub"
  echo
  echo "加好之後，再執行一次這個腳本。"
  exit 2
fi

# 2) clone
if [ ! -d "$DIR/.git" ]; then
  GIT_SSH_COMMAND="$SSH" git clone -q "git@github.com:$REPO.git" "$DIR"
fi
cd "$DIR"
git config core.sshCommand "$SSH"
git config user.name "ptt-indicator analyzer"
git config user.email "21071329+TrieKai@users.noreply.github.com"
git pull -q --rebase
if ! git push --dry-run -q origin HEAD >/dev/null 2>&1; then
  echo "這把 deploy key 沒有寫入權限：請到 https://github.com/$REPO/settings/keys 刪掉它，重新加入並勾選「Allow write access」。"
  exit 3
fi

# 3) Groq 金鑰（用個人帳號在 https://console.groq.com/keys 建立）
mkdir -p "$(dirname "$ENVF")" && chmod 700 "$(dirname "$ENVF")"
if [ ! -s "$ENVF" ]; then
  echo
  read -rs -p "請貼上 Groq API 金鑰（畫面不會顯示，按 Enter 結束）: " GK; echo
  [ -n "$GK" ] || { echo "沒有輸入金鑰"; exit 4; }
  umask 077; printf 'GROQ_API_KEY=%s\n' "$GK" > "$ENVF"; chmod 600 "$ENVF"; unset GK
fi
if ! /usr/bin/python3 -I - "$ENVF" <<'PY'
import sys, json, urllib.request
k = [l.split("=", 1)[1].strip() for l in open(sys.argv[1]) if l.startswith("GROQ_API_KEY=")][0]
r = urllib.request.urlopen(urllib.request.Request("https://api.groq.com/openai/v1/models", headers={"Authorization": "Bearer " + k, "User-Agent": "ptt-indicator/1"}), timeout=20)
ids = sorted(m["id"] for m in json.loads(r.read())["data"])
print("Groq 金鑰可以用，帳號裡有", len(ids), "個模型")
PY
then
  echo "Groq 金鑰無法使用（可能貼錯或已失效）：已刪除 $ENVF，請重新執行這個腳本再輸入一次。"
  rm -f "$ENVF"; exit 5
fi

# 4) 先跑一次（只判斷 5 篇，確認整條流程能動）
mkdir -p "$DIR/logs"
ANALYZE_MAX=5 bash scripts/analyze_loss.sh

# 5) launchd：每 30 分鐘一次；Mac 睡眠時不會執行，醒來後會補跑
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$DIR/scripts/analyze_loss.sh</string></array>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$DIR/logs/analyze.log</string>
  <key>StandardErrorPath</key><string>$DIR/logs/analyze.log</string>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo
echo "完成：這台 Mac 會每 30 分鐘判斷新的畢業文候選並推上 GitHub（舊文章會分幾天補完）。"
echo "  記錄檔：$DIR/logs/analyze.log"
echo "  停止排程：launchctl bootout gui/$(id -u)/$LABEL"
echo "  換金鑰：刪掉 $ENVF 後重新執行這個腳本"
