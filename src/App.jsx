import { useEffect, useState } from "react";
import Header from "./components/Header.jsx";
import NewsCard from "./components/NewsCard.jsx";

function App() {
  const [news, setNews] = useState([]);

  useEffect(() => {
    fetch("http://localhost:8000/api/news")
      .then(res => res.json())
      .then(data => {
        console.log(data);
        setNews(data);
      })
      .catch(err => console.error(err));
  }, []);

  return (
    <div className="app">
      <Header />
      <main className="cards">
        {news.map((item, index) => (
          <NewsCard key={index} item={item} />
        ))}
      </main>
    </div>
  );
}

export default App;
