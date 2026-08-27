from enum import StrEnum


class MaterialStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class QuestionType(StrEnum):
    MULTIPLE_CHOICE = "multiple_choice"
    TRUE_FALSE = "true_false"
    SHORT_ANSWER = "short_answer"


class Difficulty(StrEnum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class QuizStatus(StrEnum):
    GENERATING = "generating"
    READY = "ready"
    FAILED = "failed"


class AttemptStatus(StrEnum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class ErrorType(StrEnum):
    CONCEPTUAL_MISUNDERSTANDING = "conceptual_misunderstanding"
    KNOWLEDGE_GAP = "knowledge_gap"
    CARELESS_MISTAKE = "careless_mistake"
    MISREAD_QUESTION = "misread_question"
    CONCEPT_CONFUSION = "concept_confusion"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RecommendedAction(StrEnum):
    REVIEW_CONCEPT = "review_concept"
    PRACTICE_MORE = "practice_more"
    RE_READ_MATERIAL = "re_read_material"
    SLOW_DOWN = "slow_down"
    NONE = "none"
