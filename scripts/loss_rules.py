"""PTT「多方畢業／虧損文」分類規則（只看標題）
目的：只留下「鄉民自己做多賠錢、認賠出場」的文章。
排除：問句與討論畢業文本身、講市場機制的斷頭／違約、空軍畢業（放空在上漲時賠光，方向相反）、
      債券／學校／出金等不相關、新聞等分類。回傳 (是否保留, 原因)。"""
import re
CAT = lambda t: (re.match(r"[\[［]([^\]］}]+)[\]］}]", t) or [None, ""])[1]
KEYS = ["畢業", "賠光", "歸零", "爆倉", "違約交割", "斷頭", "追繳"]
SKIP_CAT = {"新聞", "情報", "公告", "創作", "活動"}
QUESTION = re.compile(r"[?？]|嗎|呢|是不是|會不會|有沒有|有人|多少|為何|為什麼|為啥|怎麼|如何|怎辦|定義|484|可行|重要性|嚴重性|勸世|"
                      r"不是畢業|太少|這麼少|還沒出來|看出|一堆|誰|大家|畢業文永遠|關於畢業文|最容易|是否")
SHORT = re.compile(r"空軍|空單|做空|放空|傻空|雜空|嘎空|豆腐軍|台指.*空$|\s空$")
UNRELATED = re.compile(r"債蛙|美債|TLT|TMF|長天期|復出|分割|董事長|紀錄|典禮|大學|大葉|新鮮人|課表|行事曆|就業|研究所|畢業生|出金|手續費|人生|財富自由|退休|想畢業|準備畢業台指")
PERSONAL = re.compile(r"我|自己|小弟|小妹|本人|被|差點|親身|積蓄|存款|了|啦|囉|嘍|惹|-\d|\d+[wW萬]")
def classify(title):
    t = title.strip()
    if re.match(r"(Re|RE|Fw|FW)\s*:", t): return False, "回文"
    k = next((k for k in KEYS if k in t), None)
    if not k: return False, "沒有關鍵字"
    if CAT(t) in SKIP_CAT: return False, f"分類 [{CAT(t)}]"
    if UNRELATED.search(t): return False, "不相關（債券、學校、人生畢業等）"
    if SHORT.search(t): return False, "空軍畢業（方向相反）"
    if QUESTION.search(t): return False, "問句或討論畢業文本身"
    body = re.sub(r"^[\[［][^\]］}]+[\]］}]\s*", "", t)          # 拿掉分類標籤再判斷
    if k != "畢業" and not PERSONAL.search(body): return False, f"「{k}」在講市場或個股，不是自己"
    return True, "保留"
