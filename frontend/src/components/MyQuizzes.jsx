import "./MyQuizzes.css";

import { useNavigate } from "react-router-dom";
import { Plus } from "lucide-react";

function MyQuizzes() {
  const navigate = useNavigate();

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

      <div className="my-quizzes__list">
        <div className="my-quiz">
          <div className="my-quiz__info">
            <h3>HTML & CSS Basics</h3>
            <p>Completed yesterday</p>
          </div>

          <div className="my-quiz__score">
            <span>92%</span>
            <small>Score</small>
          </div>

          <button onClick={() => navigate("/quiz")}>Start Quiz</button>
        </div>

        <div className="my-quiz">
          <div className="my-quiz__info">
            <h3>JavaScript Fundamentals</h3>
            <p>Completed 2 days ago</p>
          </div>

          <div className="my-quiz__score">
            <span>85%</span>
            <small>Score</small>
          </div>

          <button onClick={() => navigate("/quiz")}>Start Quiz</button>
        </div>

        <div className="my-quiz">
          <div className="my-quiz__info">
            <h3>React Basics</h3>
            <p>Completed 4 days ago</p>
          </div>

          <div className="my-quiz__score">
            <span>78%</span>
            <small>Score</small>
          </div>

          <button onClick={() => navigate("/quiz")}>Start Quiz</button>
        </div>

        <div className="my-quiz">
          <div className="my-quiz__info">
            <h3>Computer Science Basics</h3>
            <p>Completed 1 week ago</p>
          </div>

          <div className="my-quiz__score">
            <span>88%</span>
            <small>Score</small>
          </div>

          <button onClick={() => navigate("/quiz")}>Start Quiz</button>
        </div>
      </div>
    </section>
  );
}

export default MyQuizzes;
