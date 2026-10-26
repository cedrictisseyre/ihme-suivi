export default function CommitChart({ activity, stale = false }) {
  const days = activity?.days;
  if (!Array.isArray(days) || !days.length)
    return (
      <span className="chart-empty">
        Commits par jour · données à actualiser
      </span>
    );
  const peak = Math.max(0, ...days.map((d) => d.count));
  const total = days.reduce((sum, d) => sum + d.count, 0);
  const dateLabel = (date) => date.slice(8, 10) + "/" + date.slice(5, 7);
  return (
    <span className="commit-chart">
      <span className="chart-caption">
        <span>
          {activity.complete ? "" : "≥ "}
          {total} commit{total !== 1 ? "s" : ""} · 14 jours
        </span>
        <span>max. {peak}/j</span>
      </span>
      <svg
        viewBox="0 0 280 45"
        preserveAspectRatio="none"
        role="img"
        aria-label={`Commits par jour, heure de Paris : ${days.map((d) => `${dateLabel(d.date)} : ${d.count}`).join(", ")}${!activity.complete ? " ; lecture partielle" : ""}`}
      >
        {days.map((d, i) => (
          <rect
            key={d.date}
            x={i * 20 + 2}
            y={44 - (d.count ? Math.max(3, (d.count / (peak || 1)) * 40) : 1)}
            width="15"
            height={d.count ? Math.max(3, (d.count / (peak || 1)) * 40) : 1}
            rx="2"
            className={d.count ? "chart-bar" : "chart-zero"}
          >
            <title>
              {dateLabel(d.date)} : {d.count} commit{d.count !== 1 ? "s" : ""}
            </title>
          </rect>
        ))}
      </svg>
      <span className="chart-axis">
        <span>{dateLabel(days[0].date)}</span>
        <span>
          {stale
            ? "Dernière lecture disponible"
            : !activity.complete
              ? "Lecture partielle · Paris"
              : "Paris"}{" "}
          · {dateLabel(days.at(-1).date)}
        </span>
      </span>
    </span>
  );
}
