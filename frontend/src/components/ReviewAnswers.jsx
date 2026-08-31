import { useLocation, useNavigate } from "react-router-dom";
import "./ReviewAnswers.css";

function ReviewAnswers() {
  const location = useLocation();
  const navigate = useNavigate();

  const answers = location.state?.answers || [];

  return (
    <section className="review-answers">
      <div className="review-answers__header">
        <h1>Review Answers</h1>
        <p>See how you answered each question.</p>
      </div>

      <div className="review-answers__list">
        {answers.map((item, index) => (
          <div
            className={`review-answers__card ${
              item.isCorrect ? "correct" : "incorrect"
            }`}
            key={index}
          >
            <div className="review-answers__question">
              <span>Question {index + 1}</span>
              <h2>{item.question}</h2>
            </div>

            <div className="review-answers__result">
              <div>
                <span>Your answer</span>
                <strong>{item.selectedAnswer}</strong>
              </div>

              <div>
                <span>Correct answer</span>
                <strong>{item.correctAnswer}</strong>
              </div>
            </div>

            <p className="review-answers__status">
              {item.isCorrect ? "✓ Correct" : "✕ Incorrect"}
            </p>
          </div>
        ))}
      </div>

      <button
        className="review-answers__back"
        onClick={() => navigate("/quizzes")}
      >
        Back to Quizes
      </button>
    </section>
  );
}

export default ReviewAnswers;
