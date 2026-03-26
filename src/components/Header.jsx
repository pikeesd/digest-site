import Tabs from "./Tabs.jsx";

function Header() {
  return (
    <header className="header">
      <div className="brand">
        <div className="brand-badge" />
        <h1>CryptoDigest</h1>
      </div>
      <Tabs />
    </header>
  );
}

export default Header;
