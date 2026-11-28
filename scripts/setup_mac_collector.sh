#!/bin/bash
# 在「負責抓 PTT 的 Mac」上執行（可以重複執行）：
#   1. 建立只限這個 repo 的 deploy key（第一次會請你把公鑰貼到 GitHub）
#   2. 把 repo clone 到 ~/ptt-indicator
#   3. 先抓一次 PTT 並推上去
#   4. 安裝 launchd 排程，每 30 分鐘自動執行 scripts/collect_ptt.sh
# 不需要帳號密碼；推送只靠 deploy key，它只能存取這一個 repo。
set -euo pipefail
REPO="${REPO:-TrieKai/ptt-indicator}"
DIR="${DIR:-$HOME/ptt-indicator}"
KEY="$HOME/.ssh/ptt_indicator_deploy"
LABEL="com.ptt-indicator.collect"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
SSH="ssh -i $KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

# 0) 需要 git 與 Python 3（macOS 內建的 Command Line Tools 就有）
if ! /usr/bin/git --version >/dev/null 2>&1 || ! /usr/bin/python3 -c 'import sys; assert sys.version_info >= (3, 8)' >/dev/null 2>&1; then
  echo "需要 git 與 Python 3：請先執行 xcode-select --install，安裝完成後再執行一次這個腳本。"
  exit 1
fi

# 1) deploy key
if [ ! -f "$KEY" ]; then
  mkdir -p "$HOME/.ssh" && chmod 700 "$HOME/.ssh"
  ssh-keygen -t ed25519 -N "" -C "ptt-indicator collector $(scutil --get ComputerName 2>/dev/null || hostname)" -f "$KEY" -q
fi
if ! GIT_SSH_COMMAND="$SSH" git ls-remote "git@github.com:$REPO.git" >/dev/null 2>&1; then
  echo
  echo "第一步：把下面這一整行公鑰加到 GitHub（只要做一次）"
  echo "  1. 打開 https://github.com/$REPO/settings/keys/new"
  echo "  2. Title 隨意（例如：家裡的 Mac），Key 貼上下面這行"
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
git config user.name "ptt-indicator collector"
git config user.email "21071329+TrieKai@users.noreply.github.com"
if ! git push --dry-run -q origin HEAD >/dev/null 2>&1; then
  echo "這把 deploy key 沒有寫入權限：請到 https://github.com/$REPO/settings/keys 刪掉它，重新加入並勾選「Allow write access」。"
  exit 3
fi

# 3) 先跑一次
mkdir -p "$DIR/logs"
bash scripts/collect_ptt.sh

# 4) launchd：每 30 分鐘一次；Mac 睡眠時不會執行，醒來後會補跑
mkdir -p "$HOME/Library/LaunchAgents"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array><string>/bin/bash</string><string>$DIR/scripts/collect_ptt.sh</string></array>
  <key>StartInterval</key><integer>1800</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$DIR/logs/collect.log</string>
  <key>StandardErrorPath</key><string>$DIR/logs/collect.log</string>
</dict>
</plist>
EOF
launchctl bootout "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo
echo "完成：這台 Mac 會每 30 分鐘抓一次 PTT 並推上 GitHub，GitHub 收到後自動更新網站。"
echo "  記錄檔：$DIR/logs/collect.log"
echo "  停止排程：launchctl bootout gui/$(id -u)/$LABEL"
