import { useState } from "react";
import { Link } from "react-router-dom";
import { Mail, ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";
import { toast } from "sonner";
import { API_BASE_URL } from "../config/api";
import "./ForgotPassword.css";

function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);
  const handleSubmit = async (e) => {
    e.preventDefault();

    setLoading(true);

    try {
      const response = await fetch(
        `${API_BASE_URL}/auth/forgot-password`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            email: email,
          }),
        },
      );

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail?.[0]?.msg || "Failed to send reset link");
      }
      console.log("Forgot password response:", data);
      toast.success("Reset link sent! Check your inbox.");
      setSubmitted(true);
    } catch (error) {
      console.error("Forgot password error:", error);
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };
  return (
    <div className="forgot-container">
      <div className="forgot-glow" aria-hidden="true" />

      <div className="forgot-card">
        {/* Brand Header */}
        <Link to="/" className="forgot-brand">
          <span className="forgot-brand__icon">Q</span>
          <span className="forgot-brand__text">Quiza</span>
        </Link>

        <div className="forgot-header">
          <h1>Reset your password</h1>
          <p>
            Enter your email address and we'll send you a link to reset your
            password.
          </p>
        </div>

        {submitted ? (
          <div>
            <div className="forgot-success-box">
              <CheckCircle2
                size={24}
                color="#35D07F"
                style={{ margin: "0 auto 8px" }}
              />
              <p>
                A password reset link has been sent to <strong>{email}</strong>.
                Please check your inbox.
              </p>
            </div>

            <div className="forgot-footer">
              <Link to="/signin" className="forgot-back-link">
                <ArrowLeft size={16} /> Back to Sign In
              </Link>
            </div>
          </div>
        ) : (
          <form className="forgot-form" onSubmit={handleSubmit}>
            {/* Email Field */}
            <div className="forgot-field">
              <label htmlFor="forgot-email">Email Address</label>
              <div className="forgot-input-wrap">
                <Mail size={18} className="forgot-input-icon" />
                <input
                  id="forgot-email"
                  type="email"
                  required
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="forgot-input"
                />
              </div>
            </div>

            {/* Submit Button */}

            <button
              type="submit"
              className="forgot-submit-btn"
              disabled={loading}
            >
              {loading ? "Sending link..." : "Send Reset Link"}
              {!loading && <ArrowRight size={16} />}
            </button>

            {/* Footer Back */}
            <div className="forgot-footer">
              <Link to="/signin" className="forgot-back-link">
                <ArrowLeft size={16} /> Back to Sign In
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default ForgotPassword;
