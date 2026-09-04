import { useEffect, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../config/api";
import "./Settings.css";

function Settings() {
  const { user, token } = useAuth();
  const [profile, setProfile] = useState(user);
  const [loading, setLoading] = useState(!user);

  useEffect(() => {
    const getProfile = async () => {
      if (!token) {
        setLoading(false);
        return;
      }
      try {
        const response = await fetch(
          `${API_BASE_URL}/users/me`,
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
  }, [token]);
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
            onChange={(e) =>
              setProfile((prev) => ({ ...prev, name: e.target.value }))
            }
          />
        </div>

        <div className="settings__field">
          <label htmlFor="email">Email</label>
          <input
            id="email"
            type="email"
            value={loading ? "" : profile?.email || ""}
            onChange={(e) =>
              setProfile((prev) => ({ ...prev, email: e.target.value }))
            }
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
