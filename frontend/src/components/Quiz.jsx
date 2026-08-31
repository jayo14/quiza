import { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Quiz.css";

const questions = [
  {
    question: "Which language is used to structure a webpage?",
    options: ["JavaScript", "HTML", "CSS", "Python"],
    answer: "HTML",
  },
  {
    question: "Which language is used to style a webpage?",
    options: ["HTML", "CSS", "Python", "Java"],
    answer: "CSS",
  },
  {
    question: "Which HTML tag is used to create a paragraph?",
    options: ["<h1>", "<p>", "<div>", "<img>"],
    answer: "<p>",
  },
  {
    question: "Which CSS property changes the text color?",
    options: ["font-size", "background", "color", "display"],
    answer: "color",
  },
];

function Quiz() {
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [selectedAnswer, setSelectedAnswer] = useState("");
  const [score, setScore] = useState(0);
  const [userAnswers, setUserAnswers] = useState([]);

  const navigate = useNavigate();

  const question = questions[currentQuestion];

  const handleAnswer = (answer) => {
    setSelectedAnswer(answer);
  };

  const handleNext = () => {
    if (!selectedAnswer) return;

    const isCorrect = selectedAnswer === question.answer;

    const newScore = isCorrect ? score + 1 : score;

    const newAnswers = [
      ...userAnswers,
      {
        question: question.question,
        selectedAnswer: selectedAnswer,
        correctAnswer: question.answer,
        isCorrect: isCorrect,
      },
    ];

    if (currentQuestion < questions.length - 1) {
      setScore(newScore);
      setUserAnswers(newAnswers);
      setCurrentQuestion(currentQuestion + 1);
      setSelectedAnswer("");
    } else {
      navigate("/summary", {
        state: {
          score: newScore,
          total: questions.length,
          answers: newAnswers,
        },
      });
    }
  };

  return (
    <section className="quiz">
      <div className="quiz__header">
        <div>
          <h1>HTML & CSS Basics</h1>
          <p>Test your knowledge and see how much you know.</p>
        </div>

        <span className="quiz__progress">
          Question {currentQuestion + 1} of {questions.length}
        </span>
      </div>

      <div className="quiz__card">
        <h2>{question.question}</h2>

        <div className="quiz__options">
          {question.options.map((option) => (
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
          disabled={!selectedAnswer}
        >
          {currentQuestion === questions.length - 1
            ? "Finish Quiz"
            : "Next Question"}
        </button>
      </div>
    </section>
  );
}

export default Quiz;
