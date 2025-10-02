# app/schemas.py
from pydantic import BaseModel
from typing import List, Literal, Optional, Any, Dict


class ChallengeSubmission(BaseModel):
    """
    Schema สำหรับรับข้อมูลครบชุดจาก Frontend (News Data + User Input)
    """
    news_text: str                       # เนื้อหาข่าว (Required)
    news_id: Optional[str] = None        # ID ข่าว (e.g., dailyChallenges/{dateKey}/items/{itemId})
    user_label: Optional[int] = -1       # คำตอบของผู้ใช้ (-1, 0=fake, 1=real)
    user_reasoning: Optional[str] = ""   # เหตุผลของผู้ใช้
    date_key: Optional[str] = None       # วันที่/Key สำหรับอ้างอิง (YYY-MM-DD)
    user_urls: Optional[List[str]] = []  # ลิงก์ที่ผู้ใช้อ้างอิง

    
class Challenge(BaseModel):
    id: str
    title: str
    content: str
    source: str
    domain: str
    publishDate: str
    difficulty: Literal["easy", "medium", "hard"]

class AnalyzeOut(BaseModel):
    """
    Schema สำหรับตอบกลับหลังจากวิเคราะห์เสร็จ (Strong Schema)
    """
    # === Metadata (ข้อมูลที่ส่งกลับไปเพื่อให้ Frontend อ้างอิง) ===
    news_id: Optional[str] = None
    news_text: Optional[str] = None
    user_id: Optional[str] = None
    date_key: Optional[str] = None
    item_id: Optional[str] = None # ⬅️ เพิ่มตัวนี้สำหรับการอ้างอิงเฉพาะ Item ID

    # === Model Prediction Results ===
    model_label: int
    proba: float
    threshold: float
    confidence_band: Literal["low","medium","high"]
    model_clues: List[Dict[str, Any]]
    model_version: str

    # === Logic & Comparison Results ===
    evidence_match: Literal["low","partial","good"]
    overlap_ratio: float
    logic_flags: List[Dict[str, str]]
    suggestions: List[Dict[str, Any]]
