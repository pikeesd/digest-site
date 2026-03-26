import { useEffect, useMemo, useState } from "react";
import Header from "./components/Header.jsx";
import NewsCard from "./components/NewsCard.jsx";

const categories = ["Markets", "DeFi", "AI", "Regulation", "Security"];

function App() {
  const [news, setNews] = useState([]);
  const [mode, setMode] = useState("idle");
  const [selectedCategories, setSelectedCategories] = useState([]);
  const [activeCategory, setActiveCategory] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/api/news")
      .then((res) => res.json())
      .then((data) => {
        console.log(data);
        setNews(data);
      })
      .catch((err) => console.error(err));
  }, []);

  const toggleCategory = (category) => {
    setSelectedCategories((prev) =>
      prev.includes(category)
        ? prev.filter((item) => item !== category)
        : [...prev, category]
    );
  };

  useEffect(() => {
    if (mode !== "niches") {
      return;
    }
    if (!selectedCategories.length) {
      setActiveCategory("");
      return;
    }
    if (!selectedCategories.includes(activeCategory)) {
      setActiveCategory(selectedCategories[0]);
    }
  }, [mode, selectedCategories, activeCategory]);

  const filteredNews = useMemo(() => {
    if (mode !== "niches") {
      return news;
    }
    return news.filter((item) => selectedCategories.includes(item.category));
  }, [mode, news, selectedCategories]);

  const sortedNews = useMemo(() => {
    return [...filteredNews].sort(
      (a, b) => (b.count ?? 0) - (a.count ?? 0)
    );
  }, [filteredNews]);

  const topThreeGlobal = useMemo(() => sortedNews.slice(0, 3), [sortedNews]);
  const restGlobal = useMemo(() => sortedNews.slice(3), [sortedNews]);

  const activeCategoryItems = useMemo(() => {
    if (!activeCategory) {
      return [];
    }
    return sortedNews.filter((item) => item.category === activeCategory);
  }, [activeCategory, sortedNews]);

  const topThreeCategory = useMemo(
    () => activeCategoryItems.slice(0, 3),
    [activeCategoryItems]
  );
  const restCategory = useMemo(
    () => activeCategoryItems.slice(3),
    [activeCategoryItems]
  );

  return (
    <div className="app">
      <Header
        categories={categories}
        selectedCategories={selectedCategories}
        onToggleCategory={toggleCategory}
      />
      <main className="main">
        {mode === "idle" ? (
          <div className="idle-actions">
            <button
              type="button"
              className="button"
              onClick={() => setMode("full")}
            >
              Generate full digest
            </button>
            <button
              type="button"
              className="button"
              onClick={() => setMode("niches")}
              disabled={selectedCategories.length === 0}
            >
              Generate digest by niches
            </button>
          </div>
        ) : mode === "full" ? (
          <>
            <div className="cards">
              {topThreeGlobal.map((item, index) => (
                <NewsCard key={`top-${index}`} item={item} />
              ))}
            </div>
            <div className="cards">
              {restGlobal.map((item, index) => (
                <NewsCard key={`all-${index}`} item={item} />
              ))}
            </div>
          </>
        ) : (
          <>
            <div className="tabs">
              {selectedCategories.map((category) => (
                <button
                  key={category}
                  type="button"
                  className={`tab${activeCategory === category ? " active" : ""}`}
                  onClick={() => setActiveCategory(category)}
                >
                  {category}
                </button>
              ))}
            </div>
            {activeCategory ? (
              <section>
                <h2>{activeCategory}</h2>
                <div className="cards">
                  {topThreeCategory.map((item, index) => (
                    <NewsCard
                      key={`top-${activeCategory}-${index}`}
                      item={item}
                    />
                  ))}
                </div>
                <div className="cards">
                  {restCategory.map((item, index) => (
                    <NewsCard
                      key={`all-${activeCategory}-${index}`}
                      item={item}
                    />
                  ))}
                </div>
              </section>
            ) : null}
          </>
        )}
      </main>
    </div>
  );
}

export default App;
