# inference/tokenizer.py
# -*- coding: utf-8 -*-
import re
from core.config import settings 
from typing import List

def simple_tokenize(text: str) -> List[str]:
    """ Tokenizer function to preprocess text based on model training settings. """
    if text is None: return []
    s = str(text)
    
    # ใช้ค่า LOWERCASE จาก settings
    if settings.LOWERCASE: 
        s = s.lower() 
        
    # ลบ HTML tags และ URLs
    s = re.sub(r"<.*?>|https?://\S+|www\.\S+", " ", s)
    
    # จัดการช่องว่างและตัดขอบ
    s = re.sub(r"\s+", " ", s).strip()
    
    # ค้นหาสัญลักษณ์และคำภาษาไทย/อังกฤษ (ตามที่โมเดลเทรนมา)
    # [a-zA-Z0-9_]+ คือคำปกติ | [^\s\w] คือสัญลักษณ์
    tokens = re.findall(r"[a-zA-Z0-9_]+|[^()\s\w]", s)
    
    return tokens
