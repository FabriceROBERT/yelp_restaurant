export default function PepitesPage() {
  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <p className="text-sm font-semibold uppercase tracking-wider text-red-600">
        B4
      </p>

      <h1 className="mt-2 text-3xl font-bold">
        Pépites sous-évaluées
      </h1>

      <p className="mt-3 text-slate-600">
        Restaurants ayant peu d’avis, mais une note et un sentiment très
        positifs.
      </p>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-slate-500">
          Les données de gold.pepites_sous_evaluees seront affichées ici.
        </p>
      </section>
    </main>
  );
}