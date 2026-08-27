from unittest.mock import patch

from tests.fakes import FakeEmbeddingProvider, fake_get_context_for_query, generate_quiz_with_fakes, true_false_questions


def _ready_material(client, headers):
    with patch("app.ai.rag.ingestion.get_embedding_provider", return_value=FakeEmbeddingProvider()):
        upload = client.post(
            "/api/v1/materials",
            files={"file": ("notes.txt", b"Photosynthesis converts light into energy. " * 20, "text/plain")},
            headers=headers,
        )
    return upload.json()["id"]


def _quiz_and_questions(client, headers, material_id, topic="Photosynthesis", count=3):
    questions = true_false_questions(topic, count)
    generated = generate_quiz_with_fakes(
        client, headers, material_id=material_id, questions=questions, question_types=["true_false"]
    )
    body = generated.json()
    return body["id"], [q["id"] for q in body["questions"]]


def _submit_with_mocked_mistake_analysis(client, headers, attempt_id, answers):
    with (
        patch("app.ai.answer_analyzer.get_context_for_query", side_effect=fake_get_context_for_query),
        patch("app.ai.answer_analyzer.get_llm_provider") as mock_llm,
    ):
        from app.ai.answer_analyzer import MistakeAnalysisResult

        class _FakeAnalysisLLM:
            async def generate_structured(self, *, system_prompt, user_prompt, response_model, max_retries=2):
                return MistakeAnalysisResult(
                    error_type="knowledge_gap",
                    concept="Light reactions",
                    explanation="exp",
                    misconception="mixes up energy direction",
                    severity="medium",
                    recommended_action="review_concept",
                )

        mock_llm.return_value = _FakeAnalysisLLM()
        return client.post(f"/api/v1/attempts/{attempt_id}/submit", json={"answers": answers}, headers=headers)


class _FakeSummaryLLM:
    async def generate_structured(self, *, system_prompt, user_prompt, response_model, max_retries=2):
        return response_model(
            overall_performance="Solid effort overall.",
            understood_topics=[],
            struggled_topics=["Photosynthesis"],
            key_mistakes=["Missed several true/false questions."],
            weak_topics=["Photosynthesis"],
            concept_explanations=["Light-dependent reactions convert light to chemical energy."],
            recommended_revision=["Re-read the light reactions section."],
            recommended_practice=["3 more true/false questions on Photosynthesis."],
            progress_note="This is the first completed attempt.",
        )


def test_summary_requires_a_completed_attempt(client, signup):
    headers, _ = signup()
    material_id = _ready_material(client, headers)
    quiz_id, question_ids = _quiz_and_questions(client, headers, material_id)
    attempt = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers).json()

    response = client.get(f"/api/v1/attempts/{attempt['id']}/summary", headers=headers)
    assert response.status_code == 422


def test_summary_is_generated_and_cached(client, signup):
    headers, _ = signup()
    material_id = _ready_material(client, headers)
    quiz_id, question_ids = _quiz_and_questions(client, headers, material_id)
    attempt = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers).json()
    answers = [{"question_id": qid, "selected_answer": "False"} for qid in question_ids]
    _submit_with_mocked_mistake_analysis(client, headers, attempt["id"], answers)

    with patch("app.ai.summary_generator.get_llm_provider", return_value=_FakeSummaryLLM()):
        first = client.get(f"/api/v1/attempts/{attempt['id']}/summary", headers=headers)
    assert first.status_code == 200
    assert first.json()["content"]["overall_performance"] == "Solid effort overall."

    # Second call must not need the LLM mock at all — it should be served from the DB.
    second = client.get(f"/api/v1/attempts/{attempt['id']}/summary", headers=headers)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]


def test_summary_is_scoped_to_owner(client, signup):
    headers_a, _ = signup(email="suma@example.com")
    headers_b, _ = signup(email="sumb@example.com")

    material_id = _ready_material(client, headers_a)
    quiz_id, question_ids = _quiz_and_questions(client, headers_a, material_id)
    attempt = client.post(f"/api/v1/quizzes/{quiz_id}/attempts", headers=headers_a).json()

    response = client.get(f"/api/v1/attempts/{attempt['id']}/summary", headers=headers_b)
    assert response.status_code == 404


def test_practice_generate_requires_weakness_or_explicit_topics(client, signup):
    headers, _ = signup()
    material_id = _ready_material(client, headers)

    response = client.post(
        "/api/v1/practice/generate", json={"material_id": material_id, "number_of_questions": 3}, headers=headers
    )
    assert response.status_code == 422


def test_practice_generate_with_explicit_topics(client, signup):
    headers, _ = signup()
    material_id = _ready_material(client, headers)

    practice_questions = [
        {
            "question": "New practice question",
            "question_type": "multiple_choice",
            "options": ["A", "B", "C", "D"],
            "correct_answer": "A",
            "explanation": "exp",
            "topic": "Photosynthesis",
            "difficulty": "medium",
            "source_reference": None,
        }
    ]
    with (
        patch("app.ai.practice_generator.get_context_for_query", side_effect=fake_get_context_for_query),
        patch("app.ai.practice_generator.get_llm_provider") as mock_llm,
    ):
        from tests.fakes import FakeQuizLLM

        mock_llm.return_value = FakeQuizLLM(practice_questions)
        response = client.post(
            "/api/v1/practice/generate",
            json={"material_id": material_id, "number_of_questions": 1, "topics": ["Photosynthesis"]},
            headers=headers,
        )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert len(body["questions"]) == 1
