# app/routers/ranking.py

from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def get_ranking():
    return {"message": "This is the ranking endpoint"}
