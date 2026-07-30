import type { Metadata } from "next";
import Navbar from "../components/Navbar";
import "./globals.css";

export const metadata: Metadata = {
  title: "Yelp Data Analytics",
  description: "Dashboard analytique et moteur de recommandation Yelp",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr">
      <body className="bg-slate-100 text-slate-900">
        <Navbar />
        {children}
      </body>
    </html>
  );
}