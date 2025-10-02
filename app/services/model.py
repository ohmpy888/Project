# backend/app/services/model.py
import sys
from pathlib import Path 
from typing import Dict, Any, List, Optional
import json
import re # สำหรับใช้ใน Logic Flags
from fastapi import HTTPException
from pydantic import BaseModel, Field

# Fix ModuleNotFoundError: เพิ่ม Path ของ Project Root เพื่อให้ import ได้
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent 
sys.path.insert(0, str(PROJECT_ROOT)) 

# 🟢 FIX: Import Predictor และ get_predictor จาก inference.predictor
from inference.predictor import Predictor, get_predictor
from core.config import settings

# ⚠️ Import Logic Flags ที่จำเป็น
from inference.flags_and_suggestions import (
    extract_signals, run_logic_flags, build_suggestions, compare_reasoning
)

# 🔴 REMOVED: ลบฟังก์ชัน get_predictor() ที่ซ้ำซ้อนออกไป (เพราะอยู่ที่ inference/predictor.py แล้ว)

# --------------------------------------------------------
# 1. Models for API Requests
# --------------------------------------------------------

class AnalysisRequest(BaseModel):
    """
    Pydantic Model สำหรับรับข้อมูลการส่งคำตอบจาก Frontend
    """
    user_id: str = Field(..., description="ID ของผู้ใช้ที่ส่งคำตอบ (เช่น 'uid1234')") 
    news_id: str = Field(..., description="ID ของข่าว (dailyChallenges/{dateKey}/items/{itemId})")
    news_text: str = Field(..., description="เนื้อหาของข่าวที่จะถูกวิเคราะห์")
    user_reasoning: str = Field(..., description="เหตุผลในการตัดสินใจของผู้ใช้")
    user_urls: List[str] = Field(default_factory=list, description="รายการ URL ที่ผู้ใช้อ้างอิง")
    user_label: Optional[int] = Field(None, description="การตัดสินใจของผู้ใช้ (1=Reliable, 0=Fake)")


# --------------------------------------------------------
# 2. Models for API Responses
# --------------------------------------------------------

class AnalysisResponse(BaseModel):
    """Pydantic Model สำหรับรูปแบบการตอบกลับทั่วไป"""
    status: str
    data: Optional[Dict[str, Any]] = None
    detail: Optional[str] = None

# ====================================================================
# 🟢 New Prediction Function (รวม Logic การทำนายและวิเคราะห์)
# ====================================================================

def predict_challenge(
    text: str, 
    user_reasoning: Optional[str] = "", 
    user_label: Optional[int] = -1, 
    urls: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Service function to perform prediction and post-processing analysis.
    """
    if urls is None:
        urls = []

    try:
        # 1. ดึงอินสแตนซ์ Predictor ที่โหลดไว้แล้ว
        predictor = get_predictor()

        # 2. รันโมเดล (เรียก predict() จาก Predictor)
        # NOTE: Predictor class ใน inference/predictor.py ใช้เมธอด predict(text)
        pred_result = predictor.predict(text) 
        
        # 2.1 แยกผลลัพธ์หลัก
        label = int(pred_result.get("prediction", 0))
        probability = float(pred_result.get("score", 0.0))
        clues = pred_result.get("clues", []) # คาดหวัง 'clues' เป็น List[Dict] เช่นเดียวกับ attn_topk
        
        # 3. เตรียม Clue terms สำหรับ Logic Flags
        clue_terms = []
        for c in clues:
            # สมมติว่า clues แต่ละตัวมี key 'span_tokens' เป็น List[str]
            for t in c.get("span_tokens", []): 
                if len(t) > 1 and t.isalnum():
                    clue_terms.append(t.lower())
        clue_terms = list(dict.fromkeys(clue_terms))[:12]

        # 4. เทียบเหตุผลผู้ใช้ (Logic Flags)
        entities = list({m.group(0).lower() for m in re.finditer(r"[A-Za-zก-๙]+", text) if len(m.group(0)) > 3})[:20]
        evidence_match, overlap_ratio = compare_reasoning(user_reasoning, clue_terms, entities)

        signals = extract_signals(text, user_reasoning, urls)
        flags = run_logic_flags(signals, overlap_ratio, user_label, label)
        suggestions_data = build_suggestions(flags)

        # 5. รวบรวมผลลัพธ์และจัดรูปแบบ
        # NOTE: เปลี่ยน f["flag_name"] เป็น f["code"] เพื่อให้สอดคล้องกับ run_logic_flags
        return {
            "predicted_label": label,
            "probability": probability,
            # ต้องแปลง Dict clues เป็น JSON string เพื่อให้ตรงกับ Pydantic List[str] ใน AnalyzeResponse
            "clues": [json.dumps(c) for c in clues], 
            "logic_flags": {f["code"]: f.get("reason", "") for f in flags}, 
            # 🟢 FIX: ใช้ 'text' ใน suggestion แทน 'suggestion' ตาม build_suggestions
            "suggestions": [s["text"] for s in suggestions_data if "text" in s] 
        }

    except RuntimeError as e:
        # ดักจับ Error หากโมเดลโหลดไม่สำเร็จ
        print(f"ERROR: Cannot predict, model not available. {e}")
        raise HTTPException(status_code=500, detail="Model Service is not initialized.")
    except Exception as e:
        # ดักจับ Error อื่นๆ
        print(f"UNEXPECTED ERROR during prediction: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected Error during analysis: {str(e)}")
