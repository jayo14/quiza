import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Clock, HelpCircle, Loader2, Play, Plus, Sparkles, Trash2 } from "lucide-react";
import { listQuizzes, deleteQuiz, startAttempt } from "../services/apiClient";
import "./MyQuizzes.css";

const formatDate = (dateStr) => {
  if (!dateStr) return null;
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
  } catch {
    return null;
  }
};

function MyQuizzes() {
  const navigate = useNavigate();
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [quizToDelete, setQuizToDelete] = useState(null);
  const [startingQuizId, setStartingQuizId] = useState(null);

  const fetchQuizzes = async () => {
    try {
      setLoading(true);
      const data = await listQuizzes();
      const validQuizzes = (data || []).filter((quiz) => {
        const status = (quiz.status || "").toLowerCase();
        const qCount = quiz.question_count || quiz.questions?.length || quiz.number_of_questions || 0;
        return status !== "failed" && status !== "generating" && qCount > 0;
      });
      setQuizzes(validQuizzes);
    } catch (err) {
      console.error("Failed to list quizzes:", err);
      setError(err.message || "Failed to load quizzes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuizzes();
  }, []);

  const openDeleteDialog = (quiz, e) => {
    e.stopPropagation();
    setQuizToDelete(quiz);
  };

  const confirmDelete = async () => {
    if (!quizToDelete) return;
    try {
      await deleteQuiz(quizToDelete.id);
      setQuizzes((prev) => prev.filter((q) => q.id !== quizToDelete.id));
      setQuizToDelete(null);
    } catch (err) {
      setError(err.message || "Failed to delete quiz");
      setQuizToDelete(null);
    }
  };

  const handleStartAttempt = async (quizId) => {
    try {
      setStartingQuizId(quizId);
      const attempt = await startAttempt(quizId);
      navigate(`/quiz?id=${quizId}&attempt_id=${attempt.id}`);
    } catch {
      navigate(`/quiz?id=${quizId}`);
    } finally {
      setStartingQuizId(null);
    }
  };

  const visibleQuizzes = quizzes.filter((quiz) => {
    const status = (quiz.status || "").toLowerCase();
    const qCount = quiz.question_count || quiz.questions?.length || quiz.number_of_questions || 0;
    return status !== "failed" && status !== "generating" && qCount > 0;
  });

  return (
    <section className="my-quizzes">
      <div className="my-quizzes__header">
        <div>
          <h1>My Quizzes</h1>
          <p>Review your quizzes and keep track of your performance.</p>
        </div>

        <button
          className="my-quizzes__generate"
          onClick={() => navigate("/upload")}
        >
          <Plus size={17} />
          Generate Quiz
        </button>
      </div>

      {loading ? (
        <p>Loading quizzes...</p>
      ) : error ? (
        <p style={{ color: "#ff4d4f" }}>{error}</p>
      ) : visibleQuizzes.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <p>No quizzes found. Upload study materials to generate your first quiz!</p>
        </div>
      ) : (
        <div className="my-quizzes__list">
          {visibleQuizzes.map((quiz) => {
            const diff = (quiz.difficulty || "medium").toLowerCase();
            const questionCount = quiz.question_count || quiz.questions?.length || quiz.number_of_questions || 0;

            return (
              <div className="my-quiz" key={quiz.id}>
                <div className="my-quiz__header">
                  <div className="my-quiz__badge-group">
                    <div className="my-quiz__icon-box">
                      <Sparkles size={16} />
                    </div>
                    <span className={`my-quiz__diff-badge my-quiz__diff--${diff}`}>
                      {diff.charAt(0).toUpperCase() + diff.slice(1)}
                    </span>
                  </div>

                  <button
                    type="button"
                    className="my-quiz__delete-btn"
                    onClick={(e) => openDeleteDialog(quiz, e)}
                    title="Delete Quiz"
                    aria-label={`Delete ${quiz.title}`}
                  >
                    <Trash2 size={15} />
                  </button>
                </div>

                <div className="my-quiz__body">
                  <h3 className="my-quiz__title" title={quiz.title || "Untitled Quiz"}>
                    {quiz.title || "Untitled Quiz"}
                  </h3>

                  <div className="my-quiz__meta-row">
                    <span className="my-quiz__meta-pill">
                      <HelpCircle size={13} />
                      {questionCount} Questions
                    </span>
                    {quiz.created_at && (
                      <span className="my-quiz__meta-date">
                        <Clock size={12} />
                        {formatDate(quiz.created_at)}
                      </span>
                    )}
                  </div>
                </div>

                <div className="my-quiz__footer">
                  <button
                    type="button"
                    className="my-quiz__start-btn"
                    onClick={() => handleStartAttempt(quiz.id)}
                    disabled={startingQuizId === quiz.id}
                  >
                    {startingQuizId === quiz.id ? (
                      <>
                        <Loader2 size={15} className="my-quiz__spin" />
                        <span>Starting Quiz...</span>
                      </>
                    ) : (
                      <>
                        <Play size={15} />
                        <span>Start Quiz</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {quizToDelete && (
        <div className="quiz-delete-modal-overlay" onClick={() => setQuizToDelete(null)}>
          <div className="quiz-delete-modal" onClick={(e) => e.stopPropagation()}>
            <h3>Delete Quiz</h3>
            <p>
              Are you sure you want to delete <strong>{quizToDelete.title}</strong>? This action cannot be undone.
            </p>
            <div className="quiz-delete-modal__actions">
              <button
                type="button"
                className="quiz-delete-modal__btn-cancel"
                onClick={() => setQuizToDelete(null)}
              >
                Cancel
              </button>
              <button
                type="button"
                className="quiz-delete-modal__btn-delete"
                onClick={confirmDelete}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default MyQuizzes;
