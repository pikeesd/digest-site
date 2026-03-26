const defaultTabs = ["Markets", "DeFi", "AI", "Regulation", "Security"];

function Tabs({ tabs = defaultTabs, selected = [], onToggle }) {
  return (
    <div className="tabs">
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          className={`tab${selected.includes(tab) ? " active" : ""}`}
          onClick={() => onToggle(tab)}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}

export default Tabs;
