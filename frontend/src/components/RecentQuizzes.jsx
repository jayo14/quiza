import { Link, useNavigate } from "react-router-dom";
import "./RecentQuizzes.css";

function RecentQuizzes({ quizzes = [], attempts = [] }) {
  const navigate = useNavigate();
  const validQuizzes = quizzes.filter(
    (quiz) => (quiz.status || "").toLowerCase() !== "failed"
  );
  const recentItems = validQuizzes.slice(0, 4);

  const getQuizAttemptInfo = (quizId) => {
    const quizAttempts = (attempts || []).filter(
      (a) => a.quiz_id === quizId && a.status === "completed"
    );
    if (quizAttempts.length === 0) return null;
    const bestScore = Math.max(
      ...quizAttempts.map((a) => Math.round((a.accuracy ?? 0) * 100))
    );
    return { count: quizAttempts.length, bestScore };
  };

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

      {recentItems.length === 0 ? (
        <p style={{ color: "#888", padding: "16px 0" }}>
          No recent quizzes. Create your first quiz by uploading study materials!
        </p>
      ) : (
        <div className="recent-quizzes__list">
          {recentItems.map((quiz) => {
            const attemptInfo = getQuizAttemptInfo(quiz.id);

            return (
              <div
                className="recent-quiz"
                key={quiz.id}
                onClick={() => navigate(`/quiz?id=${quiz.id}`)}
                style={{ cursor: "pointer" }}
              >
                <div className="recent-quiz__info">
                  <h3>{quiz.title || "Untitled Quiz"}</h3>
                  <p>
                    {quiz.question_count ?? quiz.questions?.length ?? 0} Questions · {quiz.difficulty || "medium"}
                    {attemptInfo && ` · ${attemptInfo.count} ${attemptInfo.count === 1 ? "attempt" : "attempts"}`}
                  </p>
                </div>

                <div className="recent-quiz__score">
                  {attemptInfo ? (
                    <>
                      <span>{attemptInfo.bestScore}%</span>
                      <small>Best Score</small>
                    </>
                  ) : (
                    <>
                      <span>Start</span>
                      <small>Quiz</small>
                    </>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export default RecentQuizzes;
