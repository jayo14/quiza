from unittest.mock import patch

from tests.fakes import FakeEmbeddingProvider, fake_get_context_for_query, generate_quiz_with_fakes, true_false_questions


def _setup_and_submit(client, headers, *, correct_answers: list[bool]):
    with patch("app.ai.rag.ingestion.get_embedding_provider", return_value=FakeEmbeddingProvider()):
        upload = client.post(
            "/api/v1/materials",
            files={"file": ("notes.txt", b"Photosynthesis converts light into energy. " * 20, "text/plain")},
            headers=headers,
        )
    material_id = upload.json()["id"]

    questions = true_false_questions("Photosynthesis", len(correct_answers), correct_answer="True")
    generated = generate_quiz_with_fakes(
        client, headers, material_id=material_id, questions=questions, question_types=["true_false"]
    )
    body = generated.json()
    quiz_id, question_ids = body["id"], [q["id"] for q in body["questions"]]

    attempt = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers).json()
    answers = [
        {"question_id": qid, "selected_answer": "True" if is_correct else "False"}
        for qid, is_correct in zip(question_ids, correct_answers)
    ]

    with (
        patch("app.ai.answer_analyzer.get_context_for_query", side_effect=fake_get_context_for_query),
        patch("app.ai.answer_analyzer.get_llm_provider") as mock_llm,
    ):
        from app.ai.answer_analyzer import MistakeAnalysisResult

        class _FakeAnalysisLLM:
            async def generate_structured(self, *, system_prompt, user_prompt, response_model, max_retries=2):
                return MistakeAnalysisResult(
                    error_type="knowledge_gap",
                    concept="Light-dependent reactions",
                    explanation="The student appears not to know this fact.",
                    misconception="Confuses energy conversion direction.",
                    severity="medium",
                    recommended_action="review_concept",
                )

        mock_llm.return_value = _FakeAnalysisLLM()
        submit = client.post(
            f"/api/v1/attempts/{attempt['id']}/submit", json={"answers": answers}, headers=headers
        )

    return submit, material_id


def test_low_accuracy_with_enough_volume_creates_a_weakness(client, signup):
    headers, _ = signup()
    # 4 questions, 1 correct -> 25% accuracy, well past the 3-question minimum.
    submit, _ = _setup_and_submit(client, headers, correct_answers=[True, False, False, False])
    assert submit.status_code == 200

    weaknesses = client.get("/api/v1/analytics/weaknesses", headers=headers).json()
    assert len(weaknesses) == 1
    assert weaknesses[0]["topic"] == "Photosynthesis"
    assert weaknesses[0]["mistake_count"] == 3
    assert weaknesses[0]["severity"] == "high"


def test_a_single_mistake_does_not_create_a_weakness(client, signup):
    headers, _ = signup()
    # Only 1 question total: below MIN_QUESTIONS_FOR_WEAKNESS.
    submit, _ = _setup_and_submit(client, headers, correct_answers=[False])
    assert submit.status_code == 200

    weaknesses = client.get("/api/v1/analytics/weaknesses", headers=headers).json()
    assert weaknesses == []


def test_high_accuracy_does_not_create_a_weakness(client, signup):
    headers, _ = signup()
    submit, _ = _setup_and_submit(client, headers, correct_answers=[True, True, True, False])
    assert submit.status_code == 200

    weaknesses = client.get("/api/v1/analytics/weaknesses", headers=headers).json()
    assert weaknesses == []


def test_mistake_analysis_writes_structured_diagnosis_onto_answers(client, signup):
    headers, _ = signup()
    submit, _ = _setup_and_submit(client, headers, correct_answers=[False, False, False])
    result = submit.json()

    incorrect = [a for a in result["answers"] if not a["is_correct"]]
    assert len(incorrect) == 3
    # The background mistake-analysis task runs synchronously under TestClient, so
    # by the time we re-fetch the attempt its answers should carry the diagnosis.
    refreshed = client.get(f"/api/v1/attempts/{result['id']}", headers=headers).json()
    assert refreshed["status"] == "completed"
