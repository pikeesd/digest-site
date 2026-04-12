import { useEffect, useMemo, useState } from "react";
import NewsCard from "./components/NewsCard.jsx";
import Fuse from 'fuse.js';

const categories = ["Markets", "DeFi", "AI", "Regulation", "Security"];

function App() {
  // --- 1. ВСЕ СОСТОЯНИЯ (STATE) ---
  const [lastUpdate, setLastUpdate] = useState(new Date());
  const [news, setNews] = useState([]);
  const [mode, setMode] = useState("idle"); // idle, full, niches
  const [activeCategory, setActiveCategory] = useState("");
  const [openDropdownId, setOpenDropdownId] = useState(null);
  const [timeFilter, setTimeFilter] = useState(24);
  const [serverMessage, setServerMessage] = useState("");
  const [searchQuery, setSearchQuery] = useState("");

  const [isNichesOpen, setIsNichesOpen] = useState(false);
  const [timeAgo, setTimeAgo] = useState("just now");
  const [isOpen, setIsOpen] = useState(false);

  // --- 2. ЭФФЕКТЫ (ЗАГРУЗКА И ТАЙМЕРЫ) ---
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

  // --- 3. ВЫЧИСЛЕНИЯ (ЦЕПОЧКА ФИЛЬТРАЦИИ) ---

  // А. Фильтр по времени
  const timeFilteredNews = useMemo(() => {
    if (timeFilter === 24) return news;
    const cutoff = new Date().getTime() - timeFilter * 60 * 60 * 1000;
    return news.filter(item => new Date(item.published).getTime() >= cutoff);
  }, [news, timeFilter]);

  // Б. Фильтр по категориям и базовая сортировка
  const sortedNews = useMemo(() => {
    const filtered = mode === "niches"
      ? timeFilteredNews.filter(item => item.category === activeCategory)
      : timeFilteredNews;
    return [...filtered].sort((a, b) => (b.count ?? 0) - (a.count ?? 0));
  }, [timeFilteredNews, mode, activeCategory]);

  // В. Инициализация поискового движка на базе отфильтрованных новостей
  const fuse = useMemo(() => new Fuse(sortedNews, {
    keys: ["title", "summary.main"],
    threshold: 0.3,
    distance: 100,
  }), [sortedNews]);

  // Г. Финальный результат с учетом поиска
  const finalNews = useMemo(() => {
    if (!searchQuery) return sortedNews;
    return fuse.search(searchQuery).map(result => result.item);
  }, [searchQuery, sortedNews, fuse]);

  // Д. Разделение на ТОП и остальные (используем finalNews для живого поиска)
  const topCount = timeFilter === 24 ? 3 : 1;
  const topGlobal = finalNews.slice(0, topCount);
  const restGlobal = finalNews.slice(topCount);

  return (
    <div className={`app-layout ${isNichesOpen ? "dropdown-open" : ""}`}>

      {/* Оверлей затемнения при открытии выбора ниш */}
      {isNichesOpen && <div className="page-overlay" onClick={() => setIsNichesOpen(false)}></div>}

      {/* ЛЕВАЯ ПАНЕЛЬ (САЙДБАР) */}
      <aside className="sidebar">
        <div className="brand">
          <img src="/mountain.png" alt="logo" className="logo" />
          <div className="brand-info">
            <h1 className="brand-title">Peak Digest</h1>
            <div className="live-indicator">
              <span className="live-dot"></span>
              {/* ✅ Теперь здесь живое время */}
              Live • {timeAgo}
            </div>
          </div>
        </div>


        <div className="side-nav">
          <button
            className={`button primary btn-large ${mode === "full" ? "active" : ""}`}
            onClick={() => { setMode("full"); setIsNichesOpen(false); }}
          >
            Show full digest
          </button>

          <div className="dropdown-area">
            <button
              className="button btn-large btn-secondary"
              onClick={() => {
                // 1. Переключаем видимость меню ниш
                setIsNichesOpen(!isNichesOpen);
                // 2. 🔥 ГЛАВНОЕ: Сбрасываем ID открытой карточки, чтобы закрыть "Open source"
                setOpenDropdownId(null);
              }}
            >
              Generate by niches <svg
                className={`icon ${isOpen ? "open" : ""}`}
                width="16"
                height="16"
                viewBox="0 0 24 24"
              >
                <path
                  d="M6 9l6 6 6-6"
                  stroke="currentColor"
                  strokeWidth="2"
                  fill="none"
                />
              </svg>
            </button>

            {isNichesOpen && (
              <div className="niches-menu">
                {categories.map((cat) => (
                  <button
                    key={cat}
                    className={`menu-item ${activeCategory === cat ? "selected" : ""}`}
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
        </div>
      </aside>


      {/* ПРАВАЯ ЧАСТЬ (КОНТЕНТ) */}
      <main className="main-content">

        {mode !== "idle" && (
          <div className="top-action-bar">
            {/* Левая часть: кнопка Back */}
            <button className="back-button" onClick={() => { setMode("idle"); setTimeFilter(24); }}>
              ← Back
            </button>

            {/* ЦЕНТРАЛЬНАЯ ЧАСТЬ: ПОИСК */}
            <div className="search-wrapper">
              <span className="search-icon">🔍</span>
              <input
                type="text"
                placeholder="Search news..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="global-search-input"
              />
              {searchQuery && (
                <button className="clear-search-btn" onClick={() => setSearchQuery("")}>✕</button>
              )}
            </div>

            {/* Правая часть: фильтры времени */}
            <div className="tabs">
              {[2, 10, 24].map((h) => (
                <button
                  key={h}
                  className={`tab ${timeFilter === h ? "active" : ""}`}
                  onClick={() => setTimeFilter(h)}
                >
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
          ) : sortedNews.length === 0 ? (
            <div className="empty-category">
              <p>No news in this timeframe yet</p>
              <span>Try selecting a longer period (e.g., 24h) or check back later.</span>
            </div>
          ) : (
            <div className="cards-container">
              <div className="top-block">
                <h2 className="card-title" style={{ marginBottom: '20px', fontSize: '24px' }}>
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
                <div className="cards" style={{ marginTop: '40px' }}>
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