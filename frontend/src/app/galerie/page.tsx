import { getSamplePhotoUrls } from "../../lib/minio";
import { query } from "../../lib/db";
import PhotoGallery, { type GalleryPhoto } from "../../components/PhotoGallery";

type Row = {
  photo_id: string;
  caption: string | null;
  label: string | null;
  business_id: string;
  nom: string | null;
  adresse: string | null;
  ville: string | null;
  state_code: string | null;
  code_postal: string | null;
  gamme_prix: string | null;
  note_moyenne: number | null;
  nb_avis: number | null;
  ouvert: boolean | null;
};

const TARGET_COUNT = 24;
// On sur-échantillonne côté MinIO car une partie des photos brutes ont été
// éliminées par la dédup Silver (donc absentes de gold.dim_business_photos) -
// on filtre ensuite pour n'afficher que des photos liées à un établissement.
const FETCH_COUNT = 80;

export default async function GaleriePage() {
  const photos = await getSamplePhotoUrls(FETCH_COUNT);

  const rows =
    photos.length === 0
      ? []
      : await query<Row>(
          `SELECT dbp.photo_id, dbp.caption, dbp.label,
                  db.business_id, db.nom, db.adresse, db.ville, db.state_code,
                  db.code_postal, db.gamme_prix,
                  db.note_moyenne::float AS note_moyenne,
                  db.nb_avis::int AS nb_avis, db.ouvert
           FROM gold.dim_business_photos dbp
           JOIN gold.dim_business db ON db.business_id = dbp.business_id
           WHERE dbp.photo_id = ANY($1::text[])`,
          [photos.map((p) => p.photoId)]
        );

  const rowByPhotoId = new Map(rows.map((r) => [r.photo_id, r]));

  const gallery: GalleryPhoto[] = photos
    .map((photo) => {
      const row = rowByPhotoId.get(photo.photoId);
      if (!row) return null; // photo non liée (dédupliquée en Silver) - on l'exclut
      return {
        key: photo.key,
        url: photo.url,
        caption: row.caption,
        label: row.label,
        business: {
          business_id: row.business_id,
          nom: row.nom,
          adresse: row.adresse,
          ville: row.ville,
          state_code: row.state_code,
          code_postal: row.code_postal,
          gamme_prix: row.gamme_prix,
          note_moyenne: row.note_moyenne,
          nb_avis: row.nb_avis,
          ouvert: row.ouvert,
        },
      } satisfies GalleryPhoto;
    })
    .filter((p): p is GalleryPhoto => p !== null)
    .slice(0, TARGET_COUNT);

  return (
    <main className="mx-auto max-w-7xl px-6 py-10">
      <p className="text-sm font-semibold uppercase tracking-wider text-red-600">
        Bronze / Silver / Gold
      </p>

      <h1 className="mt-2 text-3xl font-bold">Galerie</h1>

      <p className="mt-3 text-slate-600">
        Photos (non-structuré) issues du dataset Yelp, validées et
        dédupliquées en Silver (hash exact + hash perceptif), liées à leur
        établissement via <code>photos.json</code>. Clique sur une photo pour
        voir la fiche de l&apos;établissement.
      </p>

      {gallery.length === 0 ? (
        <section className="mt-8 rounded-2xl border border-slate-200 bg-white p-8">
          <p className="text-slate-500">
            Aucune photo liée trouvée. Vérifie que{" "}
            <code>jobs/prepare_silver_photos_sample.py</code>,{" "}
            <code>jobs/transform_silver_photos.py</code> et le job Gold ont
            bien tourné.
          </p>
        </section>
      ) : (
        <PhotoGallery photos={gallery} />
      )}
    </main>
  );
}
