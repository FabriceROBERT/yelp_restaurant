"use client";

import { useState } from "react";

export type BusinessInfo = {
  business_id: string;
  nom: string | null;
  adresse: string | null;
  ville: string | null;
  state_code: string | null;
  code_postal: string | null;
  gamme_prix: string | null;
  note_moyenne: number | null;
  nb_avis: number | null;
  ouvert: boolean | null;
};

type Review = {
  review_id: string;
  note: number;
  texte: string;
  date_avis: string;
  utile: number;
};

function prix(gamme: string | null) {
  return gamme ? "$".repeat(Number(gamme)) : "Prix non renseigné";
}

export default function BusinessModal({
  business,
  imageUrl,
  caption,
  label,
  onClose,
}: {
  business: BusinessInfo;
  imageUrl?: string;
  caption?: string | null;
  label?: string | null;
  onClose: () => void;
}) {
  const [reviews, setReviews] = useState<Review[] | null>(null);
  const [loadingReviews, setLoadingReviews] = useState(false);

  async function toggleReviews() {
    if (reviews) {
      setReviews(null);
      return;
    }
    setLoadingReviews(true);
    try {
      const res = await fetch(`/api/reviews/${business.business_id}`);
      const data = await res.json();
      setReviews(data.reviews);
    } finally {
      setLoadingReviews(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className={`grid max-h-[90vh] w-full max-w-3xl grid-cols-1 overflow-y-auto rounded-2xl bg-white ${
          imageUrl ? "md:grid-cols-2" : ""
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        {imageUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={imageUrl}
            alt={caption || business.nom || ""}
            className="h-64 w-full object-cover md:h-full"
          />
        )}

        <div className="relative p-6">
          <button
            type="button"
            onClick={onClose}
            className="absolute right-4 top-4 rounded-full bg-slate-100 px-2.5 py-1 text-sm text-slate-600 hover:bg-slate-200"
            aria-label="Fermer"
          >
            ✕
          </button>

          <h2 className="pr-8 text-xl font-bold text-slate-900">
            {business.nom ?? "Établissement inconnu"}
          </h2>

          {business.adresse && (
            <p className="mt-1 text-sm text-slate-600">
              {business.adresse}
              {business.ville && `, ${business.ville}`}
              {business.state_code && ` ${business.state_code}`}
              {business.code_postal && ` ${business.code_postal}`}
            </p>
          )}

          <dl className="mt-5 grid grid-cols-2 gap-4">
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Note</dt>
              <dd className="text-lg font-semibold text-slate-900">
                {business.note_moyenne != null ? `${business.note_moyenne.toFixed(2)} / 5` : "—"}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Recommandation</dt>
              <dd className="text-lg font-semibold text-slate-900">
                {business.nb_avis != null ? (
                  <button
                    type="button"
                    onClick={toggleReviews}
                    className="underline decoration-dotted underline-offset-2 hover:text-red-600"
                  >
                    {business.nb_avis} avis
                  </button>
                ) : (
                  "—"
                )}
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Prix</dt>
              <dd className="text-lg font-semibold text-slate-900">{prix(business.gamme_prix)}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Statut</dt>
              <dd className="text-lg font-semibold text-slate-900">
                {business.ouvert == null ? "—" : business.ouvert ? "Ouvert" : "Fermé"}
              </dd>
            </div>
          </dl>

          {caption && (
            <p className="mt-5 italic text-slate-500">&laquo;&nbsp;{caption}&nbsp;&raquo;</p>
          )}
          {label && (
            <span className="mt-3 inline-block rounded-full bg-slate-100 px-2.5 py-1 text-xs text-slate-600">
              {label}
            </span>
          )}

          {loadingReviews && <p className="mt-6 text-sm text-slate-500">Chargement des avis...</p>}

          {reviews && (
            <div className="mt-6 space-y-4 border-t border-slate-100 pt-4">
              <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                Derniers avis ({reviews.length})
              </p>
              {reviews.length === 0 && <p className="text-sm text-slate-500">Aucun avis trouvé.</p>}
              {reviews.map((r) => (
                <div key={r.review_id} className="text-sm">
                  <div className="flex items-center justify-between text-slate-500">
                    <span className="font-semibold text-slate-800">{r.note.toFixed(1)} / 5</span>
                    <span>{new Date(r.date_avis).toLocaleDateString("fr-FR")}</span>
                  </div>
                  <p className="mt-1 text-slate-600">{r.texte}</p>
                  <p className="mt-1 text-xs text-slate-400">
                    {r.utile} personne(s) ont trouvé cet avis utile
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
