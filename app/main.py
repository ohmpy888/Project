from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from services.db import get_challenge_item # ⬅️ แก้ไข: ใช้ฟังก์ชันดึง Item จาก Firebase
from services.model import get_predictor # ⬅️ Import get_predictor แทน run_prediction
from routes.analyze import band_from_proba # ⬅️ Import band_from_proba เพื่อใช้ในการวิเคราะห์
# ⚠️ Import logic การวิเคราะห์จาก routes/analyze.py เพื่อไม่ให้เกิดการวนซ้ำ
from inference.flags_and_suggestions import (
    extract_signals, run_logic_flags, build_suggestions, compare_reasoning
)
import re
import json

app = FastAPI(title="Real or Fake Backend API")

# ⚠️ ตั้งค่า CORS เพื่อให้ React Frontend สามารถเรียก API ได้
# ในการใช้งานจริง ควรจำกัด origins ให้เฉพาะ Domain ของ Frontend เท่านั้น
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # อนุญาตทั้งหมดสำหรับ Local Dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------------------------
# SCHEMAS (นำมาไว้ที่นี่ชั่วคราวเพื่อให้ไฟล์ main.py ทำงานได้สมบูรณ์)
# ----------------------------------------------------------------------

class AnalyzeRequest(BaseModel):
    """ Schema สำหรับรับข้อมูลจาก Frontend """
    news_id: Optional[str] = None # ใช้เมื่อเลือกโจทย์ Daily
    news_text: Optional[str] = None # ใช้เมื่อวางข่าวเอง
    user_id: Optional[str] = None
    user_label: Optional[int] = None 
    user_reasoning: Optional[str] = None # เหตุผลที่ผู้ใช้ให้มา (สำหรับ Feedback)
    urls: Optional[List[str]] = None

class AnalyzeResponse(BaseModel):
    """ Schema สำหรับส่งผลลัพธ์กลับไปยัง Frontend (ปรับตาม AnalyzeOut เดิม) """
    # Data ข่าว
    item_id: str
    title: str = "Analysis Result"
    text: str
    
    # ผลลัพธ์โมเดล
    predicted_label: int
    probability: float
    clues: list[str]
    logic_flags: Dict[str, str]
    suggestions: list[str]

# ==============================================================================
# 🟢 1. Endpoint สำหรับดึงโจทย์ Daily
# ==============================================================================
# ⚠️ โค้ดนี้จะจำลองการดึงโจทย์ประจำวัน โดยกำหนดให้ 'item1' เป็นโจทย์เริ่มต้น
@app.get("/api/v1/daily-challenge")
async def get_daily_challenge():
    # ⚠️ Mock: สำหรับการเริ่มต้น ใช้ item1 เป็นโจทย์ Daily
    daily_item_id = "item1" 
    
    # 1. ดึงข้อมูลจาก Firebase
    item_data = get_challenge_item(daily_item_id)
    
    if not item_data:
        # หาก Firebase ไม่มี item1 ให้ลอง item2 หรือ item3
        item_data = get_challenge_item("item2")
        if not item_data:
            raise HTTPException(status_code=404, detail="Daily challenge item not found. Check Firebase /items/item1.")
    
    # 2. คืนค่าเฉพาะที่จำเป็นสำหรับ Frontend (title, text, id)
    return {
        "item_id": item_data["item_id"],
        # ⚠️ Assumption: title อยู่ใน item_data
        "title": item_data.get("title", f"Challenge {item_data['item_id']}"), 
        "text": item_data.get("text", "Content missing from Firebase.")
    }

# ==============================================================================
# 🟢 2. Endpoint สำหรับรันการวิเคราะห์ (Analysis)
# ==============================================================================
@app.post("/api/v1/analyze", response_model=AnalyzeResponse)
async def analyze_news(request: AnalyzeRequest):
    
    news_id = request.news_id
    news_text = request.news_text
    
    item_data = {}
    
    # 1. ดึงข้อมูลตัวข่าว
    if news_id:
        # กรณี Daily Challenge: ดึงจาก DB (Firebase)
        item_data = get_challenge_item(news_id)
        if not item_data or not item_data.get("text"):
             raise HTTPException(status_code=404, detail=f"Item ID '{news_id}' not found or text is missing.")
        text_to_analyze = item_data["text"]
    elif news_text:
        # กรณีวางข่าวเอง: ใช้ text ที่ส่งมา
        item_data = {"item_id": "user-input", "title": "User Submitted News", "text": news_text}
        text_to_analyze = news_text
    else:
        raise HTTPException(status_code=400, detail="Must provide news_id or news_text")

    # 2. รันโมเดล + อธิบาย (ใช้ Logic คล้าย routes/analyze.py เดิม)
    predictor = get_predictor()
    pred = predictor.predict(text_to_analyze)
    p = float(pred["proba_pos"])
    label = int(pred["label"])
    clues = pred["attn_topk"]
    
    # 3. เทียบเหตุผลผู้ใช้กับ clues/entities (ใช้ Logic จาก routes/analyze.py เดิม)
    clue_terms = []
    for c in clues:
        for t in c["span_tokens"]:
            if len(t) > 1 and t.isalnum():
                clue_terms.append(t.lower())
    clue_terms = list(dict.fromkeys(clue_terms))[:12]

    entities = list({m.group(0).lower() for m in re.finditer(r"[A-Za-zก-๙]+", text_to_analyze) if len(m.group(0)) > 3})[:20]
    evidence_match, overlap_ratio = compare_reasoning(request.user_reasoning or "", clue_terms, entities)

    # 4. flags + suggestions (ใช้ Logic จาก routes/analyze.py เดิม)
    signals = extract_signals(text_to_analyze, request.user_reasoning or "", request.urls or [])
    
    # ⚠️ NOTE: user_label อาจเป็น None จาก Frontend
    user_label_val = request.user_label if request.user_label is not None else -1 
    flags = run_logic_flags(signals, overlap_ratio, user_label_val, label)
    suggestions_data = build_suggestions(flags)

    # 5. รวบรวมผลลัพธ์
    response_data = {
        "item_id": item_data.get("item_id", "user-input"),
        "title": item_data.get("title", "User Submitted News"),
        "text": text_to_analyze,
        "predicted_label": label,
        "probability": p,
        "clues": [json.dumps(c) for c in clues], # ⚠️ Convert dict clues to string array for AnalyzeResponse simplicity
        "logic_flags": {f["flag_name"]: f.get("reason", "") for f in flags},
        "suggestions": [s["suggestion"] for s in suggestions_data]
    }
    
    return response_data
