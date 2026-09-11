import logging

from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="tasks.ingest_material")
def ingest_material_task(self, material_id: str) -> dict:
    """Celery task: ingest a material's content into the vector store."""
    import asyncio
    from app.models.material import Material
    from app.models.enums import MaterialStatus
    from app.ai.rag.ingestion import run_ingestion_for_material

    db = SessionLocal()
    try:
        material = db.get(Material, material_id)
        if not material:
            return {"status": "error", "message": f"Material {material_id} not found"}

        if material.status == MaterialStatus.READY:
            return {"status": "already_ready", "material_id": material_id}

        if material.status == MaterialStatus.PROCESSING:
            return {"status": "already_processing", "material_id": material_id}

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(run_ingestion_for_material(material_id))
        finally:
            loop.close()

        # Re-check status
        db.expire_all()
        material = db.get(Material, material_id)
        return {
            "status": material.status if material else "unknown",
            "material_id": material_id,
        }
    except Exception as exc:
        logger.exception("Celery ingest failed for material %s", material_id)
        return {"status": "error", "message": str(exc)}
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.generate_quiz")
def generate_quiz_task(
    self,
    quiz_id: str,
    user_id: str,
    material_ids: list[str],
    number_of_questions: int,
    difficulty: str,
    question_types: list[str],
) -> dict:
    """Celery task: generate quiz questions from ingested materials."""
    import asyncio
    from app.models.enums import Difficulty, QuestionType, QuizStatus
    from app.models.question import Question
    from app.models.quiz import Quiz
    from app.models.material import Material
    from app.models.enums import MaterialStatus
    from app.ai.rag.ingestion import run_ingestion_for_material
    from app.ai.quiz_generator import generate_quiz_questions
    from app.core.exceptions import safe_error_message

    db = SessionLocal()
    try:
        quiz = db.get(Quiz, quiz_id)
        if not quiz:
            return {"status": "error", "message": f"Quiz {quiz_id} not found"}

        # Step 1: Ingest any materials that aren't ready yet
        for mid in material_ids:
            mat = db.get(Material, mid)
            if mat and mat.status in (MaterialStatus.UPLOADED, MaterialStatus.QUEUED):
                logger.info("Ingesting material %s before quiz generation...", mat.filename)
                try:
                    loop = asyncio.new_event_loop()
                    try:
                        loop.run_until_complete(run_ingestion_for_material(mat.id))
                    finally:
                        loop.close()
                except Exception as e:
                    logger.error("Ingestion failed for %s: %s", mat.filename, e)

        # Step 2: Refresh materials to check status
        db.expire_all()
        materials = [db.get(Material, mid) for mid in material_ids]
        materials = [m for m in materials if m]

        failed = [m for m in materials if m.status == MaterialStatus.FAILED]
        if failed:
            quiz.status = QuizStatus.FAILED
            quiz.generation_error = f"Ingestion failed for: {', '.join(m.filename for m in failed)}"
            db.add(quiz)
            db.commit()
            return {"status": "failed", "message": quiz.generation_error}

        unready = [m for m in materials if m.status != MaterialStatus.READY]
        if unready:
            quiz.status = QuizStatus.FAILED
            quiz.generation_error = f"Materials still processing: {', '.join(m.filename for m in unready)}"
            db.add(quiz)
            db.commit()
            return {"status": "failed", "message": quiz.generation_error}

        # Step 3: Generate quiz questions
        primary = materials[0]
        diff = Difficulty(difficulty)
        q_types = [QuestionType(t) for t in question_types]

        loop = asyncio.new_event_loop()
        try:
            generated = loop.run_until_complete(
                generate_quiz_questions(
                    db,
                    user_id=user_id,
                    material_id=primary.id,
                    material_ids=material_ids,
                    number_of_questions=number_of_questions,
                    difficulty=diff,
                    question_types=q_types,
                )
            )
        finally:
            loop.close()

        db.add_all(
            [
                Question(
                    quiz_id=quiz.id,
                    order_index=i,
                    question_type=q.question_type,
                    question_text=q.question,
                    options=q.options,
                    correct_answer=q.correct_answer,
                    explanation=q.explanation,
                    topic=q.topic,
                    difficulty=q.difficulty,
                    source_reference=q.source_reference,
                )
                for i, q in enumerate(generated)
            ]
        )
        quiz.status = QuizStatus.READY
        quiz.generation_error = None
        db.add(quiz)
        db.commit()
        logger.info("Celery quiz %s generated %d questions.", quiz_id, len(generated))
        return {"status": "ready", "quiz_id": quiz_id, "questions": len(generated)}

    except Exception as exc:
        logger.exception("Celery quiz generation failed for %s", quiz_id)
        try:
            quiz = db.get(Quiz, quiz_id)
            if quiz:
                quiz.status = QuizStatus.FAILED
                quiz.generation_error = safe_error_message(exc)
                db.add(quiz)
                db.commit()
        except Exception:
            logger.exception("Failed to update quiz status for %s", quiz_id)
        return {"status": "error", "message": str(exc)}
    finally:
        db.close()
