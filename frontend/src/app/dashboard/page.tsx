export default function DashboardPage() {
  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <p className="text-sm font-semibold uppercase tracking-wider text-red-600">
        A1
      </p>

      <h1 className="mt-2 text-3xl font-bold">
        Qualité de service
      </h1>

      <p className="mt-3 text-slate-600">
        Analyse des notes, des avis, des catégories, des villes et des gammes
        de prix.
      </p>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-slate-500">
          Les graphiques de la table gold.kpi_business seront affichés ici.
        </p>
      </section>
    </main>
  );
}