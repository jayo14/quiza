import "./StatCard.css";

function StatCard({ title, value, description }) {
  return (
    <div className="stat-card">
      <p className="stat-card__title">{title}</p>
      <h3 className="stat-card__value">{value}</h3>
      <span className="stat-card__description">{description}</span>
    </div>
  );
}

export default StatCard;
