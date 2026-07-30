export default function MeteoPage() {
  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <p className="text-sm font-semibold uppercase tracking-wider text-red-600">
        A2
      </p>

      <h1 className="mt-2 text-3xl font-bold">
        Météo et fréquentation
      </h1>

      <p className="mt-3 text-slate-600">
        Comparaison des check-ins entre les jours de pluie et de beau temps.
      </p>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-slate-500">
          Les données de gold.kpi_meteo_frequentation seront affichées ici.
        </p>
      </section>
    </main>
  );
}