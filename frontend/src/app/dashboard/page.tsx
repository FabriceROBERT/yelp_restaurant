import { query } from "../../lib/db";

type KpiBusiness = {
  categorie: string;
  ville: string;
  gamme_prix: string | null;
  note_moyenne: number;
  nb_avis_total: number;
  nb_etablissements: number;
};

export default async function DashboardPage() {
  const rows = await query<KpiBusiness>(
    `SELECT categorie, ville, gamme_prix,
            note_moyenne::float AS note_moyenne,
            nb_avis_total::int AS nb_avis_total,
            nb_etablissements::int AS nb_etablissements
     FROM gold.kpi_business
     WHERE categorie IS NOT NULL AND gamme_prix IS NOT NULL AND nb_etablissements >= 15
     ORDER BY nb_avis_total DESC
     LIMIT 30`
  );

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <h1 className="mt-2 text-3xl font-bold">Qualité de service</h1>

      <p className="mt-3 text-slate-600">
        Note moyenne et volume d&apos;avis par catégorie, ville et gamme de
        prix (min. 15 établissements par groupe, prix connu), triées par
        volume d&apos;avis.
      </p>

      <section className="mt-8 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3">Catégorie</th>
              <th className="px-4 py-3">Ville</th>
              <th className="px-4 py-3">Prix</th>
              <th className="px-4 py-3 text-right">Note moyenne</th>
              <th className="px-4 py-3 text-right">Avis</th>
              <th className="px-4 py-3 text-right">Établissements</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((r, i) => (
              <tr key={i}>
                <td className="px-4 py-2">{r.categorie}</td>
                <td className="px-4 py-2">{r.ville}</td>
                <td className="px-4 py-2">
                  {r.gamme_prix ? "$".repeat(Number(r.gamme_prix)) : "—"}
                </td>
                <td className="px-4 py-2 text-right">{r.note_moyenne.toFixed(2)}</td>
                <td className="px-4 py-2 text-right">{r.nb_avis_total}</td>
                <td className="px-4 py-2 text-right">{r.nb_etablissements}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
