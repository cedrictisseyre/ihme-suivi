import React from "react";
import AutomaticEvaluation from "./AutomaticEvaluation.jsx";

export default function ProgressPanel({ p, busy, analyze }) {
  const report = p.progression;
  return (
    <section className="panel progression-panel">
      <div className="titlebar">
        <div>
          <p className="eyebrow">M2 IHME STAPS · MODULE DE 10 H</p>
          <h2>Évaluation automatique du projet</h2>
        </div>
        <button disabled={busy || !p.repository_url} onClick={analyze}>
          {busy ? "Analyse en cours…" : "Actualiser l’évaluation"}
        </button>
      </div>
      <AutomaticEvaluation p={p} />
      <p>
        Un petit scénario utile, des données structurées, un calcul expliqué et
        trois essais : normal, vide et limite.
      </p>
      <p className="muted">
        L’analyse lit un échantillon de code sans l’exécuter. Les indices ne
        valident pas les compétences et ne produisent aucune note. Vos
        corrections des jalons sont prioritaires.
      </p>
      {report?.analysis ? (
        <p>
          Dernier bilan :{" "}
          {new Date(report.analysis.generated_at).toLocaleString("fr-FR")} ·
          commit <code>{report.analysis.sha.slice(0, 7)}</code> ·{" "}
          {report.analysis.milestones.filter((m) => m.observed).length}/6 jalons
          avec indices. {report.stale && "Bilan à actualiser."}
        </p>
      ) : (
        <p>Aucune analyse disponible. Les jalons restent modifiables.</p>
      )}
      {report?.error && (
        <p className="error" role="status">
          {report.error}
        </p>
      )}
      {report?.rubric.map((rule) => {
        const m = p.milestones.find((item) => item.position === rule.position);
        return (
          <article className="rubric-item" key={rule.position}>
            <h3>
              {rule.position}. {rule.title}
            </h3>
            <p>
              <b>Attendu :</b> {rule.expected}
            </p>
            <p>
              <b>À montrer :</b> {rule.demonstration}
            </p>
            <p>
              <b>Indice automatique :</b>{" "}
              {m?.automatic?.summary || "Non vérifié."}
            </p>
            {m?.automatic?.files?.length > 0 && (
              <p className="muted">
                Fichiers repérés : {m.automatic.files.join(", ")}
              </p>
            )}
            {m?.status !== "done" && (
              <p>
                <b>Prochaine action :</b> {m?.automatic?.next || rule.next}
              </p>
            )}
            {m?.manual_override && (
              <small>Le statut choisi par l’enseignant est conservé.</small>
            )}
          </article>
        );
      })}
      <h3>Journal automatique</h3>
      <p className="muted">
        Ces relevés ne constituent pas des échanges avec l’enseignant.
      </p>
      {report?.history?.length ? (
        <ul>
          {report.history.map((h) => (
            <li key={h.sha}>
              {new Date(h.generated_at).toLocaleString("fr-FR")} ·{" "}
              {h.sha.slice(0, 7)} · {h.observed}/6 jalons avec indices
            </li>
          ))}
        </ul>
      ) : (
        <p>Les premières analyses apparaîtront ici.</p>
      )}
    </section>
  );
}
