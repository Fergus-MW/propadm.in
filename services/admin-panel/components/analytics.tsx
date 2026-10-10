"use client";

import { usePathname } from "next/navigation";
import { useEffect, useRef } from "react";
import { captureAnalytics } from "@/lib/analytics";

export function Analytics() {
  const pathname = usePathname();
  const previous = useRef<string | null>(null);
  useEffect(() => {
    if (previous.current === pathname || pathname.startsWith("/track/")) return;
    previous.current = pathname;
    captureAnalytics("$pageview", {
      $current_url: `${window.location.origin}${pathname}`,
      $pathname: pathname,
    });
  }, [pathname]);
  return null;
}
