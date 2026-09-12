import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { CheckCircle2, ChevronLeft, ChevronRight, Loader2 } from "lucide-react";
import { toast } from "sonner";
import {
  getQuizQuestions,
  getQuiz,
  listQuizzes,
  startAttempt,
  submitAttempt,
  getAttempt,
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
  const [answersByQuestionId, setAnswersByQuestionId] = useState({});
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
        if (currentAttemptId) {
          try {
            const attemptInfo = await getAttempt(currentAttemptId);
            if (attemptInfo && attemptInfo.status === "completed") {
              currentAttemptId = null;
            }
          } catch {
            currentAttemptId = null;
          }
        }

        if (!currentAttemptId) {
          const attempt = await startAttempt(targetQuizId);
          currentAttemptId = attempt.id;
          navigate(`/quiz?id=${targetQuizId}&attempt_id=${currentAttemptId}`, {
            replace: true,
          });
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
  const selectedAnswer = question ? (answersByQuestionId[question.id] || "") : "";

  const handleAnswer = (option) => {
    if (!question) return;
    setAnswersByQuestionId((prev) => ({
      ...prev,
      [question.id]: option,
    }));
  };

  const handlePrevious = () => {
    if (currentQuestion > 0) {
      setCurrentQuestion((prev) => prev - 1);
    }
  };

  const handleNext = async () => {
    if (currentQuestion < questions.length - 1) {
      setCurrentQuestion((prev) => prev + 1);
      return;
    }

    setSubmitting(true);
    try {
      const formattedAnswers = questions
        .map((q) => {
          const ans = answersByQuestionId[q.id];
          if (!ans) return null;
          return {
            question_id: q.id,
            selected_answer: ans,
            time_taken_seconds: null,
          };
        })
        .filter(Boolean);

      const result = await submitAttempt(attemptId, formattedAnswers);
      navigate(`/summary?attempt_id=${result.id}`, {
        replace: true,
        state: { attemptResult: result },
      });
    } catch (err) {
      console.error("Failed to submit attempt:", err);
      toast.error(err.message || "Failed to submit attempt");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <section className="quiz quiz--loading">
        <div className="quiz__loading-card">
          <Loader2 size={36} className="quiz__spin" />
          <h2>Preparing Quiz...</h2>
          <p>Retrieving your questions and initializing your session.</p>
        </div>
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

  const options =
    question?.options && question.options.length > 0
      ? question.options
      : (question?.question_type === "true_false" ? ["True", "False"] : []);

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
          type="button"
          className="quiz__prev"
          onClick={handlePrevious}
          disabled={currentQuestion === 0 || submitting}
        >
          <ChevronLeft size={16} />
          <span>Previous</span>
        </button>

        <button
          type="button"
          className="quiz__next"
          onClick={handleNext}
          disabled={submitting}
        >
          {submitting ? (
            <>
              <Loader2 size={16} className="quiz__spin" />
              <span>Submitting...</span>
            </>
          ) : currentQuestion === questions.length - 1 ? (
            <>
              <span>Finish Quiz</span>
              <CheckCircle2 size={16} />
            </>
          ) : (
            <>
              <span>Next Question</span>
              <ChevronRight size={16} />
            </>
          )}
        </button>
      </div>
    </section>
  );
}

export default Quiz;
