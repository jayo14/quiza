import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Lock, Eye, EyeOff, CheckCircle2, ArrowRight, ArrowLeft } from "lucide-react";
import "./ResetPassword.css";

function ResetPassword() {
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const isMatching = confirmPassword.length > 0 && password === confirmPassword;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (password !== confirmPassword) return;

    setLoading(true);
    setTimeout(() => {
      setLoading(false);
      setSuccess(true);
    }, 600);
  };

  return (
    <div className="reset-container">
      <div className="reset-glow" aria-hidden="true" />

      <div className="reset-card">
        {/* Brand Header */}
        <Link to="/" className="reset-brand">
          <span className="reset-brand__icon">Q</span>
          <span className="reset-brand__text">Quiza</span>
        </Link>

        <div className="reset-header">
          <h1>Set new password</h1>
          <p>Create a strong password to secure your account.</p>
        </div>

        {success ? (
          <div>
            <div className="reset-success-box">
              <CheckCircle2 size={28} color="#35D07F" style={{ margin: "0 auto 8px" }} />
              <p>
                <strong>Password successfully updated!</strong>
                <br />
                You can now sign in with your new credentials.
              </p>
            </div>

            <button
              type="button"
              className="reset-submit-btn"
              onClick={() => navigate("/signin")}
            >
              Sign In Now <ArrowRight size={16} />
            </button>
          </div>
        ) : (
          <form className="reset-form" onSubmit={handleSubmit}>
            {/* New Password */}
            <div className="reset-field">
              <label htmlFor="reset-password">New Password</label>
              <div className="reset-input-wrap">
                <Lock size={18} className="reset-input-icon" />
                <input
                  id="reset-password"
                  type={showPassword ? "text" : "password"}
                  required
                  placeholder="Enter new password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="reset-input"
                />
                <button
                  type="button"
                  className="reset-toggle-btn"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </div>
            </div>

            {/* Confirm Password */}
            <div className="reset-field">
              <label htmlFor="reset-confirm-password">Confirm New Password</label>
              <div className="reset-input-wrap">
                <Lock size={18} className="reset-input-icon" />
                <input
                  id="reset-confirm-password"
                  type={showConfirm ? "text" : "password"}
                  required
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="reset-input"
                />
                {isMatching ? (
                  <span className="reset-match-icon" title="Passwords match">
                    <CheckCircle2 size={18} />
                  </span>
                ) : (
                  <button
                    type="button"
                    className="reset-toggle-btn"
                    onClick={() => setShowConfirm(!showConfirm)}
                    aria-label={showConfirm ? "Hide password" : "Show password"}
                  >
                    {showConfirm ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                )}
              </div>
            </div>

            {/* Submit Button */}
            <button
              type="submit"
              className="reset-submit-btn"
              disabled={loading || !isMatching}
            >
              {loading ? "Updating password..." : "Reset Password"}
              {!loading && <ArrowRight size={16} />}
            </button>

            {/* Footer Back */}
            <div className="reset-footer">
              <Link to="/signin" className="reset-back-link">
                <ArrowLeft size={16} /> Back to Sign In
              </Link>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

export default ResetPassword;
