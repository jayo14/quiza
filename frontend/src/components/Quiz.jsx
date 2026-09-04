import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  getQuizQuestions,
  getQuiz,
  listQuizzes,
  startAttempt,
  submitAttempt,
} from "../services/apiClient";
import "./Quiz.css";

function Quiz() {
  const [searchParams] = useSearchParams();
  const quizIdParam = searchParams.get("id");
  const attemptIdParam = searchParams.get("attempt_id");

  const [quizTitle, setQuizTitle] = useState("Quiz");
  const [questions, setQuestions] = useState([]);
  const [attemptId, setAttemptId] = useState(attemptIdParam || null);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState("");
  const [userAnswers, setUserAnswers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const navigate = useNavigate();

  useEffect(() => {
    const initQuiz = async () => {
      try {
        setLoading(true);
        let targetQuizId = quizIdParam;

        if (!targetQuizId) {
          const quizzes = await listQuizzes();
          const readyQuizzes = (quizzes || []).filter(
            (q) => q.status === "ready" || !q.status
          );
          if (readyQuizzes.length > 0) {
            targetQuizId = readyQuizzes[0].id;
          } else {
            setError("No ready quizzes available. Please generate a quiz first.");
            setLoading(false);
            return;
          }
        }

        const quizData = await getQuiz(targetQuizId).catch(() => null);
        if (quizData) setQuizTitle(quizData.title || "Quiz");

        const qList = await getQuizQuestions(targetQuizId);
        setQuestions(qList || []);

        let currentAttemptId = attemptIdParam;
        if (!currentAttemptId) {
          const attempt = await startAttempt(targetQuizId);
          currentAttemptId = attempt.id;
        }
        setAttemptId(currentAttemptId);
      } catch (err) {
        console.error("Failed to load quiz:", err);
        setError(err.message || "Failed to load quiz questions");
      } finally {
        setLoading(false);
      }
    };

    initQuiz();
  }, [quizIdParam, attemptIdParam]);

  const question = questions[currentQuestion];

  const handleAnswer = (option) => {
    setSelectedAnswer(option);
  };

  const handleNext = async () => {
    if (!selectedAnswer || !question) return;

    const currentAnswerObj = {
      question_id: question.id,
      selected_answer: selectedAnswer,
      time_taken_seconds: null,
    };

    const newAnswers = [...userAnswers, currentAnswerObj];
    setUserAnswers(newAnswers);

    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion(currentQuestion + 1);
      setSelectedAnswer("");
    } else {
      setSubmitting(true);
      try {
        const result = await submitAttempt(attemptId, newAnswers);
        navigate(`/summary?attempt_id=${result.id}`, {
          state: { attemptResult: result },
        });
      } catch (err) {
        console.error("Failed to submit attempt:", err);
        alert(err.message || "Failed to submit attempt");
      } finally {
        setSubmitting(false);
      }
    }
  };

  if (loading) {
    return (
      <section className="quiz">
        <p>Loading quiz questions...</p>
      </section>
    );
  }

  if (error || questions.length === 0) {
    return (
      <section className="quiz">
        <p style={{ color: "#ef4444" }}>{error || "No questions found for this quiz."}</p>
        <button className="quiz__next" onClick={() => navigate("/upload")}>
          Generate a Quiz
        </button>
      </section>
    );
  }

  const options = question.options || [];

  return (
    <section className="quiz">
      <div className="quiz__header">
        <div>
          <h1>{quizTitle}</h1>
          <p>Test your knowledge and see how much you know.</p>
        </div>

        <span className="quiz__progress">
          Question {currentQuestion + 1} of {questions.length}
        </span>
      </div>

      <div className="quiz__card">
        <h2>{question.question_text || question.question || question.text}</h2>

        <div className="quiz__options">
          {options.map((option) => (
            <button
              key={option}
              className={selectedAnswer === option ? "selected" : ""}
              onClick={() => handleAnswer(option)}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      <div className="quiz__footer">
        <button
          className="quiz__next"
          onClick={handleNext}
          disabled={!selectedAnswer || submitting}
        >
          {submitting
            ? "Submitting..."
            : currentQuestion === questions.length - 1
            ? "Finish Quiz"
            : "Next Question"}
        </button>
      </div>
    </section>
  );
}

export default Quiz;
