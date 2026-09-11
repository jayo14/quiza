import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { User, Mail, Lock, Eye, EyeOff, ArrowRight } from "lucide-react";
import { toast } from "sonner";
import { useAuth } from "../context/AuthContext";
import "./SignUp.css";

function SignUp() {
  const { signUp, signInWithGoogle } = useAuth();
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const getPasswordStrength = (pass) => {
    if (!pass) return { level: "", score: 0, text: "" };
    let score = 0;
    if (pass.length >= 8) score += 1;
    if (/[0-9]/.test(pass)) score += 1;
    if (/[A-Z]/.test(pass)) score += 1;
    if (/[^A-Za-z0-9]/.test(pass)) score += 1;

    if (score <= 1) return { level: "weak", score: 1, text: "Weak password" };
    if (score <= 3)
      return { level: "medium", score: 2, text: "Medium strength" };
    return { level: "strong", score: 3, text: "Strong password" };
  };

  const strength = getPasswordStrength(password);

  const handleSubmit = async (e) => {
    e.preventDefault();

    setLoading(true);

    try {
      await signUp(name, email, password);
      navigate("/");
    } catch (error) {
      console.error("Signup error:", error);
      toast.error(error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="signup-container">
      <div className="signup-glow" aria-hidden="true" />

      <div className="signup-card">
        {/* Brand Header */}
        <Link to="/" className="signup-brand">
          <span className="signup-brand__icon">Q</span>
          <span className="signup-brand__text">Quiza</span>
        </Link>

        <div className="signup-header">
          <h1>Create your account</h1>
          <p>Start turning your study notes into smart AI quizzes.</p>
        </div>

        <form className="signup-form" onSubmit={handleSubmit}>
          {/* Full Name */}
          <div className="signup-field">
            <label htmlFor="signup-name">Full Name</label>
            <div className="signup-input-wrap">
              <User size={18} className="signup-input-icon" />
              <input
                id="signup-name"
                type="text"
                required
                placeholder="Elvis Presley"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="signup-input"
              />
            </div>
          </div>

          <div className="signup-field">
            <label htmlFor="signup-email">Email Address</label>
            <div className="signup-input-wrap">
              <Mail size={18} className="signup-input-icon" />
              <input
                id="signup-email"
                type="email"
                required
                placeholder="name@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="signup-input"
              />
            </div>
          </div>

          {/* Password */}
          <div className="signup-field">
            <label htmlFor="signup-password">Password</label>
            <div className="signup-input-wrap">
              <Lock size={18} className="signup-input-icon" />
              <input
                id="signup-password"
                type={showPassword ? "text" : "password"}
                required
                placeholder="At least 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="signup-input"
              />
              <button
                type="button"
                className="signup-toggle-btn"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? "Hide password" : "Show password"}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>

            {/* Password Strength Indicator */}
            {password && (
              <div className="signup-strength">
                <div className="signup-strength__bar-wrap">
                  <div
                    className={`signup-strength__bar signup-strength__bar--${strength.level}`}
                  />
                </div>
                <span
                  className={`signup-strength__text signup-strength__text--${strength.level}`}
                >
                  {strength.text}
                </span>
              </div>
            )}
          </div>

          {/* Submit Button */}
          <button
            type="submit"
            className="signup-submit-btn"
            disabled={loading}
          >
            {loading ? "Creating account..." : "Create Account"}
            {!loading && <ArrowRight size={16} />}
          </button>

          {/* Divider */}
          <div className="signup-divider">
            <span>OR</span>
          </div>

          {/* Google Sign Up */}
          <button
            type="button"
            className="signup-google-btn"
            onClick={signInWithGoogle}
          >
            <svg className="signup-google-icon" viewBox="0 0 24 24">
              <path
                fill="#4285F4"
                d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"
              />
              <path
                fill="#34A853"
                d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.33 24 12 24z"
              />
              <path
                fill="#FBBC05"
                d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"
              />
              <path
                fill="#EA4335"
                d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.33 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"
              />
            </svg>
            <span>Sign up with Google</span>
          </button>
        </form>

        {/* Footer */}
        <div className="signup-footer">
          Already have an account?{" "}
          <Link to="/signin" className="signup-link">
            Sign In
          </Link>
        </div>
      </div>
    </div>
  );
}

export default SignUp;
