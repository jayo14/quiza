import "./Settings.css";

function Settings() {
  return (
    <section className="settings">
      <div className="settings__header">
        <h1>Settings</h1>
        <p>Manage your account and preferences.</p>
      </div>

      {/* Profile */}
      <div className="settings__card">
        <h2>Profile</h2>

        <div className="settings__field">
          <label htmlFor="name">Name</label>
          <input id="name" type="text" placeholder="Enter your name" />
        </div>

        <div className="settings__field">
          <label htmlFor="email">Email</label>
          <input id="email" type="email" placeholder="Enter your email" />
        </div>
      </div>

      {/* Preferences */}
      <div className="settings__card">
        <h2>Preferences</h2>

        <div className="settings__option">
          <div>
            <h3>Email Notifications</h3>
            <p>Receive updates about your quizzes and progress.</p>
          </div>

          <input type="checkbox" id="email-notifications" />
        </div>

        <div className="settings__option">
          <div>
            <h3>Study Reminders</h3>
            <p>Get reminders to keep up with your learning.</p>
          </div>

          <input type="checkbox" id="study-reminders" />
        </div>
      </div>
    </section>
  );
}

export default Settings;
