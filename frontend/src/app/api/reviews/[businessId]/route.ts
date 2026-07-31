import type { NextRequest } from "next/server";
import { query } from "../../../../lib/db";

type Review = {
  review_id: string;
  note: number;
  texte: string;
  date_avis: string;
  utile: number;
};

export async function GET(_req: NextRequest, ctx: RouteContext<"/api/reviews/[businessId]">) {
  const { businessId } = await ctx.params;

  const reviews = await query<Review>(
    `SELECT review_id, note::float AS note, texte,
            date_avis::text AS date_avis, utile::int AS utile
     FROM gold.dim_review
     WHERE business_id = $1
     ORDER BY date_avis DESC
     LIMIT 20`,
    [businessId]
  );

  return Response.json({ reviews });
}
