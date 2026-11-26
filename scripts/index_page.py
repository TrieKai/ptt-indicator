"""讀股票版某一頁列表，回傳：該頁文章的日期範圍、墓碑列（被刪文章）數量與條號"""
import re, html, time, datetime as dt, urllib.request
TZ = dt.timezone(dt.timedelta(hours=8))
def fetch(n, retries=4):
    url = f"https://www.ptt.cc/bbs/Stock/index{n}.html"
    for i in range(retries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
                t = r.read().decode("utf-8")
            break
        except Exception:
            if i == retries - 1: raise
            time.sleep(5 * (i + 1))                      # Cloudflare 5xx／限流時退避
    t = t.split('r-list-sep')[0]                         # 去掉置底文
    out = []
    for e in re.findall(r'<div class="r-ent">(.*?)<div class="mark">', t, re.S):
        title = re.search(r'<div class="title">(.*?)</div>', e, re.S).group(1)
        date = re.search(r'<div class="date">\s*([^<]*?)\s*</div>', e).group(1)
        m = re.search(r'/bbs/Stock/M\.(\d+)\.A\.', title)
        if m:
            out.append({"ts": int(m.group(1)), "date": date, "deleted": None})
        else:
            txt = html.unescape(re.sub(r'\s+', ' ', title)).strip()
            kind = "mod" if "已被移除" in txt else ("self" if "已被刪除" in txt else "other")
            rule = txt.split(":", 1)[1].strip() if kind == "mod" and ":" in txt else ""
            out.append({"ts": None, "date": date, "deleted": kind, "rule": rule})
    return out
