import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { getAttempt } from "../services/apiClient";
import "./ReviewAnswers.css";

function ReviewAnswers() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const attemptId = searchParams.get("attempt_id") || location.state?.attemptId;

  const [answers, setAnswers] = useState(location.state?.answers || []);
  const [loading, setLoading] = useState(!location.state?.answers && !!attemptId);

  useEffect(() => {
    const fetchAttempt = async () => {
      if (!attemptId || answers.length > 0) return;
      try {
        setLoading(true);
        const data = await getAttempt(attemptId);
        setAnswers(data?.answers || []);
      } catch (err) {
        console.error("Failed to load attempt for review:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAttempt();
  }, [attemptId, answers]);

  return (
    <section className="review-answers">
      <div className="review-answers__header">
        <h1>Review Answers</h1>
        <p>See how you answered each question.</p>
      </div>

      {loading ? (
        <p>Loading review...</p>
      ) : (
        <div className="review-answers__list">
          {answers.map((item, index) => {
            const isCorrect = item.is_correct ?? item.isCorrect;
            const questionText = item.question_text || item.question || `Question ${index + 1}`;
            const selected = item.selected_answer || item.selected_option || item.selectedAnswer || item.text_answer || "N/A";
            const correct = item.correct_answer || item.correctAnswer || "N/A";

            return (
              <div
                className={`review-answers__card ${
                  isCorrect ? "correct" : "incorrect"
                }`}
                key={item.question_id || index}
              >
                <div className="review-answers__question">
                  <span>Question {index + 1}</span>
                  <h2>{questionText}</h2>
                </div>

                <div className="review-answers__result">
                  <div>
                    <span>Your answer</span>
                    <strong>{selected}</strong>
                  </div>

                  <div>
                    <span>Correct answer</span>
                    <strong>{correct}</strong>
                  </div>
                </div>

                {item.explanation && (
                  <p style={{ marginTop: "8px", fontSize: "0.85rem", color: "#888" }}>
                    <strong>Explanation:</strong> {item.explanation}
                  </p>
                )}

                <p className="review-answers__status">
                  {isCorrect ? "✓ Correct" : "✕ Incorrect"}
                </p>
              </div>
            );
          })}
        </div>
      )}

      <button
        className="review-answers__back"
        onClick={() => navigate("/quizzes")}
      >
        Back to Quizzes
      </button>
    </section>
  );
}

export default ReviewAnswers;
