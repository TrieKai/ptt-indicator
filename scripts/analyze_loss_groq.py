"""用 Groq 判斷畢業文候選的內文：是不是作者本人做多賠錢、有沒有依據（截圖或具體虧損金額）。
結果存在 data/loss_labels.json（每篇文章只判斷一次）。第一階段只存結果、不影響分數。

用法: python3 -I scripts/analyze_loss_groq.py data [--max N] [--dry-run] [--ids id1,id2]
  --max N     這一輪最多判斷幾篇（預設 20；免費額度有每日 token 上限，舊文章會分好幾天補完）
  --dry-run   不呼叫 Groq，只印出要送的內容（測試用）
金鑰：環境變數 GROQ_API_KEY，或 ~/.config/ptt-indicator/groq.env 裡的 GROQ_API_KEY=...（不要放進 repo）
模型：環境變數 GROQ_MODEL；沒有設定時從 PREFER 依序挑帳號裡有的第一個，並記在每筆結果裡。
新文章優先；遇到 429（額度用完）就停，下一輪再繼續。PTT 會擋雲端主機，要在一般網路的電腦上跑。
"""
import sys, os, re, json, time, argparse, datetime as dt, urllib.request, urllib.error
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ptt_content import load_posts, candidates, fetch, hints

PROMPT_VERSION = "loss-v1"
PREFER = ["qwen/qwen3.6-27b", "moonshotai/kimi-k2-instruct-0905", "openai/gpt-oss-120b", "llama-3.3-70b-versatile"]
API = "https://api.groq.com/openai/v1"
MAX_CHARS = 1800
TZ = dt.timezone(dt.timedelta(hours=8))

SYSTEM = """你是資料標註員，幫忙判斷 PTT 股票版的文章。只根據提供的內容判斷，不要猜測，不確定就降低 confidence。
「畢業文」在這裡的定義：作者本人做多（買進股票、ETF、期貨多單、權證或選擇權買方等）之後認賠出場，或帳戶出現重大虧損（例如斷頭、追繳、歸零、賠光、大幅虧損）。
不算的情況：討論或提問、新聞或轉述別人的虧損、假設語氣（如果賠了…）、差點出事但沒有發生、已經賺回來、純心得檢討但沒說自己賠多少、放空賠錢（方向相反）。
依據：內文附圖片連結（多半是對帳單或庫存截圖，視為 screenshot），或寫出具體的虧損金額或比例（視為 amount）。
只輸出一個 JSON 物件，欄位如下：
{"own_loss": true 或 false, "side": "long" 或 "short" 或 "unknown", "evidence": "screenshot" 或 "amount" 或 "both" 或 "none", "amount": "虧損金額或比例的原文，沒有就空字串", "confidence": 0 到 1 的數字, "reason": "30 字內的理由"}"""

def user_msg(post, kind, own, h):
    t = own if len(own) <= MAX_CHARS else own[:MAX_CHARS] + "…（以下省略）"
    return (f"標題：{post['title']}\n"
            f"類型：{'原文' if kind == 'orig' else '回文（只看回文者自己寫的部分，引用原文已去掉）'}\n"
            f"內文中的連結網域：{', '.join(h['hosts']) or '無'}\n"
            f"程式找到的金額片段（僅供參考，可能有誤）：{'、'.join(h['nums']) or '無'}\n"
            f"作者自己寫的內文：\n\"\"\"\n{t}\n\"\"\"")

def key():
    k = os.environ.get("GROQ_API_KEY")
    if k: return k
    f = os.path.expanduser("~/.config/ptt-indicator/groq.env")
    if os.path.exists(f):
        for ln in open(f, encoding="utf-8"):
            if ln.startswith("GROQ_API_KEY="): return ln.split("=", 1)[1].strip()
    sys.exit("找不到 Groq 金鑰：請設定環境變數 GROQ_API_KEY，或寫在 ~/.config/ptt-indicator/groq.env")

class RateLimited(Exception): pass

