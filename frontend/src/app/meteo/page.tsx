import { query } from "../../lib/db";
import MeteoChart from "../../components/MeteoChart";

type KpiMeteo = {
  ville: string;
  condition_meteo: string;
  nb_checkins_moyen_jour: number;
};

export default async function MeteoPage() {
  const rows = await query<KpiMeteo>(
    `SELECT ville, condition_meteo, nb_checkins_moyen_jour::float AS nb_checkins_moyen_jour
     FROM gold.kpi_meteo_frequentation
     ORDER BY ville, condition_meteo`
  );

  const parVille = new Map<string, { beauTemps?: number; pluie?: number }>();
  for (const r of rows) {
    const entry = parVille.get(r.ville) ?? {};
    if (r.condition_meteo === "pluie") entry.pluie = r.nb_checkins_moyen_jour;
    else entry.beauTemps = r.nb_checkins_moyen_jour;
    parVille.set(r.ville, entry);
  }

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <h1 className="mt-2 text-3xl font-bold">Météo et fréquentation</h1>

      <p className="mt-3 text-slate-600">
        Check-ins moyens par jour, jours de pluie vs beau temps. Échantillon
        limité aux villes couvertes par l&apos;ingestion météo (quota API
        limité).
      </p>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-6">
        <MeteoChart
          data={[...parVille.entries()].map(([ville, v]) => ({
            ville,
            beauTemps: v.beauTemps ?? null,
            pluie: v.pluie ?? null,
          }))}
        />
      </section>

      <section className="mt-6 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3">Ville</th>
              <th className="px-4 py-3 text-right">Beau temps</th>
              <th className="px-4 py-3 text-right">Pluie</th>
              <th className="px-4 py-3 text-right">Écart</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[...parVille.entries()].map(([ville, v]) => {
              const ecart =
                v.beauTemps != null && v.pluie != null ? v.pluie - v.beauTemps : null;
              return (
                <tr key={ville}>
                  <td className="px-4 py-2">{ville}</td>
                  <td className="px-4 py-2 text-right">{v.beauTemps?.toFixed(1) ?? "—"}</td>
                  <td className="px-4 py-2 text-right">{v.pluie?.toFixed(1) ?? "—"}</td>
                  <td
                    className={`px-4 py-2 text-right ${
                      ecart != null && ecart < 0 ? "text-red-600" : "text-emerald-600"
                    }`}
                  >
                    {ecart != null ? `${ecart >= 0 ? "+" : ""}${ecart.toFixed(1)}` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>
    </main>
  );
}
