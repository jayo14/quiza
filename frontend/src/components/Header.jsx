import { Bell, Menu } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import "./Header.css";

function Header({ onToggleMenu }) {
  const { user } = useAuth();
  return (
    <header className="header">
      <div className="header__left">
        <button
          className="header__menu-btn"
          onClick={onToggleMenu}
          aria-label="Toggle navigation menu"
        >
          <Menu size={22} />
        </button>

        <div className="header__greeting">
          <h1>Good morning {user?.name || "there"},</h1>
          <p>Ready to continue learning?</p>
        </div>
      </div>

      <div className="header__actions">
        <button className="header__notification" aria-label="Notifications">
          <Bell size={20} />
        </button>

        <div className="header__profile">
          <div className="header__avatar">
            {user?.profile_image ? (
              <img src={user.profile_image} alt={user.name} />
            ) : (
              user?.name?.charAt(0) || "U"
            )}
          </div>

          <div className="header__user">
            <span>{user?.name || "User"}</span>
            <small>Student</small>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;
