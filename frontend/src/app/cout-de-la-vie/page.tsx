import { query } from "../../lib/db";
import CoutVieChart from "../../components/CoutVieChart";
import ValeurPercueChart from "../../components/ValeurPercueChart";
import ValeurPercueTable, { type ValeurRow } from "../../components/ValeurPercueTable";

type KpiCoutVie = {
  state_code: string;
  cost_of_living_index: number;
  gamme_prix_moyenne: number | null;
  note_moyenne_etat: number;
  nb_etablissements: number;
};

type ScoreValeur = {
  business_id: string;
  nom: string;
  adresse: string | null;
  ville: string;
  state_code: string;
  code_postal: string | null;
  gamme_prix: string | null;
  note_moyenne: number;
  nb_avis: number | null;
  ouvert: boolean | null;
  cost_of_living_index: number;
  score_valeur_ajuste: number;
};

export default async function CoutDeLaViePage() {
  const [coutVie, topValeur] = await Promise.all([
    query<KpiCoutVie>(
      `SELECT state_code,
              cost_of_living_index::float AS cost_of_living_index,
              gamme_prix_moyenne::float AS gamme_prix_moyenne,
              note_moyenne_etat::float AS note_moyenne_etat,
              nb_etablissements::int AS nb_etablissements
       FROM gold.kpi_cout_vie_prix
       WHERE nb_etablissements >= 10
       ORDER BY cost_of_living_index DESC`
    ),
    query<ScoreValeur>(
      `SELECT svp.business_id, svp.nom, svp.ville, svp.state_code, svp.gamme_prix,
              svp.note_moyenne::float AS note_moyenne,
              svp.cost_of_living_index::float AS cost_of_living_index,
              svp.score_valeur_ajuste::float AS score_valeur_ajuste,
              db.adresse, db.code_postal, db.nb_avis, db.ouvert
       FROM gold.score_valeur_percue svp
       LEFT JOIN gold.dim_business db ON db.business_id = svp.business_id
       ORDER BY svp.score_valeur_ajuste DESC, db.nb_avis DESC NULLS LAST
       LIMIT 20`
    ),
  ]);

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <h1 className="mt-2 text-3xl font-bold">
        Coût de la vie et valeur perçue
      </h1>

      <p className="mt-3 text-slate-600">
        Analyse du positionnement prix et du score de valeur ajusté (note
        normalisée par le coût de la vie local).
      </p>

      <h2 className="mt-10 text-xl font-semibold">
        Positionnement prix / note par état
      </h2>
      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-6">
        <CoutVieChart
          data={coutVie.map((r) => ({
            state_code: r.state_code,
            cost_of_living_index: r.cost_of_living_index,
            note_moyenne_etat: r.note_moyenne_etat,
          }))}
        />
      </section>

      <section className="mt-6 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <table className="w-full text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-4 py-3">État</th>
              <th className="px-4 py-3 text-right">Indice coût de la vie</th>
              <th className="px-4 py-3 text-right">Prix moyen (1-4)</th>
              <th className="px-4 py-3 text-right">Note moyenne</th>
              <th className="px-4 py-3 text-right">Établissements</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {coutVie.map((r) => (
              <tr key={r.state_code}>
                <td className="px-4 py-2">{r.state_code}</td>
                <td className="px-4 py-2 text-right">{r.cost_of_living_index.toFixed(1)}</td>
                <td className="px-4 py-2 text-right">
                  {r.gamme_prix_moyenne != null ? r.gamme_prix_moyenne.toFixed(2) : "—"}
                </td>
                <td className="px-4 py-2 text-right">{r.note_moyenne_etat.toFixed(2)}</td>
                <td className="px-4 py-2 text-right">{r.nb_etablissements}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <h2 className="mt-10 text-xl font-semibold">
        Meilleur rapport qualité-prix (top 20)
      </h2>
      <section className="mt-4 rounded-2xl border border-slate-200 bg-white p-6">
        <ValeurPercueChart
          data={topValeur.map((r) => ({ nom: r.nom, score: r.score_valeur_ajuste }))}
        />
      </section>

      <section className="mt-6 overflow-x-auto rounded-2xl border border-slate-200 bg-white">
        <ValeurPercueTable
          rows={topValeur.map(
            (r): ValeurRow => ({
              business: {
                business_id: r.business_id,
                nom: r.nom,
                adresse: r.adresse,
                ville: r.ville,
                state_code: r.state_code,
                code_postal: r.code_postal,
                gamme_prix: r.gamme_prix,
                note_moyenne: r.note_moyenne,
                nb_avis: r.nb_avis,
                ouvert: r.ouvert,
              },
              gamme_prix: r.gamme_prix,
              note_moyenne: r.note_moyenne,
              score_valeur_ajuste: r.score_valeur_ajuste,
            })
          )}
        />
      </section>
    </main>
  );
}
