import type { NextRequest } from "next/server";
import { query } from "../../../../lib/db";
import { getPhotoUrlByPhotoId } from "../../../../lib/minio";

export async function GET(
  _req: NextRequest,
  ctx: RouteContext<"/api/business-photo/[businessId]">
) {
  const { businessId } = await ctx.params;

  const [row] = await query<{ photo_id: string }>(
    `SELECT photo_id FROM gold.dim_business_photos WHERE business_id = $1 LIMIT 1`,
    [businessId]
  );

  if (!row) return Response.json({ url: null });

  const url = await getPhotoUrlByPhotoId(row.photo_id);
  return Response.json({ url });
}
