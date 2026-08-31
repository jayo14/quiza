import { Link } from "react-router-dom";
import "./ContinueLearning.css";

function ContinueLearning() {
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
          <span className="continue-learning__label">In Progress</span>
          <h3>JavaScript Fundamentals</h3>
          <p>Continue your quiz on JavaScript basics.</p>
        </div>

        <div className="continue-learning__progress">
          <div className="progress-info">
            <span>Progress</span>
            <span>65%</span>
          </div>

          <div className="progress-bar">
            <div className="progress-bar__fill"></div>
          </div>
        </div>

        <Link to="/quiz" className="continue-learning__button">
          Continue
        </Link>
      </div>
    </section>
  );
}

export default ContinueLearning;
