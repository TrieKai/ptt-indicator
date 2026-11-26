"""用 PTT 網頁版站內搜尋抓股票版標題（只比對標題），存成 JSON: ts, id, title, nrec"""
import sys, re, json, time, html, urllib.request, urllib.parse, urllib.error

q, max_pages, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
rows = []
for p in range(1, max_pages + 1):
    url = f"https://www.ptt.cc/bbs/Stock/search?page={p}&q={urllib.parse.quote(q)}"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20) as r:
            t = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        if e.code == 404: print("no more pages at", p); break
        print("error at page", p, e); time.sleep(10); continue
    ents = re.findall(r'<div class="r-ent">(.*?)<div class="mark">', t, re.S)
    if not ents: break
    for e in ents:
        m = re.search(r'href="/bbs/Stock/M\.(\d+)\.A\.([0-9A-F]+)\.html">(.*?)</a>', e, re.S)
        if not m: continue
        n = re.search(r'<div class="nrec">(?:<span[^>]*>)?([^<]*)', e)
        rows.append({"ts": int(m.group(1)), "id": f"M.{m.group(1)}.A.{m.group(2)}",
                     "title": html.unescape(m.group(3).strip()), "nrec": n.group(1).strip() if n else ""})
    if p % 20 == 0: print("page", p, "rows", len(rows), flush=True)
    time.sleep(1)
json.dump(rows, open(out, "w"), ensure_ascii=False)
print(q, "saved", len(rows), "rows")
