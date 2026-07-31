import Link from "next/link";

const navigation = [
  { label: "Accueil", href: "/" },
  { label: "Dashboard", href: "/dashboard" },
  { label: "Météo", href: "/meteo" },
  { label: "Coût de la vie", href: "/cout-de-la-vie" },
  { label: "Galerie", href: "/galerie" },
  { label: "Recommandations", href: "/recommandations" },
  { label: "Pépites", href: "/pepites" },
];

export default function Navbar() {
  return (
    <header className="border-b border-slate-200 bg-white">
      <div className="mx-auto flex max-w-7xl flex-col gap-4 px-6 py-5 lg:flex-row lg:items-center lg:justify-between">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-red-600 text-lg font-bold text-white">
            Y
          </div>

          <div>
            <p className="font-bold text-slate-900">
              Yelp Data Analytics
            </p>
            <p className="text-xs text-slate-500">
              Data Lake & Warehouse
            </p>
          </div>
        </Link>

        <nav className="flex flex-wrap gap-2">
          {navigation.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-red-600"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}