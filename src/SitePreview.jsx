import React, { useState } from "react";

export default function SitePreview({ p }) {
  const [failed, setFailed] = useState(null);
  const url = p.site?.url || p.deployed_url;
  const thumbnail = p.site?.thumbnail;
  const image = thumbnail && failed !== thumbnail;
  return (
    <div className="site-preview">
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="site-preview-link"
        >
          {image ? (
            <img
              src={thumbnail}
              alt={`Aperçu du site de ${p.student_name}`}
              loading="lazy"
              width="640"
              height="400"
              onError={() => setFailed(thumbnail)}
            />
          ) : (
            <span className="site-preview-placeholder">Miniature à venir</span>
          )}
          <span className="site-preview-caption">Voir le site ↗</span>
        </a>
      ) : (
        <div className="site-preview-placeholder">Site à renseigner</div>
      )}
      {url && <small className="site-address">{url}</small>}
      {image && <small>Dernier aperçu enregistré</small>}
      {p.site?.progress_url && (
        <a
          className="public-progress-link"
          href={p.site.progress_url}
          target="_blank"
          rel="noreferrer"
        >
          Évaluation automatique publique ↗
        </a>
      )}
    </div>
  );
}
