from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.weakness import Weakness


def list_weaknesses(db: Session, *, user: User) -> list[Weakness]:
    stmt = (
        select(Weakness)
        .where(Weakness.user_id == user.id)
        .order_by(Weakness.confidence.desc(), Weakness.accuracy.asc())
    )
    return list(db.scalars(stmt).all())
