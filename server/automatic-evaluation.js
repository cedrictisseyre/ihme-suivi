import { RUBRIC } from "./rubric.js";

export function automaticEvaluation(analysis) {
  const available = Array.isArray(analysis?.milestones);
  const milestones = RUBRIC.map((rule) => {
    const evidence = analysis?.milestones?.find(
      (m) => m.position === rule.position,
    );
    const observed = available && evidence?.observed === true;
    return {
      position: rule.position,
      title: rule.title,
      observed,
      label: !available
        ? "Non évalué"
        : observed
          ? "Indices repérés"
          : "À vérifier",
      feedback: evidence?.summary || "Aucune analyse disponible pour ce jalon.",
      next: evidence?.next || rule.next,
    };
  });
  const observed = milestones.filter((m) => m.observed).length;
  const gaps = milestones.filter((m) => !m.observed);
  return {
    available,
    observed,
    total: RUBRIC.length,
    verdict: !available
      ? "Évaluation en attente"
      : observed === RUBRIC.length
        ? "Des indices sur les six jalons ; démonstration à confirmer"
        : "Des points restent à vérifier dans le projet",
    strengths: milestones.filter((m) => m.observed).map((m) => m.title),
    priorities: !available
      ? [
          "Publier le travail dans le dépôt, puis lancer l’évaluation automatique.",
        ]
      : gaps.length
        ? gaps.slice(0, 3).map((m) => m.next)
        : [
            "Rejouer le parcours principal et les trois essais : normal, vide et limite.",
            "Expliquer le calcul et la requête SQL à l’enseignant pour valider les jalons.",
          ],
    milestones,
  };
}
