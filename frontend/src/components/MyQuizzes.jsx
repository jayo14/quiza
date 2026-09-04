import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Plus, Trash2, Play } from "lucide-react";
import { listQuizzes, deleteQuiz, startAttempt } from "../services/apiClient";
import "./MyQuizzes.css";

function MyQuizzes() {
  const navigate = useNavigate();
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const fetchQuizzes = async () => {
    try {
      setLoading(true);
      const data = await listQuizzes();
      setQuizzes(data || []);
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

  const handleDelete = async (quizId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this quiz?")) return;
    try {
      await deleteQuiz(quizId);
      setQuizzes((prev) => prev.filter((q) => q.id !== quizId));
    } catch (err) {
      alert(err.message || "Failed to delete quiz");
    }
  };

  const handleStartAttempt = async (quizId) => {
    try {
      const attempt = await startAttempt(quizId);
      navigate(`/quiz?id=${quizId}&attempt_id=${attempt.id}`);
    } catch (err) {
      navigate(`/quiz?id=${quizId}`);
    }
  };

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
      ) : quizzes.length === 0 ? (
        <div style={{ textAlign: "center", padding: "40px 0" }}>
          <p>No quizzes found. Upload study materials to generate your first quiz!</p>
        </div>
      ) : (
        <div className="my-quizzes__list">
          {quizzes.map((quiz) => (
            <div className="my-quiz" key={quiz.id}>
              <div className="my-quiz__info">
                <h3>{quiz.title || "Untitled Quiz"}</h3>
                <p>
                  {quiz.question_count || 0} Questions · Difficulty: {quiz.difficulty || "medium"}
                </p>
              </div>

              <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                <button onClick={() => handleStartAttempt(quiz.id)}>
                  <Play size={15} style={{ marginRight: "4px" }} /> Start Quiz
                </button>
                <button
                  onClick={(e) => handleDelete(quiz.id, e)}
                  style={{ background: "#ef4444", border: "none", borderRadius: "8px", color: "white", padding: "10px", cursor: "pointer" }}
                  title="Delete Quiz"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}

export default MyQuizzes;
