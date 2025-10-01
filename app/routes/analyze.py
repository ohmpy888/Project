# app/routes/analyze.py (ฉบับแก้ไข)
from fastapi import APIRouter, HTTPException
from app.schemas import AnalyzeIn, AnalyzeOut
from app.services.model import get_predictor
from app.services.db import get_news_text_by_id # ⬅️ ใช้ชื่อเดิมที่แก้แล้ว
from inference.flags_and_suggestions import (
    extract_signals, run_logic_flags, build_suggestions, compare_reasoning
)

router = APIRouter()

def band_from_proba(p: float, t: float) -> str:
    d = abs(p - t)
    if d >= 0.35: return "high"
    if d >= 0.15: return "medium"
    return "low"

@router.post("/analyze", response_model=AnalyzeOut)
def analyze(inp: AnalyzeIn):
    # 1) หา text ข่าว
    news_text = None
    if inp.text and inp.text.strip():
        news_text = inp.text
    elif inp.news_id:
        try:
            # ⚠️ เรียก DB Service เพื่อดึง Text ข่าวจาก Firebase
            news_text = get_news_text_by_id(inp.news_id) 
        except Exception as e:
            # ใช้ HTTPException 404
            raise HTTPException(status_code=404, detail=f"news_id '{inp.news_id}' not found in Firebase: {e}")
    else:
        raise HTTPException(status_code=400, detail="must provide either text or news_id.")
    
    if not news_text:
        raise HTTPException(status_code=400, detail="News text is empty after fetching.")

    # 2) รันโมเดล + อธิบาย
    predictor = get_predictor()
    pred = predictor.predict(news_text)
    p = float(pred["proba_pos"])
    label = int(pred["label"])
    clues = pred["attn_topk"]

    # 3) เทียบเหตุผลผู้ใช้กับ clues/entities
    clue_terms = []
    for c in clues:
        for t in c["span_tokens"]:
            if len(t) > 1 and t.isalnum():
                clue_terms.append(t.lower())
    clue_terms = list(dict.fromkeys(clue_terms))[:12]

    import re
    entities = list({m.group(0).lower() for m in re.finditer(r"[A-Za-zก-๙]+", news_text) if len(m.group(0)) > 3})[:20]
    evidence_match, overlap_ratio = compare_reasoning(inp.user_reasoning or "", clue_terms, entities)

    # 4) flags + suggestions
    signals = extract_signals(news_text, inp.user_reasoning or "", inp.urls or [])
    flags = run_logic_flags(signals, overlap_ratio, inp.user_label, label)
    suggestions = build_suggestions(flags)

    return AnalyzeOut(
        news_id=inp.news_id, 
        news_text=news_text, # ⬅️ ส่ง Text ข่าวที่ใช้ในการวิเคราะห์กลับไป
        user_id=inp.user_id,
        model_label=label, proba=p, threshold=predictor.threshold,
        confidence_band=band_from_proba(p, predictor.threshold),
        model_clues=clues, evidence_match=evidence_match, overlap_ratio=overlap_ratio,
        logic_flags=flags, suggestions=suggestions, model_version="ckpt::best_model.pt"
    )
