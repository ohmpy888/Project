# -*- coding: utf-8 -*-
import re
from typing import List, Dict, Any, Tuple

SAFE_DOMAIN_HINTS = (
  "bbc.", "reuters.", "apnews.", "nytimes.", "washingtonpost.", "theguardian.",
  "bangkokpost.", "thairath.", "matichon.", "mgronline.", "posttoday.", "prachatai."
)
CLICKBAIT_WORDS_TH = r"(ด่วน|ช็อก|โคตร|ฟรี|แจกเงิน|วันนี้เท่านั้น|ห้ามพลาด)"
EMO_PUNCT = r"!!!+|\?\?+"

def extract_signals(news_text: str, user_reasoning: str, urls: List[str] | None):
  tokens_news = re.findall(r"\w+|\S", news_text.lower())
  tokens_user = re.findall(r"\w+|\S", (user_reasoning or "").lower())
  has_number_in_news = bool(re.search(r"\b\d{1,3}(?:[.,]\d{3})+|\b\d+%?\b", news_text))
  has_clickbait = bool(re.search(CLICKBAIT_WORDS_TH, news_text)) or bool(re.search(EMO_PUNCT, news_text))
  mentions_date_user = bool(re.search(r"\b\d{1,2}/\d{1,2}(/\d{2,4})?|\b\d{4}\b|วันที่|อัปเดต|update", user_reasoning or "", re.IGNORECASE))
  has_source_word = bool(re.search(r"(อ้างอิง|ที่มา|source|อ้างถึง|ประกาศ)", user_reasoning or "", re.IGNORECASE))
  url_list = urls or []
  return {
    "tokens_news": tokens_news,
    "tokens_user": tokens_user,
    "has_number_in_news": has_number_in_news,
    "has_clickbait": has_clickbait,
    "mentions_date_user": mentions_date_user,
    "has_source_word": has_source_word,
    "urls": url_list
  }

def domain_trust(url: str) -> str:
  url_low = url.lower()
  if any(h in url_low for h in SAFE_DOMAIN_HINTS):
    return "trusted"
  if re.search(r"\.(blogspot|wordpress|medium)\.", url_low) or re.search(r"t\.me/|line\.me/", url_low):
    return "weak"
  return "unknown"

def run_logic_flags(signals: Dict[str, Any], overlap_ratio: float, user_label: int | None, model_label: int):
  flags: List[Dict[str, str]] = []

  # แหล่งอ้างอิง
  if not signals["urls"] and not signals["has_source_word"]:
    flags.append({"code": "SRC_MISSING", "reason": "ไม่พบลิงก์หรือคำว่าอ้างอิง/ที่มาในเหตุผล"})
  else:
    trusts = [domain_trust(u) for u in signals["urls"]]
    if trusts and all(t != "trusted" for t in trusts):
      flags.append({"code": "SRC_WEAK_DOMAIN", "reason": "โดเมนอ้างอิงไม่น่าเชื่อถือ หรือไม่มีแหล่งทางการ"})

  # วันที่/เวลา
  if not signals["mentions_date_user"]:
    flags.append({"code": "DATE_MISSING", "reason": "เหตุผลไม่ระบุวันที่/ช่วงเวลา"})

  # ตัวเลขในข่าว
  if signals["has_number_in_news"] and not (signals["urls"] or signals["has_source_word"]):
    flags.append({"code": "NUM_UNJUSTIFIED", "reason": "ข่าวมีตัวเลข แต่เหตุผลไม่มีที่มารองรับ"})

  # ภาษาอารมณ์/คลิกเบait
  if signals["has_clickbait"]:
    flags.append({"code": "EMO_LANGUAGE", "reason": "ข่าวมีถ้อยคำ/เครื่องหมายกระตุ้นอารมณ์"})

  # แก่นเหตุผลไม่เข้าเป้า (ใช้ overlap คร่าวๆ)
  if overlap_ratio < 0.2:
    flags.append({"code": "MISMATCH_CORE", "reason": "เหตุผลยังไม่แตะประเด็นที่สำคัญของข่าว"})

  # ผู้ใช้ vs โมเดล (ถ้าให้มา)
  if user_label is not None and int(user_label) != int(model_label):
    flags.append({"code": "USER_MODEL_MISMATCH", "reason": "คำตอบของผู้ใช้ต่างจากโมเดล"})

  return flags

SUGGESTION_MAP = {
  "SRC_MISSING": "เพิ่มลิงก์อย่างน้อย 2 แหล่ง (สำนักข่าวหลัก + แหล่งทางการ/หน่วยงานรัฐ)",
  "SRC_WEAK_DOMAIN": "ใช้แหล่งที่มาจากโดเมนที่น่าเชื่อถือ (เช่น สำนักข่าวหลัก/ประกาศหน่วยงานรัฐ)",
  "DATE_MISSING": "ระบุวันที่/ช่วงเวลาเพื่อกันข้อมูลเก่าและตรวจสอบว่าอัปเดตล่าสุด",
  "NUM_UNJUSTIFIED": "ตรวจที่มาของตัวเลข/เปอร์เซ็นต์จากเอกสารประกาศหรือรายงานทางการ",
  "EMO_LANGUAGE": "ระวังถ้อยคำชวนเชื่อ/เครื่องหมายตกใจ—ตรวจสาระสำคัญแทนความเร้าอารมณ์",
  "MISMATCH_CORE": "ผูกเหตุผลกับประเด็นหลักของข่าว เช่น entity/คำสำคัญที่ปรากฏชัด",
  "USER_MODEL_MISMATCH": "ลองอ่านคำชี้แนะ/คำสำคัญของโมเดล แล้วทบทวนเหตุผลอีกครั้ง",
}

def build_suggestions(flags: List[Dict[str, str]]) -> List[Dict[str, Any]]:
  # เรียงความสำคัญง่าย ๆ: แหล่งอ้างอิง > วันที่ > mismatch_core > ตัวเลข > อื่นๆ
  priority = {"SRC_MISSING":1, "SRC_WEAK_DOMAIN":2, "DATE_MISSING":3, "MISMATCH_CORE":4, "NUM_UNJUSTIFIED":5, "EMO_LANGUAGE":6, "USER_MODEL_MISMATCH":7}
  items = []
  seen = set()
  for f in sorted(flags, key=lambda x: priority.get(x["code"], 99)):
    code = f["code"]
    if code in seen: continue
    seen.add(code)
    items.append({"id": f"S_{code}", "text": SUGGESTION_MAP.get(code, ""), "from_flags": [code]})
  return items

def lexical_overlap(a: str, b_terms: List[str]) -> float:
  # overlap แบบง่าย: สัดส่วนคำซ้ำ
  import string
  tbl = str.maketrans("", "", string.punctuation)
  a_tokens = set(a.lower().translate(tbl).split())
  b_tokens = set([t.lower().translate(tbl) for t in b_terms if t.strip()])
  if not a_tokens or not b_tokens: return 0.0
  inter = len(a_tokens & b_tokens)
  return inter / max(1, len(a_tokens | b_tokens))

def compare_reasoning(user_reasoning: str, model_clue_terms: List[str], key_entities: List[str]) -> Tuple[str, float]:
  # รวม ref terms = clues + entities
  ref = list(set(model_clue_terms + key_entities))
  ov = lexical_overlap(user_reasoning or "", ref)
  if ov >= 0.5: level = "good"
  elif ov >= 0.2: level = "partial"
  else: level = "low"
  return level, ov