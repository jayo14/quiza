import { useEffect, useState, useRef } from "react";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../config/api";
import { Camera, Loader2 } from "lucide-react";
import { toast } from "sonner";
import "./Settings.css";

function Settings() {
  const { user, token, refreshUser } = useAuth();
  const [profile, setProfile] = useState(user);
  const [loading, setLoading] = useState(!user);
  const [saving, setSaving] = useState(false);
  const [uploadingAvatar, setUploadingAvatar] = useState(false);
  const fileInputRef = useRef(null);

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

  const handleSaveProfile = async () => {
    setSaving(true);
    try {
      const response = await fetch(
        `${API_BASE_URL}/users/me`,
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ name: profile?.name }),
        },
      );

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to update profile");
      }

      setProfile(data);
      localStorage.setItem("user", JSON.stringify(data));
      refreshUser();
      toast.success("Profile updated successfully!");
    } catch (error) {
      toast.error(error.message);
    } finally {
      setSaving(false);
    }
  };

  const handleAvatarUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowedTypes = ["image/jpeg", "image/png", "image/webp", "image/gif"];
    if (!allowedTypes.includes(file.type)) {
      toast.error("Please upload a JPEG, PNG, WebP, or GIF image.");
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      toast.error("Image must be under 5 MB.");
      return;
    }

    setUploadingAvatar(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(
        `${API_BASE_URL}/users/me/avatar`,
        {
          method: "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
          body: formData,
        },
      );

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || "Failed to upload avatar");
      }

      setProfile(data);
      localStorage.setItem("user", JSON.stringify(data));
      refreshUser();
      toast.success("Profile image updated!");
    } catch (error) {
      toast.error(error.message);
    } finally {
      setUploadingAvatar(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  return (
    <section className="settings">
      <div className="settings__header">
        <h1>Settings</h1>
        <p>Manage your account and preferences.</p>
      </div>

      {/* Profile */}
      <div className="settings__card">
        <h2>Profile</h2>

        <div className="settings__avatar-section">
          <div className="settings__avatar">
            {profile?.profile_image ? (
              <img src={profile.profile_image} alt="Profile" />
            ) : (
              <span>{profile?.name?.charAt(0)?.toUpperCase() || "U"}</span>
            )}
          </div>
          <div className="settings__avatar-actions">
            <button
              type="button"
              className="settings__avatar-btn"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploadingAvatar}
            >
              {uploadingAvatar ? (
                <Loader2 size={16} className="settings__spin" />
              ) : (
                <Camera size={16} />
              )}
              {uploadingAvatar ? "Uploading..." : "Change Photo"}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              onChange={handleAvatarUpload}
              style={{ display: "none" }}
            />
            <span className="settings__avatar-hint">JPEG, PNG, WebP, or GIF. Max 5 MB.</span>
          </div>
        </div>

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
            disabled
          />
        </div>

        <button
          type="button"
          className="settings__save-btn"
          onClick={handleSaveProfile}
          disabled={saving}
        >
          {saving ? "Saving..." : "Save Changes"}
        </button>
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
