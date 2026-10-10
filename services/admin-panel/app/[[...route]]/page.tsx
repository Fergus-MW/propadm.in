import { Suspense } from "react";
import { Screen } from "@/components/screen";
import { decodeRouteSegment } from "@/lib/routes";
export default async function Page({
  params,
}: {
  params: Promise<{ route?: string[] }>;
}) {
  const { route = [] } = await params;
  return (
    <Suspense fallback={<p>Loading…</p>}>
      <Screen route={route.map(decodeRouteSegment)} />
    </Suspense>
  );
}
