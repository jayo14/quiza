import { useEffect, useState } from "react";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { getAttempt, getAttemptSummary } from "../services/apiClient";
import "./Summary.css";

function Summary() {
  const location = useLocation();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const attemptIdParam = searchParams.get("attempt_id");

  const [attemptData, setAttemptData] = useState(location.state?.attemptResult || null);
  const [aiSummary, setAiSummary] = useState(null);
  const [loading, setLoading] = useState(!location.state?.attemptResult && !!attemptIdParam);

  useEffect(() => {
    const fetchAttemptDetails = async () => {
      if (!attemptIdParam) return;
      try {
        setLoading(true);
        const data = await getAttempt(attemptIdParam);
        setAttemptData(data);

        const summary = await getAttemptSummary(attemptIdParam).catch(() => null);
        if (summary) setAiSummary(summary.content);
      } catch (err) {
        console.error("Failed to load attempt summary:", err);
      } finally {
        setLoading(false);
      }
    };

    if (!attemptData && attemptIdParam) {
      fetchAttemptDetails();
    }
  }, [attemptIdParam, attemptData]);

  const score = attemptData?.score ?? location.state?.score ?? 0;
  const total = attemptData?.total_questions ?? location.state?.total ?? 0;
  const percentage = total > 0 ? Math.round((score / total) * 100) : 0;
  const incorrect = total - score;
  const answers = attemptData?.answers || location.state?.answers || [];

  return (
    <section className="summary">
      <div className="summary__header">
        <h1>Quiz Complete!</h1>
        <p>Here's how you performed on your quiz.</p>
      </div>

      {loading ? (
        <p>Loading attempt summary...</p>
      ) : (
        <div className="summary__card">
          <h2>Quiz Performance Summary</h2>

          <div className="summary__score">
            <span>{percentage}%</span>
            <small>Your Score</small>
          </div>

          <div className="summary__stats">
            <div className="summary__stat">
              <strong>{score}</strong>
              <span>Correct</span>
            </div>

            <div className="summary__stat">
              <strong>{incorrect}</strong>
              <span>Incorrect</span>
            </div>

            <div className="summary__stat">
              <strong>{total}</strong>
              <span>Total Questions</span>
            </div>
          </div>

          {aiSummary && (
            <div style={{ marginTop: "20px", textAlign: "left", padding: "16px", background: "rgba(255, 255, 255, 0.05)", borderRadius: "8px" }}>
              <h3 style={{ fontSize: "1rem", marginBottom: "8px" }}>AI Summary & Recommendations</h3>
              <p style={{ fontSize: "0.9rem", color: "#ccc" }}>{aiSummary}</p>
            </div>
          )}
        </div>
      )}

      <div className="summary__actions">
        <button
          className="summary__review"
          onClick={() =>
            navigate("/review", {
              state: {
                answers: answers,
                attemptId: attemptIdParam || attemptData?.id,
              },
            })
          }
        >
          Review Answers
        </button>

        <button className="summary__back" onClick={() => navigate("/quizzes")}>
          Back to Quizzes
        </button>
      </div>
    </section>
  );
}

export default Summary;
