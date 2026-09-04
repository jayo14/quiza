import { useLocation, useNavigate } from "react-router-dom";
import "./Summary.css";

function Summary() {
  const location = useLocation();
  const navigate = useNavigate();
  const score = location.state?.score ?? 0;
  const total = location.state?.total ?? 0;
  const answers = location.state?.answers ?? [];
  const percentage = total > 0 ? Math.round((score / total) * 100) : 0;
  const incorrect = total - score;

  return (
    <section className="summary">
      <div className="summary__header">
        <h1>Quiz Complete!</h1>
        <p>Here's how you performed on your quiz.</p>
      </div>

      <div className="summary__card">
        <h2>HTML & CSS Basics</h2>

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
      </div>

      <div className="summary__actions">
        <button
          className="summary__review"
          onClick={() =>
            navigate("/review", {
              state: {
                answers: answers,
              },
            })
          }
        >
          Review Answers
        </button>

        <button className="summary__back" onClick={() => navigate("/quizzes")}>
          Back to Quizes
        </button>
      </div>
    </section>
  );
}

export default Summary;
