import { Link } from "react-router-dom";
import "./Dashboard.css";

import StatCard from "./StatCard.jsx";
import ContinueLearning from "./ContinueLearning.jsx";
import RecentQuizzes from "./RecentQuizzes.jsx";

function Dashboard() {
  return (
    <section className="dashboard">
      <div className="dashboard__welcome">
        <div>
          <h1>Ready to sharpen a few more topics today?</h1>

          <p>Upload your study material and let Quiza turn it into a quiz.</p>
        </div>

        <Link to="/upload" className="dashboard__upload-button">
          Upload Material
        </Link>
      </div>

      <section className="dashboard__overview">
        <h2>Overview</h2>

        <div className="dashboard__stat">
          <StatCard title="Quizzes Taken" value="12" description="This month" />

          <StatCard
            title="Average Score"
            value="78%"
            description="Across all quizzes"
          />

          <StatCard
            title="Questions Answered"
            value="145"
            description="Keep it up"
          />

          <StatCard
            title="Weak Topics"
            value="3"
            description="Topics to improve"
          />
        </div>
      </section>

      <ContinueLearning />

      <RecentQuizzes />
    </section>
  );
}

export default Dashboard;
