import { useState } from "react";

function NewsCard({ item }) {
  const [open, setOpen] = useState(false);

  return (
    <article className="card">
      <div className="card-header">
        <div>
          <h3 className="card-title">{item.title}</h3>
          <div className="card-meta">{item.count} sources</div>
        </div>

        <a href={item.link || "#"} target="_blank" rel="noreferrer">
          Open source
        </a>
      </div>

      <div className="card-actions">
        <button onClick={() => setOpen(!open)}>
          {open ? "Hide details" : "Show details"}
        </button>
      </div>

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
