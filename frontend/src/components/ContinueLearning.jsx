import { Link } from "react-router-dom";
import "./ContinueLearning.css";

function ContinueLearning({ quizzes = [] }) {
  const validQuizzes = quizzes.filter(
    (quiz) => (quiz.status || "").toLowerCase() !== "failed"
  );
  const latestQuiz = validQuizzes[0];

  if (!latestQuiz) {
    return (
      <section className="continue-learning">
        <div className="continue-learning__header">
          <div>
            <h2>Continue Learning</h2>
            <p>Pick up where you left off.</p>
          </div>
          <Link to="/upload" className="continue-learning__view-all">
            Upload
          </Link>
        </div>
        <div className="continue-learning__card">
          <div className="continue-learning__info">
            <span className="continue-learning__label">Get Started</span>
            <h3>No Active Quizzes Yet</h3>
            <p>Upload a PDF, DOCX, or text file to generate smart AI quizzes.</p>
          </div>
          <Link to="/upload" className="continue-learning__button">
            Generate Quiz
          </Link>
        </div>
      </section>
    );
  }

  return (
    <section className="continue-learning">
      <div className="continue-learning__header">
        <div>
          <h2>Continue Learning</h2>
          <p>Pick up where you left off.</p>
        </div>
        <Link to="/quizzes" className="continue-learning__view-all">
          View All
        </Link>
      </div>

      <div className="continue-learning__card">
        <div className="continue-learning__info">
          <span className="continue-learning__label">Ready to Practice</span>
          <h3>{latestQuiz.title || "Latest Quiz"}</h3>
          <p>Practice {latestQuiz.question_count || 5} questions on {latestQuiz.title || "your study material"}.</p>
        </div>

        <Link to={`/quiz?id=${latestQuiz.id}`} className="continue-learning__button">
          Start Quiz
        </Link>
      </div>
    </section>
  );
}

export default ContinueLearning;
