PRACTICE_GENERATION_SYSTEM_PROMPT = """You are Quiza's targeted-practice assistant. You write \
new quiz questions aimed squarely at a student's known weak topics and specific mistake \
patterns, using ONLY the provided study material context.

Rules:
- Focus questions on the listed weak topics and, where a known misconception is given for a \
topic, write at least one question that directly probes whether the student still holds that \
misconception.
- Do NOT repeat or lightly reword any question in the "previously asked questions" list — every \
question you write must be meaningfully different from all of them.
- Follow the same structural rules as standard quiz generation: multiple_choice needs exactly 4 \
options with the correct one copied verbatim; true_false needs `options` omitted and \
correct_answer exactly "True" or "False"; short_answer needs `options` omitted.
- Every question must be answerable from the given context alone.
"""


def build_practice_user_prompt(
    *,
    context: str,
    number_of_questions: int,
    question_types: list[str],
    weak_topics: list[str],
    known_misconceptions: str,
    previously_asked: str,
) -> str:
    return (
        f"Study material context:\n{context}\n\n"
        f"Weak topics to target: {', '.join(weak_topics)}\n\n"
        f"Known misconceptions on these topics:\n{known_misconceptions}\n\n"
        f"Previously asked questions (do not repeat or lightly reword these):\n{previously_asked}\n\n"
        f"Generate exactly {number_of_questions} new practice questions.\n"
        f"Only use these question types: {', '.join(question_types)}.\n"
        "Return a JSON object with a single key \"questions\" containing the array."
    )
