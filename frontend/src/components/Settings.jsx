import { useEffect, useState } from "react";
import "./Settings.css";

function Settings() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    const getProfile = async () => {
      try {
        const token = localStorage.getItem("access_token");
        const response = await fetch(
          "https://quiza-urmm.onrender.com/api/v1/users/me",
          {
            method: "GET",
            headers: {
              Authorization: `Bearer ${token}`,
            },
          },
        );

        const data = await response.json();

        if (!response.ok) {
          throw new Error(data.detail || "Failed to get profile");
        }

        setProfile(data);
      } catch (error) {
        console.error("Get profile error:", error);
      } finally {
        setLoading(false);
      }
    };

    getProfile();
  }, []);
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
          <input
            id="name"
            type="text"
            value={loading ? "" : profile?.name || ""}
          />
        </div>

        <div className="settings__field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={loading ? "" : profile?.email || ""}
          />
        </div>
      </div>

      {/* Preferences  */}
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
