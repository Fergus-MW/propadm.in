"use client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, type ReactNode } from "react";
import { Analytics } from "./analytics";
export function Providers({ children }: { children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { staleTime: 10000, retry: false } },
      }),
  );
  return <QueryClientProvider client={client}><Analytics />{children}</QueryClientProvider>;
}
