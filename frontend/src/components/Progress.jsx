import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { Sparkles, AlertTriangle, CheckCircle2, Target } from "lucide-react";
import {
  listWeaknesses,
  listTopicMastery,
  listAttempts,
  generatePractice,
  listMaterials,
} from "../services/apiClient";
import "./Progress.css";

function Progress() {
  const navigate = useNavigate();
  const [weaknesses, setWeaknesses] = useState([]);
  const [topics, setTopics] = useState([]);
  const [attempts, setAttempts] = useState([]);
  const [materials, setMaterials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        const [wList, tList, aList, mList] = await Promise.all([
          listWeaknesses().catch(() => []),
          listTopicMastery().catch(() => []),
          listAttempts().catch(() => []),
          listMaterials().catch(() => []),
        ]);
        setWeaknesses(wList || []);
        setTopics(tList || []);
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
      toast.warning("Please upload study material first before generating practice quizzes.");
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
      toast.error(err.message || "Failed to generate targeted practice quiz");
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

          {weaknesses.length > 0 && (
            <section className="progress__topics" style={{ marginBottom: "32px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
                <AlertTriangle size={20} color="#ef4444" />
                <h2 style={{ margin: 0 }}>Identified Weakness Areas</h2>
              </div>

              {weaknesses.map((item) => {
                const accPercent = Math.round((item.accuracy || 0) * 100);
                return (
                  <div className="progress__topic" key={item.id || item.topic} style={{ borderLeft: "4px solid #ef4444" }}>
                    <div className="progress__topic-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <strong style={{ fontSize: "1.05rem" }}>{item.topic}</strong>
                        <span
                          style={{
                            marginLeft: "10px",
                            padding: "2px 8px",
                            borderRadius: "4px",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            background: item.severity === "high" ? "#fee2e2" : "#fef3c7",
                            color: item.severity === "high" ? "#ef4444" : "#d97706",
                          }}
                        >
                          {item.severity?.toUpperCase() || "MEDIUM"} SEVERITY ({accPercent}% Accuracy)
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
                          padding: "8px 14px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          fontSize: "0.85rem",
                          fontWeight: 500,
                        }}
                      >
                        <Sparkles size={14} /> Practice Topic
                      </button>
                    </div>

                    <div className="progress__bar" style={{ marginTop: "10px" }}>
                      <div
                        className="progress__bar-fill"
                        style={{
                          width: `${accPercent}%`,
                          background: "#ef4444",
                        }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </section>
          )}

          <section className="progress__topics">
            <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "16px" }}>
              <Target size={20} color="#6366f1" />
              <h2 style={{ margin: 0 }}>Topic Mastery Breakdown</h2>
            </div>

            {topics.length === 0 ? (
              <div style={{ textAlign: "center", padding: "32px 0", color: "var(--text-secondary)" }}>
                <p>No topic analytics found yet. Complete a quiz to analyze topic performance!</p>
              </div>
            ) : (
              topics.map((item) => {
                const accPercent = Math.round((item.accuracy || 0) * 100);
                const isMastered = item.status === "Mastered";
                const isDeveloping = item.status === "Developing";

                return (
                  <div className="progress__topic" key={item.topic}>
                    <div className="progress__topic-header" style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <div>
                        <strong>{item.topic}</strong>
                        <span
                          style={{
                            marginLeft: "10px",
                            padding: "2px 8px",
                            borderRadius: "4px",
                            fontSize: "0.75rem",
                            fontWeight: 600,
                            background: isMastered ? "#d1fae5" : isDeveloping ? "#e0f2fe" : "#fee2e2",
                            color: isMastered ? "#10b981" : isDeveloping ? "#0284c7" : "#ef4444",
                          }}
                        >
                          {item.status.toUpperCase()} ({accPercent}%)
                        </span>
                      </div>
                      <button
                        onClick={() => handleGeneratePractice(item.topic)}
                        disabled={generating}
                        style={{
                          background: isMastered ? "transparent" : "#6366f1",
                          color: isMastered ? "var(--text-secondary)" : "white",
                          border: isMastered ? "1px solid var(--border-color)" : "none",
                          borderRadius: "6px",
                          padding: "6px 12px",
                          cursor: "pointer",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "0.85rem",
                        }}
                      >
                        <Sparkles size={14} /> Practice
                      </button>
                    </div>

                    <div className="progress__bar" style={{ marginTop: "8px" }}>
                      <div
                        className="progress__bar-fill"
                        style={{
                          width: `${accPercent}%`,
                          background: isMastered ? "#10b981" : isDeveloping ? "#f59e0b" : "#ef4444",
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
