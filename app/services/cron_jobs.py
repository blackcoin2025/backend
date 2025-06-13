from sqlalchemy.orm import Session
from app.models import Balance, Level, Ranking, TaskStat
from datetime import datetime

def update_daily_stats(db: Session):
    """Met à jour les statistiques quotidiennes pour tous les utilisateurs."""
    now = datetime.utcnow()
    users = db.query(Balance).all()
    for user in users:
        # Exemple : Réinitialisation de certaines données quotidiennes
        tasks = db.query(TaskStat).filter(TaskStat.telegram_id == user.telegram_id).first()
        if tasks:
            tasks.validated = 0
        db.commit()

def recalculate_rankings(db: Session):
    """Recalcule les classements globaux."""
    rankings = db.query(Ranking).order_by(Ranking.rank).all()
    for i, rank in enumerate(rankings):
        rank.rank = i + 1
    db.commit()
