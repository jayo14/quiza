import logging
from datetime import datetime, timezone

from app.core.async_loop import run_async
from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@celery_app.task(bind=True, name="tasks.ingest_material")
def ingest_material_task(self, material_id: str) -> dict:
    """Ingest a material when explicitly requested by a generation job."""
    from app.ai.rag.ingestion import run_ingestion_for_material
    from app.models.enums import MaterialStatus
    from app.models.material import Material

    db = SessionLocal()
    try:
        material = db.get(Material, material_id)
        if not material:
            return {"status": "error", "message": f"Material {material_id} not found"}
        if material.status == MaterialStatus.READY:
            return {"status": "already_ready", "material_id": material_id}

        run_async(run_ingestion_for_material(material_id))

        db.expire_all()
        material = db.get(Material, material_id)
        return {"status": material.status if material else "unknown", "material_id": material_id}
    finally:
        db.close()


@celery_app.task(bind=True, name="tasks.generate_quiz", max_retries=0)
def generate_quiz_task(
    self,
    job_id: str,
    user_id: str,
    material_ids: list[str],
    question_count: int,
    difficulty: str,
    question_types: list[str],
) -> dict:
    """Process one durable generation job from start to finish."""
    from app.ai.quiz_generator import generate_quiz_questions
    from app.ai.rag.ingestion import run_ingestion_for_material
    from app.core.exceptions import safe_error_message
    from app.models.enums import Difficulty, GenerationJobStatus, MaterialStatus, QuestionType, QuizStatus
    from app.models.generation_job import GenerationJob
    from app.models.material import Material
    from app.models.question import Question
    from app.models.quiz import Quiz

    db = SessionLocal()
    job = None

    def update_job(stage: str, progress: int) -> None:
        job.current_stage = stage
        job.progress = progress
        db.add(job)
        db.commit()

    try:
        job = db.get(GenerationJob, job_id)
        if not job or job.user_id != user_id:
            return {"status": "error", "message": "Generation job not found"}
        if job.status == GenerationJobStatus.COMPLETED:
            return {"status": "already_completed", "job_id": job_id, "quiz_id": job.quiz_id}
        if job.status == GenerationJobStatus.PROCESSING:
            return {"status": "already_processing", "job_id": job_id}

        task_id = getattr(getattr(self, "request", None), "id", None)
        job.status = GenerationJobStatus.PROCESSING
        job.started_at = job.started_at or _utcnow()
        job.celery_task_id = job.celery_task_id or task_id
        db.add(job)
        db.commit()

        update_job("preparing_materials", 5)
        materials = [db.get(Material, material_id) for material_id in material_ids]
        if any(material is None or material.user_id != user_id for material in materials):
            raise ValueError("One or more selected materials could not be found.")

        for index, material in enumerate(materials):
            if material.status != MaterialStatus.READY:
                run_async(run_ingestion_for_material(material.id))
            update_job("reading_materials", 10 + int((index + 1) / len(materials) * 30))

        db.expire_all()
        materials = [db.get(Material, material_id) for material_id in material_ids]
        failed = [material for material in materials if material.status == MaterialStatus.FAILED]
        if failed:
            raise ValueError(
                "Material processing failed: " + ", ".join(material.filename for material in failed)
            )
        if any(material.status != MaterialStatus.READY for material in materials):
            raise ValueError("Selected materials are not ready for generation.")

        primary = materials[0]
        update_job("finding_relevant_content", 50)
        generated = run_async(
            generate_quiz_questions(
                db,
                user_id=user_id,
                material_id=primary.id,
                material_ids=material_ids,
                number_of_questions=question_count,
                difficulty=Difficulty(difficulty),
                question_types=[QuestionType(value) for value in question_types],
            )
        )

        if not generated:
            raise ValueError("No questions could be generated from the selected materials.")

        if len(generated) > question_count:
            generated = generated[:question_count]

        effective_count = len(generated)

        update_job("saving_quiz", 90)
        title = f"Quiz: {primary.title}" if len(materials) == 1 else f"Multi-Material Quiz ({len(materials)} sources)"
        quiz = Quiz(
            user_id=user_id,
            material_id=primary.id,
            title=title,
            difficulty=Difficulty(difficulty),
            number_of_questions=effective_count,
            status=QuizStatus.READY,
        )
        db.add(quiz)
        db.flush()
        db.add_all(
            [
                Question(
                    quiz_id=quiz.id,
                    order_index=index,
                    question_type=question.question_type,
                    question_text=question.question,
                    options=question.options if question.options else (["True", "False"] if question.question_type == QuestionType.TRUE_FALSE else None),
                    correct_answer=question.correct_answer,
                    explanation=question.explanation,
                    topic=question.topic,
                    difficulty=question.difficulty,
                    source_reference=question.source_reference,
                )
                for index, question in enumerate(generated)
            ]
        )
        job.quiz_id = quiz.id
        job.status = GenerationJobStatus.COMPLETED
        job.progress = 100
        job.current_stage = "completed"
        job.completed_at = _utcnow()
        job.error_message = None
        db.commit()
        logger.info(
            "Generation job completed job_id=%s task_id=%s user_id=%s materials=%s question_count=%d",
            job_id,
            task_id,
            user_id,
            material_ids,
            question_count,
        )
        return {"status": "completed", "job_id": job_id, "quiz_id": quiz.id}
    except Exception as exc:
        fallback_task_id = getattr(getattr(self, "request", None), "id", None) if "self" in locals() else None
        logger.exception("Generation job failed job_id=%s task_id=%s", job_id, fallback_task_id)
        db.rollback()
        if job is None:
            job = db.get(GenerationJob, job_id)
        if job:
            job.status = GenerationJobStatus.FAILED
            job.current_stage = "failed"
            job.error_message = safe_error_message(exc)
            job.completed_at = _utcnow()
            db.add(job)
            db.commit()
        return {"status": "failed", "job_id": job_id, "message": safe_error_message(exc)}
    finally:
        db.close()
