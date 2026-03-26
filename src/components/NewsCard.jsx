import { useState } from "react";

function NewsCard({ item }) {
  const [open, setOpen] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const links = item.links ?? [];
  const safeLinks = links.filter((linkItem) => linkItem?.link);

  return (
    <article className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">{item.title}</h3>
          <div className="card-meta">{item.count} sources</div>
        </div>
      </div>

      <div className="card-actions">
        <button onClick={() => setOpen(!open)}>
          {open ? "Hide details" : "Show details"}
        </button>
        {safeLinks.length === 1 ? (
          <a href={safeLinks[0].link} target="_blank" rel="noreferrer">
            {safeLinks[0].source || "Source"}
          </a>
        ) : null}
        {safeLinks.length > 1 ? (
          <button onClick={() => setShowSources(!showSources)}>
            Sources {showSources ? "▲" : "▼"}
          </button>
        ) : null}
      </div>

      {safeLinks.length > 1 && showSources ? (
        <div className="sources-list">
          {safeLinks.map((linkItem, index) => (
            <div key={`${linkItem.source}-${index}`}>
              <a href={linkItem.link} target="_blank" rel="noreferrer">
                {linkItem.source || "Source"}
              </a>
            </div>
          ))}
        </div>
      ) : null}

      {open && (
        <div className="details">
          <p><strong>Summary:</strong> {item.summary?.main || "No summary"}</p>
          <p><strong>Impact:</strong> {item.summary?.impact || "-"}</p>
          <p><strong>Consequences:</strong> {item.summary?.consequences || "-"}</p>
        </div>
      )}
    </article>
  );
}

export default NewsCard;
