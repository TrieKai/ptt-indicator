"""從股票版列表頁抓最新文章（站內搜尋會延遲收錄，最新文章以列表頁為準）
用法: python3 -I fetch_ptt_latest.py 頁數 out.json"""
import sys, re, json, time, html, urllib.request
pages, out = int(sys.argv[1]), sys.argv[2]
get = lambda u: urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8")
t = get("https://www.ptt.cc/bbs/Stock/index.html")
last = int(re.search(r'index(\d+)\.html">&lsaquo;', t).group(1)) + 1
rows = []
for n in range(last, last - pages, -1):
    t = t if n == last else get(f"https://www.ptt.cc/bbs/Stock/index{n}.html")
    t = t.split("r-list-sep")[0]
    for e in re.findall(r'<div class="r-ent">(.*?)<div class="mark">', t, re.S):
        m = re.search(r'href="/bbs/Stock/M\.(\d+)\.A\.([0-9A-F]+)\.html">(.*?)</a>', e, re.S)
        if not m: continue
        nr = re.search(r'<div class="nrec">(?:<span[^>]*>)?([^<]*)', e)
        rows.append({"ts": int(m.group(1)), "id": f"M.{m.group(1)}.A.{m.group(2)}", "title": html.unescape(m.group(3).strip()), "nrec": nr.group(1).strip() if nr else ""})
    time.sleep(1)
json.dump(rows, open(out, "w"), ensure_ascii=False)
print("saved", len(rows), "posts from", pages, "pages")
