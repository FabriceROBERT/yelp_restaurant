export default function CoutDeLaViePage() {
  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <p className="text-sm font-semibold uppercase tracking-wider text-red-600">
        A3 et A4
      </p>

      <h1 className="mt-2 text-3xl font-bold">
        Coût de la vie et valeur perçue
      </h1>

      <p className="mt-3 text-slate-600">
        Analyse du positionnement prix et du score de valeur ajusté.
      </p>

      <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-8">
        <p className="text-slate-500">
          Les données des tables gold.kpi_cout_vie_prix et
          gold.score_valeur_percue seront affichées ici.
        </p>
      </section>
    </main>
  );
}