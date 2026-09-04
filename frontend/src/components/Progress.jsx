import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Sparkles } from "lucide-react";
import {
  listWeaknesses,
  listAttempts,
  generatePractice,
  listMaterials,
} from "../services/apiClient";
import "./Progress.css";

function Progress() {
  const navigate = useNavigate();
  const [weaknesses, setWeaknesses] = useState([]);
  const [attempts, setAttempts] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [wList, aList, mList] = await Promise.all([
          listWeaknesses().catch(() => []),
          listAttempts().catch(() => []),
          listMaterials().catch(() => []),
        ]);
        setWeaknesses(wList || []);
        setAttempts(aList || []);
        setMaterials(mList || []);
      } catch (err) {
        console.error("Failed to load progress:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const totalQuestionsAnswered = attempts.reduce(
    (acc, a) => acc + (a.total_questions || 0),
    0
  );
  const totalScoreSum = attempts.reduce((acc, a) => acc + (a.score || 0), 0);
  const overallAvg =
    totalQuestionsAnswered > 0
      ? Math.round((totalScoreSum / totalQuestionsAnswered) * 100)
      : 0;

  const handleGeneratePractice = async (topicName) => {
    if (materials.length === 0) {
      alert("Please upload study material first before generating practice quizzes.");
      navigate("/upload");
      return;
    }

    setGenerating(true);
    try {
      const practiceQuiz = await generatePractice({
        material_id: materials[0].id,
        number_of_questions: 5,
        topics: [topicName],
      });
      navigate(`/quiz?id=${practiceQuiz.id}`);
    } catch (err) {
      alert(err.message || "Failed to generate targeted practice quiz");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <section className="progress">
      <div className="progress__header">
        <div>
          <h1>Your Progress & Weakness Analytics</h1>
          <p>Track your learning progress and generate targeted AI practice quizzes.</p>
        </div>
      </div>

      {loading ? (
        <p>Loading analytics...</p>
      ) : (
        <>
          <div className="progress__overview">
            <div className="progress__card">
              <span>Overall Accuracy</span>
              <strong>{overallAvg}%</strong>
              <p>Across all attempt submissions</p>
            </div>

            <div className="progress__card">
              <span>Quizzes Attempted</span>
              <strong>{attempts.length}</strong>
              <p>Total attempts completed</p>
            </div>

            <div className="progress__card">
              <span>Questions Answered</span>
              <strong>{totalQuestionsAnswered}</strong>
              <p>Keep up the great work!</p>
            </div>
          </div>

          <section className="progress__topics">
            <h2>Identified Weaknesses & Topic Mastery</h2>

            {weaknesses.length === 0 ? (
              <p style={{ padding: "16px 0", color: "#888" }}>
                No weakness areas identified yet. Take more quizzes to generate topic analytics!
              </p>
            ) : (
              weaknesses.map((item) => {
                const mastery = Math.max(0, Math.round(100 - (item.weakness_score || 0) * 100));
                return (
                  <div className="progress__topic" key={item.id || item.topic}>
                    <div className="progress__topic-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <strong>{item.topic}</strong>
                        <span style={{ marginLeft: "8px", fontSize: "0.8rem", color: "#888" }}>
                          (Mastery: {mastery}%)
                        </span>
                      </div>
                      <button
                        onClick={() => handleGeneratePractice(item.topic)}
                        disabled={generating}
                        style={{
                          background: "#6366f1",
                          color: "white",
                          border: "none",
                          borderRadius: "6px",
                          padding: "6px 12px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "0.85rem",
                        }}
                      >
                        <Sparkles size={14} /> Practice Topic
                      </button>
                    </div>

                    <div className="progress__bar" style={{ marginTop: "8px" }}>
                      <div
                        className="progress__bar-fill"
                        style={{
                          width: `${mastery}%`,
                          background: mastery < 60 ? "#ef4444" : mastery < 80 ? "#f59e0b" : "#10b981",
                        }}
                      ></div>
                    </div>
                  </div>
                );
              })
            )}
          </section>
        </>
      )}
    </section>
  );
}

export default Progress;
