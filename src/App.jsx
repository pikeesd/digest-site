import { useEffect, useMemo, useState } from "react";
import NewsCard from "./components/NewsCard.jsx";
import Fuse from 'fuse.js';

const categories = ["Markets", "DeFi", "AI", "Security", "Regulation"];

// Хук для эффекта печатания (Typewriter)
export const useTypewriter = (text, speed = 25) => {
  const [displayedText, setDisplayedText] = useState("");

  useEffect(() => {
    if (!text) return;

    setDisplayedText(""); // Сбрасываем при новом тексте
    let i = 0;

    const timer = setInterval(() => {
      // Используем колбэк, чтобы всегда брать актуальное значение
      setDisplayedText(text.slice(0, i + 1));
      i++;

      if (i >= text.length) {
        clearInterval(timer);
      }
    }, speed);

    return () => clearInterval(timer);
  }, [text, speed]);

  return displayedText;
};

function App() {
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [news, setNews] = useState([]);
  const [mode, setMode] = useState("idle");
  const [activeCategory, setActiveCategory] = useState("");
  const [openDropdownId, setOpenDropdownId] = useState(null);
  const [timeFilter, setTimeFilter] = useState(24);
  const [serverMessage, setServerMessage] = useState("");
  const [searchQuery, setSearchQuery] = useState("");
  const [briefing, setBriefing] = useState("");

  const [isNichesOpen, setIsNichesOpen] = useState(false);
  const [timeAgo, setTimeAgo] = useState("just now");

  // Подключаем анимацию для брифинга
  const animatedBriefing = useTypewriter(briefing, 20);

  useEffect(() => {
    fetch("https://steadfast-beauty-production-9beb.up.railway.app/api/news")
      .then((res) => res.json())
      .then((data) => {
        if (data.error) {
          setServerMessage("AI is analyzing fresh news...");
          return;
        }
        if (data.metadata?.last_updated) {
          setLastUpdate(new Date(data.metadata.last_updated));
        }

        setBriefing(data.metadata?.briefing || "");
        setNews(data.news || []);
        setServerMessage("");
      })
      .catch(() => setServerMessage("Connecting to server..."));
  }, []);

  useEffect(() => {
    const calculateTime = () => {
      const diffMs = new Date() - lastUpdate;
      const diffMins = Math.floor(diffMs / 60000);
      const diffHours = Math.floor(diffMins / 60);
      if (diffMins < 1) return "just now";
      if (diffMins < 60) return `${diffMins} min ago`;
      if (diffHours < 24) return `${diffHours} hours ago`;
      return lastUpdate.toLocaleDateString();
    };
    setTimeAgo(calculateTime());
    const interval = setInterval(() => setTimeAgo(calculateTime()), 60000);
    return () => clearInterval(interval);
  }, [lastUpdate]);

  const timeFilteredNews = useMemo(() => {
    if (timeFilter === 24) return news;
    const cutoff = new Date().getTime() - timeFilter * 60 * 60 * 1000;
    return news.filter(item => new Date(item.published).getTime() >= cutoff);
  }, [news, timeFilter]);

  const sortedNews = useMemo(() => {
    const filtered = mode === "niches"
      ? timeFilteredNews.filter(item =>
        item.category?.toLowerCase() === activeCategory?.toLowerCase()
      )
      : timeFilteredNews;
    return [...filtered].sort((a, b) => (b.count ?? 0) - (a.count ?? 0));
  }, [timeFilteredNews, mode, activeCategory]);

  const fuse = useMemo(() => new Fuse(sortedNews, {
    keys: ["title", "summary.main"],
    threshold: 0.3,
  }), [sortedNews]);

  const finalNews = useMemo(() => {
    if (!searchQuery) return sortedNews;
    return fuse.search(searchQuery).map(result => result.item);
  }, [searchQuery, sortedNews, fuse]);

  const topCount = timeFilter === 24 ? 3 : 1;
  const topGlobal = finalNews.slice(0, topCount);
  const restGlobal = finalNews.slice(topCount);

  return (
    <div className={`app-layout ${isNichesOpen ? "dropdown-open" : ""}`}>
      {/* Оверлей затемнения при открытии выбора ниш */}
      {isNichesOpen && (
        <div className="page-overlay" onClick={() => setIsNichesOpen(false)}></div>
      )}

      <aside className="sidebar">
        <div className="brand">
          <img src="/mountain.png" alt="logo" className="logo" />
          <div className="brand-info">
            <h1 className="brand-title">Peak Digest</h1>
            <div className="live-indicator">
              <span className="live-dot"></span>
              Live • {timeAgo}
            </div>
          </div>
        </div>

        <div className="side-nav">
          <button
            className={`button primary btn-large ${mode === "full" ? "active" : ""}`}
            onClick={() => {
              setMode("full");
              setIsNichesOpen(false);
            }}
          >
            Show full digest
          </button>

          <div className="dropdown-area">
            <button
              className="button btn-large btn-secondary"
              onClick={() => {
                setIsNichesOpen(!isNichesOpen);
                setOpenDropdownId(null);
              }}
            >
              Generate by niches
              <svg className={`icon ${isNichesOpen ? "open" : ""}`} width="16" height="16" viewBox="0 0 24 24">
                <path d="M6 9l6 6 6-6" stroke="currentColor" strokeWidth="2" fill="none" />
              </svg>
            </button>

            {isNichesOpen && (
              <div className="niches-menu">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    className={`menu-item ${activeCategory?.toLowerCase() === cat?.toLowerCase() ? "selected" : ""}`}
                    onClick={() => {
                      setActiveCategory(cat);
                      setMode("niches");
                      setIsNichesOpen(false);
                    }}
                  >
                    {cat}
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="sidebar-briefing">
            <h3>AI Briefing</h3>
            <p>
              {animatedBriefing || "Distilling market chaos..."}
              <span className="typewriter-cursor">|</span>
            </p>
            <div className="briefing-status">
              <span className="dot pulse"></span> Live Insight
            </div>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {mode !== "idle" && (
          <div className="top-action-bar">
            <button className="back-button" onClick={() => { setMode("idle"); setTimeFilter(24); }}>
              ← Back
            </button>

            <div className="search-wrapper">
              <span className="search-icon">🔍</span>
              <input
                type="text"
                placeholder="Search news..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="global-search-input"
              />
              {searchQuery && <button className="clear-search-btn" onClick={() => setSearchQuery("")}>✕</button>}
            </div>

            <div className="tabs">
              {[2, 10, 24].map((h) => (
                <button key={h} className={`tab ${timeFilter === h ? "active" : ""}`} onClick={() => setTimeFilter(h)}>
                  {h}h
                </button>
              ))}
            </div>
          </div>
        )}

        <div className="content-scroll">
          {serverMessage ? (
            <div className="status-msg"><h2>{serverMessage}</h2></div>
          ) : mode === "idle" ? (
            <div className="empty-state">
              <h2>Ready to peak?</h2>
              <span>Choose your digest type on the left to start.</span>
            </div>
          ) : finalNews.length === 0 ? (
            <div className="empty-category">
              <p>No news in this timeframe yet</p>
            </div>
          ) : (
            <div className="cards-container">
              <div className="top-block">
                <h2 className="card-title" style={{ marginBottom: "20px", fontSize: "24px" }}>
                  {mode === "full" ? "Top news today" : `${activeCategory} Top`}
                </h2>
                <div className="top-cards">
                  {topGlobal.map((item, i) => (
                    <NewsCard
                      key={`top-${i}`}
                      item={item}
                      isOpen={openDropdownId === `top-${i}`}
                      onToggle={() => setOpenDropdownId(openDropdownId === `top-${i}` ? null : `top-${i}`)}
                    />
                  ))}
                </div>
              </div>

              {restGlobal.length > 0 && (
                <div className="cards" style={{ marginTop: "40px" }}>
                  {restGlobal.map((item, i) => (
                    <NewsCard
                      key={`rest-${i}`}
                      item={item}
                      isOpen={openDropdownId === `rest-${i}`}
                      onToggle={() => setOpenDropdownId(openDropdownId === `rest-${i}` ? null : `rest-${i}`)}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;