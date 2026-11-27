#!/bin/bash
# 平日收盤後（台灣 15:35–19:00），列出還沒有今天資料的收盤資料檔；沒缺或不在時段內就什麼都不印。
# GitHub 的收盤排程常延遲或被跳過，所以負責抓 PTT 的電腦每 15 分鐘推文章時，部署前先用這支檢查，缺就順便完整更新。
# 違約公告是成交日後第 2 個營業日才公布、融資晚上才公布，不在檢查範圍。測試用：NOW_U（1–7）、NOW_HM（例如 1540）、TODAY（YYYY-MM-DD）。
export TZ=Asia/Taipei
D="${1:-data}"
U="${NOW_U:-$(date +%u)}"; HM="${NOW_HM:-$(date +%H%M)}"; T="${TODAY:-$(date +%F)}"
[ "$U" -le 5 ] && [ "$((10#$HM))" -ge 1535 ] && [ "$((10#$HM))" -lt 1900 ] || exit 0
miss=""
for f in taiex tpex taifex_pc foreign_inst turnover futures_foreign; do
  [ "$(tail -n 1 "$D/$f.csv" 2>/dev/null | cut -d, -f1)" = "$T" ] || miss="$miss $f"
done
echo "${miss# }"
