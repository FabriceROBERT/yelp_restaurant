"use client";

import { useState } from "react";
import BusinessModal, { type BusinessInfo } from "./BusinessModal";

export type ValeurRow = {
  business: BusinessInfo;
  gamme_prix: string | null;
  note_moyenne: number;
  score_valeur_ajuste: number;
};

function prix(gamme: string | null) {
  return gamme ? "$".repeat(Number(gamme)) : "—";
}

export default function ValeurPercueTable({ rows }: { rows: ValeurRow[] }) {
  const [selected, setSelected] = useState<BusinessInfo | null>(null);
  const [photoUrl, setPhotoUrl] = useState<string | null>(null);

  async function openBusiness(business: BusinessInfo) {
    setSelected(business);
    setPhotoUrl(null);
    const res = await fetch(`/api/business-photo/${business.business_id}`);
    const data = await res.json();
    setPhotoUrl(data.url);
  }

  return (
    <>
      <table className="w-full text-left text-sm">
        <thead className="bg-slate-50 text-slate-500">
          <tr>
            <th className="px-4 py-3">Établissement</th>
            <th className="px-4 py-3">Ville</th>
            <th className="px-4 py-3">Prix</th>
            <th className="px-4 py-3 text-right">Note</th>
            <th className="px-4 py-3 text-right">Score ajusté</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((r) => (
            <tr
              key={r.business.business_id}
              onClick={() => openBusiness(r.business)}
              className="cursor-pointer hover:bg-slate-50"
            >
              <td className="px-4 py-2 font-medium text-slate-800">{r.business.nom}</td>
              <td className="px-4 py-2">
                {r.business.ville}, {r.business.state_code}
              </td>
              <td className="px-4 py-2">{prix(r.gamme_prix)}</td>
              <td className="px-4 py-2 text-right">{r.note_moyenne.toFixed(2)}</td>
              <td className="px-4 py-2 text-right">{r.score_valeur_ajuste.toFixed(4)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      {selected && (
        <BusinessModal
          business={selected}
          imageUrl={photoUrl ?? undefined}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
