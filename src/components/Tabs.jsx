import { useState } from "react";

const defaultTabs = ["Markets", "DeFi", "AI", "Regulation", "Security"];

function Tabs({ tabs = defaultTabs }) {
  const [active, setActive] = useState(tabs[0]);

  return (
    <div className="tabs">
      {tabs.map((tab) => (
        <button
          key={tab}
          type="button"
          className={`tab${active === tab ? " active" : ""}`}
          onClick={() => setActive(tab)}
        >
          {tab}
        </button>
      ))}
    </div>
  );
}

export default Tabs;
