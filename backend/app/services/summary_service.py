from sqlalchemy.orm import Session

from app.ai.summary_generator import generate_attempt_summary
from app.core.exceptions import ValidationFailedError
from app.models.enums import AttemptStatus
from app.models.summary import Summary
from app.models.user import User
from app.services import attempt_service


async def get_or_generate_summary(db: Session, *, user: User, attempt_id: str) -> Summary:
    attempt = attempt_service.get_owned_attempt(db, user=user, attempt_id=attempt_id)

    if attempt.summary is not None:
        return attempt.summary

    if attempt.status != AttemptStatus.COMPLETED:
        raise ValidationFailedError("Submit this attempt before requesting a summary.")

    content = await generate_attempt_summary(db, attempt=attempt)

    summary = Summary(
        attempt_id=attempt.id,
        user_id=user.id,
        content=content.model_dump(mode="json"),
        raw_ai_response=content.model_dump(mode="json"),
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary
