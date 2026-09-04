import { NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard,
  Upload,
  BookOpen,
  BarChart3,
  Settings,
  LogOut,
  X,
} from "lucide-react";
import { useAuth } from "../context/AuthContext";

import "./Sidebar.css";

function Sidebar({ isOpen, onClose }) {
  const navigate = useNavigate();
  const { user, signOut } = useAuth();

  const handleSignOut = () => {
    signOut();
    onClose();
    navigate("/signin");
  };

  return (
    <>
      <div
        className={`sidebar__backdrop ${
          isOpen ? "sidebar__backdrop--visible" : ""
        }`}
        onClick={onClose}
        aria-hidden="true"
      />

      <aside className={`sidebar ${isOpen ? "sidebar--open" : ""}`}>
        <div className="sidebar__logo">
          <div className="sidebar__brand">
            <span>Q</span>
            <h1>Quiza</h1>
          </div>

          <button
            className="sidebar__close-btn"
            onClick={onClose}
            aria-label="Close menu"
          >
            <X size={20} />
          </button>
        </div>

        <nav className="sidebar__nav">
          <NavLink
            to="/"
            onClick={onClose}
            className={({ isActive }) =>
              isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
            }
            end
          >
            <LayoutDashboard className="sidebar__icon" size={18} />
            <span>Dashboard</span>
          </NavLink>

          <NavLink
            to="/upload"
            onClick={onClose}
            className={({ isActive }) =>
              isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
            }
          >
            <Upload className="sidebar__icon" size={18} />
            <span>Upload Material</span>
          </NavLink>

          <NavLink
            to="/quizzes"
            onClick={onClose}
            className={({ isActive }) =>
              isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
            }
          >
            <BookOpen className="sidebar__icon" size={18} />
            <span>My Quizzes</span>
          </NavLink>

          <NavLink
            to="/progress"
            onClick={onClose}
            className={({ isActive }) =>
              isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
            }
          >
            <BarChart3 className="sidebar__icon" size={18} />
            <span>Progress</span>
          </NavLink>

          <NavLink
            to="/settings"
            onClick={onClose}
            className={({ isActive }) =>
              isActive ? "sidebar__link sidebar__link--active" : "sidebar__link"
            }
          >
            <Settings className="sidebar__icon" size={18} />
            <span>Settings</span>
          </NavLink>
        </nav>

        <div className="sidebar__bottom">
          <div className="sidebar__profile">
            <div className="sidebar__avatar">
              {" "}
              {user?.name?.charAt(0).toUpperCase() || "U"}
            </div>
            <div>
              <p>{user?.name || "User"}</p>
              <span>Student</span>
            </div>
          </div>

          <button
            type="button"
            className="sidebar__logout"
            onClick={handleSignOut}
          >
            <LogOut size={18} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;
