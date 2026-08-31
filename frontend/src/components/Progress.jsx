import "./Progress.css";

function Progress() {
  return (
    <section className="progress">
      <div className="progress__header">
        <div>
          <h1>Your Progress</h1>
          <p>Track your learning progress and see where you can improve.</p>
        </div>
      </div>

      <div className="progress__overview">
        <div className="progress__card">
          <span>Overall Score</span>
          <strong>82%</strong>
          <p>Across all quizzes</p>
        </div>

        <div className="progress__card">
          <span>Quizzes Completed</span>
          <strong>12</strong>
          <p>This month</p>
        </div>

        <div className="progress__card">
          <span>Questions Answered</span>
          <strong>145</strong>
          <p>Keep going!</p>
        </div>
      </div>

      <section className="progress__topics">
        <h2>Topic Performance</h2>

        <div className="progress__topic">
          <div className="progress__topic-header">
            <span>HTML</span>
            <strong>92%</strong>
          </div>

          <div className="progress__bar">
            <div className="progress__bar-fill" style={{ width: "92%" }}></div>
          </div>
        </div>

        <div className="progress__topic">
          <div className="progress__topic-header">
            <span>CSS</span>
            <strong>88%</strong>
          </div>

          <div className="progress__bar">
            <div className="progress__bar-fill" style={{ width: "88%" }}></div>
          </div>
        </div>

        <div className="progress__topic">
          <div className="progress__topic-header">
            <span>JavaScript</span>
            <strong>74%</strong>
          </div>

          <div className="progress__bar">
            <div className="progress__bar-fill" style={{ width: "74%" }}></div>
          </div>
        </div>

        <div className="progress__topic">
          <div className="progress__topic-header">
            <span>React</span>
            <strong>68%</strong>
          </div>

          <div className="progress__bar">
            <div className="progress__bar-fill" style={{ width: "68%" }}></div>
          </div>
        </div>
      </section>
    </section>
  );
}

export default Progress;
