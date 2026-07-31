import Link from "next/link";
import { query } from "../lib/db";

type Summary = {
  nb_etablissements: number;
  nb_avis: number;
  note_moyenne: number;
  nb_villes: number;
};

const dashboardSections = [
  {
    title: "Qualité de service",
    description:
      "Analyse des notes et du volume d’avis par catégorie, ville et gamme de prix.",
    href: "/dashboard",
  },
  {
    title: "Météo et fréquentation",
    description:
      "Comparaison du nombre de check-ins entre les jours de pluie et de beau temps.",
    href: "/meteo",
  },
  {
    title: "Coût de la vie et prix",
    description:
      "Comparaison du positionnement prix des établissements avec le coût de la vie local.",
    href: "/cout-de-la-vie",
  },
  {
    title: "Valeur perçue",
    description:
      "Classement des établissements selon leur note, leur prix et leur contexte économique.",
    href: "/cout-de-la-vie",
  },
];

export default async function Home() {
  const [summary] = await query<Summary>(
    `SELECT nb_etablissements::int AS nb_etablissements,
            nb_avis::int AS nb_avis,
            note_moyenne::float AS note_moyenne,
            nb_villes::int AS nb_villes
     FROM gold.dim_summary
     ORDER BY date_calcul DESC
     LIMIT 1`
  );

  const indicators = [
    {
      title: "Établissements",
      value: summary?.nb_etablissements?.toLocaleString("fr-FR") ?? "—",
      description: "Nombre total de restaurants",
    },
    {
      title: "Avis",
      value: summary?.nb_avis?.toLocaleString("fr-FR") ?? "—",
      description: "Volume total d’avis Yelp",
    },
    {
      title: "Note moyenne",
      value: summary?.note_moyenne?.toFixed(2) ?? "—",
      description: "Moyenne globale sur 5",
    },
    {
      title: "Villes",
      value: summary?.nb_villes?.toLocaleString("fr-FR") ?? "—",
      description: "Nombre de villes analysées",
    },
  ];

  return (
    <main className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wider text-red-600">
              Yelp Data Warehouse
            </p>

            <h1 className="mt-1 text-2xl font-bold text-slate-900">
              Dashboard analytique
            </h1>
          </div>

          <div className="rounded-full bg-green-100 px-4 py-2 text-sm font-semibold text-green-700">
            PostgreSQL Gold
          </div>
        </div>
      </header>

      <div className="mx-auto max-w-7xl px-6 py-8">
        <section>
          <h2 className="text-lg font-bold text-slate-900">
            Vue d’ensemble
          </h2>

          <p className="mt-1 text-sm text-slate-600">
            Indicateurs principaux issus de la couche Gold du projet Yelp.
          </p>

          <div className="mt-5 grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
            {indicators.map((indicator) => (
              <article
                key={indicator.title}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <p className="text-sm font-medium text-slate-500">
                  {indicator.title}
                </p>

                <p className="mt-3 text-3xl font-bold text-slate-900">
                  {indicator.value}
                </p>

                <p className="mt-2 text-sm text-slate-500">
                  {indicator.description}
                </p>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-10">
          <h2 className="text-lg font-bold text-slate-900">
            Analyses disponibles
          </h2>

          <p className="mt-1 text-sm text-slate-600">
            Les graphiques seront progressivement connectés aux tables
            PostgreSQL du schéma Gold.
          </p>

          <div className="mt-5 grid gap-5 md:grid-cols-2">
            {dashboardSections.map((section) => (
              <article
                key={section.title}
                className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <div className="flex items-start gap-4">
                  <div>
                    <h3 className="text-lg font-bold text-slate-900">
                      {section.title}
                    </h3>

                    <p className="mt-2 leading-6 text-slate-600">
                      {section.description}
                    </p>

                    <Link
                      href={section.href}
                      className="mt-5 inline-block rounded-lg bg-slate-900 px-4 py-2 text-sm font-semibold text-white transition hover:bg-slate-700"
                    >
                      Consulter l’analyse
                    </Link>
                  </div>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="mt-10 rounded-2xl bg-slate-900 p-7 text-white">
          <p className="text-sm font-semibold uppercase tracking-wider text-red-400">
            Recommandation
          </p>

          <h2 className="mt-2 text-2xl font-bold">
            Trouver les meilleures recommandations Yelp
          </h2>

          <p className="mt-3 max-w-3xl leading-7 text-slate-300">
            Le moteur proposera des recommandations collaboratives, des
            suggestions pour les nouveaux utilisateurs, une adaptation au coût
            de la vie et une sélection de pépites sous-évaluées.
          </p>

          <Link
            href="/recommandations"
            className="mt-6 inline-block rounded-lg bg-red-600 px-5 py-3 font-semibold text-white transition hover:bg-red-500"
          >
            Ouvrir les recommandations
          </Link>
        </section>
      </div>
    </main>
  );
}
