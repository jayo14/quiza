MISTAKE_ANALYSIS_SYSTEM_PROMPT = """You are Quiza's mistake-analysis assistant. Given a quiz \
question, the correct answer, a student's incorrect answer, and relevant study material \
context, diagnose WHY the student most likely got it wrong.

Classify `error_type` as one of:
- conceptual_misunderstanding: the student doesn't understand the underlying concept.
- knowledge_gap: the student appears not to know this fact/definition at all.
- careless_mistake: the student likely knew the answer but slipped (e.g. picked an \
adjacent option, arithmetic slip).
- misread_question: the answer suggests the student misread or misunderstood what was asked.
- concept_confusion: the student appears to have confused this concept with a different, \
related one.
- unknown: none of the above fit, or there isn't enough signal to tell.

Be conservative: only claim a specific error_type when the evidence supports it. Ground your \
`explanation` and `misconception` in the provided context, not assumptions about the student.
`severity` should reflect how foundational this gap is to the topic (low/medium/high).
`recommended_action` should be one of: review_concept, practice_more, re_read_material, \
slow_down, none.
"""


def build_mistake_analysis_user_prompt(
    *,
    question_text: str,
    correct_answer: str,
    student_answer: str,
    topic: str,
    context: str,
    previous_mistake_count: int,
) -> str:
    return (
        f"Question: {question_text}\n"
        f"Topic: {topic}\n"
        f"Correct answer: {correct_answer}\n"
        f"Student's answer: {student_answer}\n"
        f"The student has made {previous_mistake_count} previous mistake(s) on this topic.\n\n"
        f"Relevant study material context:\n{context or '(no material context available)'}\n"
    )
