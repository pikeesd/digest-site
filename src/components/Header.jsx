import { useEffect, useState } from "react";
import Tabs from "./Tabs.jsx";

function Header({ lastUpdate, categories, selectedCategories, onToggleCategory }) {
  const [timeAgoText, setTimeAgoText] = useState("just now");

  useEffect(() => {
    // Функция подсчета времени
    const calculateTimeAgo = () => {
      if (!lastUpdate) return "updating...";

      const diffMs = new Date() - new Date(lastUpdate);
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);

      if (diffMins < 1) return "just now";
      if (diffMins < 60) return `${diffMins} min ago`;
      if (diffHours === 1) return `1 hour ago`;
      if (diffHours < 24) return `${diffHours} hours ago`;

      // Если новостям больше суток (на всякий случай)
      const diffDays = Math.floor(diffHours / 24);
      return diffDays === 1 ? `1 day ago` : `${diffDays} days ago`;
    };

    // Считаем сразу при рендере
    setTimeAgoText(calculateTimeAgo());

    // Запускаем таймер, который каждую минуту обновляет надпись
    const intervalId = setInterval(() => {
      setTimeAgoText(calculateTimeAgo());
    }, 60000);

    // Очищаем таймер, если компонент удаляется
    return () => clearInterval(intervalId);
  }, [lastUpdate]); // Перезапускаем хук, если сервер прислал новую дату

  // Бонус: если новостям больше часа, зеленая точка станет желтой (не такие уж и "Live")
  const dotColor = timeAgoText.includes("hour") || timeAgoText.includes("day")
    ? "#f59e0b" // Желтый
    : "#22c55e"; // Зеленый

  return (
    <header className="header">
      {/* Убрал тег <p>, вкладывать div в p — это ошибка HTML */}
      <div style={{ fontSize: "12px", color: "gray", marginBottom: "16px" }}>
        <div className="live-indicator">
          <span
            className="live-dot"
            style={{ backgroundColor: dotColor, boxShadow: `0 0 8px ${dotColor}80` }}
          ></span>
          Live • {timeAgoText}
        </div>
      </div>

      <div className="brand">
        <img src="/mountain.png" alt="logo" className="logo" />
        <h1 className="brand-title">Peak Digest</h1>
      </div>

      <Tabs
        tabs={categories}
        selected={selectedCategories}
        onToggle={onToggleCategory}
      />
    </header>
  );
}

export default Header;