def call(path, k, body=None):
    req = urllib.request.Request(API + path, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": "Bearer " + k, "Content-Type": "application/json", "User-Agent": "ptt-indicator/1"})
    try:
        return json.loads(urllib.request.urlopen(req, timeout=60).read().decode())
    except urllib.error.HTTPError as e:
        msg = e.read().decode("utf-8", "replace")[:300]
        if e.code == 429: raise RateLimited(msg)
        raise RuntimeError(f"Groq HTTP {e.code}: {msg}")

def pick_model(k):
    m = os.environ.get("GROQ_MODEL")
    if m: return m
    have = {x["id"] for x in call("/models", k).get("data", [])}
    for p in PREFER:
        if p in have: return p
    sys.exit("帳號裡沒有預設的模型，請用 GROQ_MODEL 指定（可用的模型：" + ", ".join(sorted(have)[:12]) + "…）")

def judge(k, model, post, kind, own, h):
    body = {"model": model, "temperature": 0, "max_tokens": 300, "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user_msg(post, kind, own, h)}],
            "response_format": {"type": "json_object"}}
    try:
        r = call("/chat/completions", k, body)
    except RuntimeError as e:
        if "response_format" not in str(e) and "json" not in str(e).lower(): raise
        body.pop("response_format"); r = call("/chat/completions", k, body)   # 有些模型不支援 JSON 模式
    txt = r["choices"][0]["message"]["content"]
    m = re.search(r"\{.*\}", txt, re.S)
    out = json.loads(m.group(0) if m else txt)
    ev = out.get("evidence") if out.get("evidence") in ("screenshot", "amount", "both", "none") else "none"
    side = out.get("side") if out.get("side") in ("long", "short", "unknown") else "unknown"
    return {"own_loss": bool(out.get("own_loss")), "side": side, "evidence": ev, "amount": str(out.get("amount") or "")[:40],
            "confidence": round(float(out.get("confidence") or 0), 2), "reason": str(out.get("reason") or "")[:60],
            "tokens": (r.get("usage") or {}).get("total_tokens")}

def counts(lab):
    """算進畢業文的條件：作者本人、不是放空、有依據。"""
    return lab.get("status") == "ok" and lab.get("own_loss") and lab.get("side") != "short" and lab.get("evidence") != "none"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("data"); ap.add_argument("--max", type=int, default=20); ap.add_argument("--dry-run", action="store_true"); ap.add_argument("--ids", default="")
    a = ap.parse_args()
    out_path = os.path.join(a.data, "loss_labels.json")
    labels = json.load(open(out_path, encoding="utf-8")) if os.path.exists(out_path) else {}
    cands = candidates(load_posts(a.data))
    if a.ids: cands = [c for c in cands if c[0]["id"] in set(a.ids.split(","))]
    todo = [(p, kind) for p, kind in cands if p["id"] not in labels or labels[p["id"]].get("prompt_version") != PROMPT_VERSION]
    print(f"候選 {len(cands)} 篇，已判斷 {len(cands) - len(todo)} 篇，這一輪最多判斷 {min(a.max, len(todo))} 篇", flush=True)
    k = None if a.dry_run else key()
    model = "dry-run" if a.dry_run else pick_model(k)
    done = 0
    for p, kind in todo[:a.max]:
        status, own = fetch(p["id"]); time.sleep(1)
        lab = {"id": p["id"], "ts": p["ts"], "title": p["title"], "kind": kind, "status": status, "model": model, "prompt_version": PROMPT_VERSION,
               "labeled_at": dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M")}
        if status == "ok":
            h = hints(own, p["title"]); lab["hints"] = h
            if a.dry_run:
                print("—" * 20, "\n", user_msg(p, kind, own, h)[:600]); continue
            try:
                lab.update(judge(k, model, p, kind, own, h))
            except RateLimited as e:
                print("Groq 額度用完，下一輪再繼續：", e, flush=True); break
            except Exception as e:
                print("判斷失敗，下一輪再試：", p["id"], type(e).__name__, str(e)[:160], flush=True); continue
            lab["counts"] = bool(counts(lab))
        elif status.startswith(("http", "error")):
            print("讀不到文章，下一輪再試：", p["id"], status, flush=True); continue
        labels[p["id"]] = lab; done += 1
        tmp = out_path + ".tmp"; json.dump(labels, open(tmp, "w", encoding="utf-8"), ensure_ascii=False, indent=0, sort_keys=True); os.replace(tmp, out_path)
        print(f"{done}. {p['title'][:30]} → {'算' if lab.get('counts') else '不算'}（{lab.get('evidence', lab['status'])}，{lab.get('reason', '')}）", flush=True)
    left = len(todo) - done
    print(f"這一輪判斷 {done} 篇，還有 {left} 篇", flush=True)

if __name__ == "__main__":
    main()
