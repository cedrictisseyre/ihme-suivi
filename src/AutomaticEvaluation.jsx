import React from "react";

export default function AutomaticEvaluation({ p, compact = false, onOpen }) {
  const evaluation = p.progression?.evaluation;
  const available = evaluation?.available;
  return (
    <section
      className={`automatic-evaluation${compact ? " automatic-compact" : ""}`}
      aria-label={`Évaluation automatique de ${p.student_name || "ce projet"}`}
    >
      <p className="eyebrow">ÉVALUATION AUTOMATIQUE</p>
      <strong className="automatic-count">
        {available
          ? `${evaluation.observed}/${evaluation.total} jalons avec indices`
          : "Évaluation en attente"}
      </strong>
      {p.progression?.stale && (
        <span className="automatic-warning">À actualiser</span>
      )}
      {!compact && (
        <>
          <p>
            {evaluation?.verdict ||
              "Publier le travail dans le dépôt, puis lancer l’évaluation."}
          </p>
          <p className="muted">
            Diagnostic du dépôt : les indices repérés sont à confirmer par une
            démonstration. Les validations et la note sur 20 restent
            enseignantes.
          </p>
          {available && (
            <>
              <h3>Points repérés automatiquement</h3>
              <p>
                {evaluation.strengths.length
                  ? evaluation.strengths.join(" · ")
                  : "Aucun indice concluant dans l’échantillon lu ; à vérifier."}
              </p>
              <h3>Priorités proposées</h3>
              <ol>
                {evaluation.priorities.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ol>
              <div className="automatic-grid">
                {evaluation.milestones.map((m) => (
                  <div key={m.position}>
                    <span>
                      {m.position}. {m.title}
                    </span>
                    <b>{m.label}</b>
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
      {compact && (
        <button type="button" className="automatic-open" onClick={onOpen}>
          Voir l’évaluation automatique →
        </button>
      )}
    </section>
  );
}
