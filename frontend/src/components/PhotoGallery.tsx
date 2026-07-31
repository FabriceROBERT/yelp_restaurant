"use client";

import { useState } from "react";
import BusinessModal, { type BusinessInfo } from "./BusinessModal";

export type GalleryPhoto = {
  key: string;
  url: string;
  caption: string | null;
  label: string | null;
  business: BusinessInfo;
};

export default function PhotoGallery({ photos }: { photos: GalleryPhoto[] }) {
  const [selected, setSelected] = useState<GalleryPhoto | null>(null);

  return (
    <>
      <section className="mt-8 grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
        {photos.map((photo) => (
          <button
            key={photo.key}
            type="button"
            onClick={() => setSelected(photo)}
            className="group overflow-hidden rounded-xl border border-slate-200 bg-white text-left transition hover:shadow-md"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photo.url}
              alt={photo.caption || photo.business.nom || photo.key}
              className="aspect-square w-full object-cover transition group-hover:scale-105"
              loading="lazy"
            />
            <div className="p-3 text-xs">
              <p className="truncate font-semibold text-slate-800">
                {photo.business.nom ?? photo.business.business_id}
              </p>
              {photo.business.ville && (
                <p className="text-slate-500">{photo.business.ville}</p>
              )}
            </div>
          </button>
        ))}
      </section>

      {selected && (
        <BusinessModal
          business={selected.business}
          imageUrl={selected.url}
          caption={selected.caption}
          label={selected.label}
          onClose={() => setSelected(null)}
        />
      )}
    </>
  );
}
