# app/routes/daily.py
from fastapi import APIRouter
from typing import List
from app.schemas import Challenge
from app.services.db import list_daily_items

router = APIRouter()

@router.get("/daily_challenges", response_model=List[Challenge])
def daily_challenges():
    return list_daily_items()
