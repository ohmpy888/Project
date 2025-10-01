# inference/tokenizer.py
# -*- coding: utf-8 -*-
import re
from core.config import settings # ⚠️ Import settings

def simple_tokenize(text: str):
    if text is None: return []
    s = str(text)
    if settings.LOWERCASE: s = s.lower() # ⚠️ ใช้ค่าจาก settings
    s = re.sub(r"<.*?>|https?://\S+|www\.\S+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    tokens = re.findall(r"[a-zA-Z0-9_]+|[^\s\w]", s)
    return tokens