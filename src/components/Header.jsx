import Tabs from "./Tabs.jsx";

function Header({ categories, selectedCategories, onToggleCategory }) {
  return (
    <header className="header">
      <div className="brand">
        <div className="brand-badge" />
        <h1>CryptoDigest</h1>
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
