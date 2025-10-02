# app/services/model.py
import sys
from pathlib import Path 
from typing import Dict, Any, List, Optional
import json
import re
from fastapi import HTTPException
from pydantic import BaseModel, Field

# Fix ModuleNotFoundError: เพิ่ม Path ของ Project Root เพื่อให้ import ได้
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent 
sys.path.insert(0, str(PROJECT_ROOT)) 

from inference.predictor import Predictor, get_predictor
from core.config import settings
from inference.flags_and_suggestions import (
    extract_signals, run_logic_flags, build_suggestions, compare_reasoning
)

def predict_challenge(
    text: str,
    user_label: bool,
    user_reasoning: str,
    urls: Optional[List[str]],
) -> Dict[str, Any]:
    """
    Service หลักในการวิเคราะห์ข่าว: รับข้อความ, ทำนายผล, เปรียบเทียบเหตุผล, และสร้าง Feedback
    """
    if urls is None:
        urls = []

    try:
        # 1. โหลดโมเดลและทำนายผล
        predictor = get_predictor()
        prediction_result = predictor.predict(text)

        label = prediction_result.get("prediction", 0)
        probability = prediction_result.get("score", 0.0)
        raw_clues = prediction_result.get("clues", [])

        # ✅ FIX: ประมวลผล Clues ที่ได้จากโมเดลให้เป็นโครงสร้างที่ถูกต้อง
        clue_words_analysis = []
        clue_terms = []
        if raw_clues:
            # ดึง list ของคำ (token) ออกมา
            clue_terms = [c.get('token', '').strip().lower() for c in raw_clues]
            
            # สร้าง list of dicts สำหรับ `clue_words_analysis`
            for clue_data in raw_clues:
                clue_word = clue_data.get('token', '').strip()
                if not clue_word:
                    continue
                
                # ตรวจสอบว่าผู้ใช้ได้กล่าวถึงคำใบ้นี้ในเหตุผลหรือไม่
                found = clue_word.lower() in user_reasoning.lower() if user_reasoning else False
                
                analysis_text = "คำนี้เป็นหนึ่งในปัจจัยสำคัญที่ AI ใช้ในการตัดสินใจ"
                
                clue_words_analysis.append({
                    "word": clue_word,
                    "analysis": analysis_text,
                    "found_in_reason": found
                })

        # 3. วิเคราะห์ด้วย Logic-based rules
        signals = extract_signals(text, user_reasoning, urls)
        evidence_match, overlap_ratio = compare_reasoning(user_reasoning, clue_terms, [])
        flags = run_logic_flags(signals, overlap_ratio, user_label, bool(label))
        suggestions_data = build_suggestions(flags)
        
        # 4. รวบรวมผลลัพธ์ทั้งหมดเพื่อส่งกลับไปให้ analyze.py
        return {
            "predicted_label": label,
            "probability": probability,
            "suggestions": [s.get("text", "") for s in suggestions_data],
            "clue_words_analysis": clue_words_analysis # ส่งข้อมูลที่ประมวลผลแล้วกลับไป
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred in model service: {e}")