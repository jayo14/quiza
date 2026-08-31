import { Link } from "react-router-dom";
import "./RecentQuizzes.css";

function RecentQuizzes() {
  return (
    <section className="recent-quizzes">
      <div className="recent-quizzes__header">
        <div>
          <h2>Recent Quizzes</h2>
          <p>Keep track of your latest quiz activity.</p>
        </div>

        <Link to="/quizzes" className="recent-quizzes__view-all">
          View All
        </Link>
      </div>

      <div className="recent-quizzes__list">
        <div className="recent-quiz">
          <div className="recent-quiz__info">
            <h3>HTML & CSS Basics</h3>
            <p>Completed yesterday</p>
          </div>

          <div className="recent-quiz__score">
            <span>92%</span>
            <small>Score</small>
          </div>
        </div>

        <div className="recent-quiz">
          <div className="recent-quiz__info">
            <h3>JavaScript Fundamentals</h3>
            <p>Completed 2 days ago</p>
          </div>

          <div className="recent-quiz__score">
            <span>85%</span>
            <small>Score</small>
          </div>
        </div>

        <div className="recent-quiz">
          <div className="recent-quiz__info">
            <h3>React Basics</h3>
            <p>Completed 4 days ago</p>
          </div>

          <div className="recent-quiz__score">
            <span>78%</span>
            <small>Score</small>
          </div>
        </div>
      </div>
    </section>
  );
}

export default RecentQuizzes;
