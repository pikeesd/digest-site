import { useState } from "react";

function NewsCard({ item, isOpen, onToggle }) {


  // убираем дубли ссылок
  const uniqueLinks = Object.values(
    (item.links || []).reduce((acc, curr) => {
      if (!acc[curr.source]) {
        acc[curr.source] = curr;
      }
      return acc;
    }, {})
  );

  return (
    <article className={`card ${isOpen ? "active-dropdown" : ""}`}>
      <div className="card-header">
        <div>
          <h3 className="card-title">{item.title}</h3>
          <div className="card-meta">{item.count} sources</div>
        </div>

        {/* ✅ ОДИН dropdown */}
        <div className="source-dropdown">
          <button
            className="source-button"
            onClick={onToggle}
          >
            Open source ▾
          </button>

          {isOpen && (
            <div className="source-menu">
              {uniqueLinks.map((src, index) => (
                <a
                  key={index}
                  href={src.link}
                  target="_blank"
                  rel="noreferrer"
                  className="source-item"
                >
                  {src.source}
                </a>
              ))}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

export default NewsCard;