"""PTT 畢業文候選與內文讀取（Groq 分析與實驗共用）。

候選 = 標題規則保留的畢業文原文（loss_rules.py）＋ 標題含畢業類關鍵字的 Re:／Fw: 回文（回覆新聞、情報、公告的除外）。
「作者自己寫的部分」= 拿掉作者／時間等標頭、引用原文的行（": " 開頭、※ 引述）、推文與簽名檔之後的內文。
PTT 會擋雲端主機，讀內文要在一般網路的電腦上跑；呼叫端自己控制速度（每秒 1 篇）。
"""
import os, re, json, glob, html, time, urllib.request, urllib.error
from loss_rules import classify, SKIP_CAT, CAT

KEYS = ["畢業", "賠光", "歸零", "爆倉", "違約交割", "斷頭", "追繳"]
REPLY = re.compile(r"(Re|RE|Fw|FW)\s*:")
IMG = re.compile(r"https?://(?:i\.)?imgur\.com/\S+|https?://\S+\.(?:jpe?g|png|gif|webp)\b|https?://(?:i\.ibb\.co|ibb\.co|postimg\.cc|i\.postimg\.cc|"
                 r"pbs\.twimg\.com|lh\d\.googleusercontent\.com|photos\.app\.goo\.gl|flic\.kr|www\.flickr\.com|meee\.com\.tw|i\.meee\.com\.tw)/\S+", re.I)
SHORT_LINK = re.compile(r"https?://(?:lurl\.cc|ppt\.cc|reurl\.cc|bit\.ly|tinyurl\.com|pse\.is)/\S+", re.I)
LINK = re.compile(r"https?://\S+")
NUM = [
    re.compile(r"[-−－]\s?\d[\d,\.]*\s?(?:萬|w|W|k|K|元|%|％|億)"),
    re.compile(r"(?:賠|虧|損失|輸|燒|蒸發|噴)[^\d\n]{0,8}?\d[\d,\.]*\s?(?:萬|w|W|k|K|元|%|％|億)"),
    re.compile(r"(?:損益|未實現|已實現|報酬率|虧損|淨值)[^\d\n]{0,6}[-−－]?\s?\d[\d,\.]*\s?(?:萬|w|W|元|%|％)"),
    re.compile(r"\d[\d,\.]*\s?(?:萬|w|W)\s?(?:本金|全部|歸零|賠光|沒了|剩)"),
    re.compile(r"(?:斷頭|追繳)通知|維持率\s?\d"),
    re.compile(r"(?:賠|虧|損失|輸|燒|蒸發)[^\n]{0,8}?[一二兩三四五六七八九十百千]+\s?(?:萬|億|成)"),
    re.compile(r"(?:虧損|損失|賠|輸)[了掉]?\s?\d[\d,]{4,}"),
    re.compile(r"[一二兩三四五六七八九十百千]+\s?萬\s?(?:本金|全部|歸零|賠光|沒了|剩)"),
]
FIRST = re.compile(r"我|小弟|小妹|本人|自己|偶|俺")


def load_posts(D):
    """跟 build_dashboard_data.py 讀同一批 PTT 標題資料。"""
    seen = {}
    for f in [f"{D}/graduation_search.json", f"{D}/creative_search.json"] + glob.glob(f"{D}/kw_*.json") + glob.glob(f"{D}/greed_*.json") + glob.glob(f"{D}/ptt_latest.json"):
        if os.path.exists(f):
            for p in json.load(open(f, encoding="utf-8")): seen[p["id"]] = p
    return seen


def candidates(seen):
    """回傳 [(post, 'orig'|'reply')]，新到舊排序。"""
    out = []
    for p in seen.values():
        t = p["title"]
        if REPLY.match(t):
            # 回文：標題有關鍵字，而且不是回覆新聞、情報、公告（原文的這些分類本來就排除）
            if any(k in t for k in KEYS) and CAT(REPLY.sub("", t, count=1).strip()) not in SKIP_CAT: out.append((p, "reply"))
        elif classify(t)[0]:
            out.append((p, "orig"))
    out.sort(key=lambda x: -x[0]["ts"])
    return out


def own_text(page):
    m = re.search(r'<div id="main-content"[^>]*>(.*?)<div id="article-polling"', page, re.S) or re.search(r'<div id="main-content"[^>]*>(.*)', page, re.S)
    if not m: return None
    body = m.group(1)
    body = re.sub(r'<div class="article-metaline(?:-right)?">.*?</div>', "", body, flags=re.S)
    body = re.sub(r'<div class="push">.*?</div>', "", body, flags=re.S)
    body = re.sub(r"<a [^>]*>(.*?)</a>", r"\1", body, flags=re.S)
    body = re.sub(r'<div class="richcontent">.*?</div>', "", body, flags=re.S)
    text = html.unescape(re.sub(r"<[^>]+>", "", body))
    text = re.split(r"\n--\n※ 發信站|\n※ 發信站", text)[0]
    own = []
    for ln in text.split("\n"):
        s = ln.strip()
        if s.startswith((":", "：")) or s.startswith(("※ 引述", "※ 文章網址", "※ 編輯")): continue
        own.append(ln)
    return "\n".join(own).strip()


def hints(own, title=""):
    """規則找到的線索：圖片連結、短網址、金額片段、第一人稱。給模型參考，也用來跟模型比對。"""
    imgs = IMG.findall(own)
    shorts = SHORT_LINK.findall(own)
    hosts = sorted({re.sub(r"https?://([^/]+)/.*", r"\1", u) for u in LINK.findall(own)})
    nums = []
    for rx in NUM:
        for m in rx.finditer(own + "\n" + title): nums.append(m.group(0))
    return {"img": len(imgs), "short_links": len(shorts), "hosts": hosts[:6], "nums": list(dict.fromkeys(nums))[:5], "first": bool(FIRST.search(own)), "own_len": len(own)}


def fetch(post_id):
    """讀一篇文章；回傳 (status, own_text)。status: ok / deleted / http NNN / error X。Cloudflare 偶爾回 5xx，等一下再試。"""
    url = f"https://www.ptt.cc/bbs/Stock/{post_id}.html"
    for i in range(3):
        try:
            page = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8", "replace")
            if "本網頁已被刪除" in page: return "deleted", None
            own = own_text(page)
            return ("ok", own) if own is not None else ("deleted", None)
        except urllib.error.HTTPError as e:
            if e.code == 404: return "deleted", None
            if e.code < 500 or i == 2: return f"http {e.code}", None
        except Exception as e:
            if i == 2: return "error " + type(e).__name__, None
        time.sleep(5 * (i + 1))
