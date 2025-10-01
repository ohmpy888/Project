# app/schemas.py
from pydantic import BaseModel
from typing import List, Literal, Optional, Any, Dict

class Challenge(BaseModel):
    id: str
    title: str
    content: str
    source: str
    domain: str
    publishDate: str
    difficulty: Literal["easy", "medium", "hard"]

class AnalyzeIn(BaseModel):
    news_id: Optional[str] = None
    text: Optional[str] = None
    user_id: Optional[str] = None
    user_label: Optional[int] = None  # 0=fake,1=real
    user_reasoning: Optional[str] = None
    urls: Optional[List[str]] = None
    news_id: Optional[str] = None
    text: Optional[str] = None

class AnalyzeOut(BaseModel):
    news_id: Optional[str] = None
    news_text: Optional[str] = None # ⬅️ เพิ่ม Field นี้สำหรับส่ง Text ข่าวกลับ
    user_id: Optional[str] = None
    model_label: int
    proba: float
    threshold: float
    confidence_band: Literal["low","medium","high"]
    model_clues: List[Dict[str, Any]]
    evidence_match: Literal["low","partial","good"]
    overlap_ratio: float
    logic_flags: List[Dict[str, str]]
    suggestions: List[Dict[str, Any]]
    model_version: str
