import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  listQuizzes,
  listAttempts,
  listWeaknesses,
  getHealth,
} from "../services/apiClient";
import "./Dashboard.css";
import StatCard from "./StatCard.jsx";
import ContinueLearning from "./ContinueLearning.jsx";
import RecentQuizzes from "./RecentQuizzes.jsx";

function Dashboard() {
  const [quizzes, setQuizzes] = useState([]);
  const [attempts, setAttempts] = useState([]);
  const [weaknesses, setWeaknesses] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true);
        const [qList, aList, wList, hStatus] = await Promise.all([
          listQuizzes().catch(() => []),
          listAttempts().catch(() => []),
          listWeaknesses().catch(() => []),
          getHealth().catch(() => ({ status: "unavailable" })),
        ]);

        setQuizzes(qList || []);
        setAttempts(aList || []);
        setWeaknesses(wList || []);
        setHealth(hStatus?.status || "online");
      } catch (err) {
        console.error("Failed to load dashboard data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const totalAttempts = attempts.length;
  const totalQuestionsAnswered = attempts.reduce(
    (acc, a) => acc + (a.total_questions || 0),
    0
  );
  const totalScoreSum = attempts.reduce((acc, a) => acc + (a.score || 0), 0);
  const avgScore =
    totalQuestionsAnswered > 0
      ? `${Math.round((totalScoreSum / totalQuestionsAnswered) * 100)}%`
      : "0%";

  return (
    <section className="dashboard">
      <div className="dashboard__welcome">
        <div>
          <h1>Ready to sharpen a few more topics today?</h1>
          <p>
            Upload your study material and let Quiza turn it into a quiz.
            {health && (
              <span style={{ marginLeft: "12px", fontSize: "0.85rem", opacity: 0.8 }}>
                (Server API: {health})
              </span>
            )}
          </p>
        </div>

        <Link to="/upload" className="dashboard__upload-button">
          Upload Material
        </Link>
      </div>

      <section className="dashboard__overview">
        <h2>Overview</h2>

        <div className="dashboard__stat">
          <StatCard
            title="Quizzes Taken"
            value={loading ? "..." : String(totalAttempts)}
            description="Total attempts completed"
          />

          <StatCard
            title="Average Score"
            value={loading ? "..." : avgScore}
            description="Across all quizzes"
          />

          <StatCard
            title="Questions Answered"
            value={loading ? "..." : String(totalQuestionsAnswered)}
            description="Keep it up"
          />

          <StatCard
            title="Weak Topics"
            value={loading ? "..." : String(weaknesses.length)}
            description="Topics to improve"
          />
        </div>
      </section>

      <ContinueLearning quizzes={quizzes} attempts={attempts} />
      <RecentQuizzes quizzes={quizzes} attempts={attempts} />
    </section>
  );
}

export default Dashboard;
