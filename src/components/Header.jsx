import Tabs from "./Tabs.jsx";

function Header({ lastUpdate, categories, selectedCategories, onToggleCategory }) {
  const getTimeAgo = () => {
    const diff = Math.floor((new Date() - new Date(lastUpdate)) / 60000);

    if (diff < 1) return "just now";
    if (diff === 1) return "1 min ago";
    return `${diff} min ago`;
  };
  return (
    <header className="header">

      <p style={{ fontSize: "12px", color: "gray" }}>
        <div className="live-indicator">
          <span className="live-dot"></span>
          Live • {getTimeAgo()}
        </div>
      </p>

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
