SUMMARY_SYSTEM_PROMPT = """You are Quiza's learning-summary assistant. Given a student's quiz \
attempt results, their per-question outcomes, their known weak topics, and (if available) how \
this attempt compares to their previous performance, write an encouraging but honest summary \
of how they did.

Ground every claim in the data you're given — do not invent topics, mistakes, or numbers that \
aren't present in the input. If there isn't enough information for a field (e.g. no previous \
attempts to compare against), say so plainly rather than fabricating a comparison.
"""


def build_summary_user_prompt(
    *,
    quiz_title: str,
    score: float,
    accuracy: float,
    total_questions: int,
    correct_count: int,
    incorrect_count: int,
    topic_performance: str,
    missed_questions: str,
    known_weaknesses: str,
    previous_attempt_comparison: str,
) -> str:
    return (
        f"Quiz: {quiz_title}\n"
        f"Score: {correct_count}/{total_questions} ({accuracy:.0%} accuracy)\n\n"
        f"Topic performance this attempt:\n{topic_performance}\n\n"
        f"Missed questions (with diagnosed mistakes where available):\n{missed_questions}\n\n"
        f"Student's known weak topics across all history:\n{known_weaknesses}\n\n"
        f"Comparison with previous attempts:\n{previous_attempt_comparison}\n\n"
        "Return a JSON object matching the schema, with recommended_practice being concrete, "
        "specific next steps (e.g. \"5 questions on friction\") rather than generic advice."
    )
