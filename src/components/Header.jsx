import Tabs from "./Tabs.jsx";

function Header({ categories, selectedCategories, onToggleCategory }) {
  return (
    <header className="header">
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
