"use client";
import { useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, endpoint, type RecordData } from "./api";
export function useData<T>(path: string, enabled = true) {
  return useQuery<T>({
    queryKey: [path],
    queryFn: () => api<T>(path),
    enabled,
    retry: false,
    refetchInterval: 30000,
  });
}
export function useItems(path: string) {
  return useData<{ items: RecordData[] }>(path);
}
export function useAction<T = RecordData>() {
  const client = useQueryClient();
  return useMutation<
    T,
    Error,
    { path: string; body?: unknown; method?: string }
  >({
    mutationFn: ({ path, body, method }) => api<T>(path, body, method),
    onSuccess: () => client.invalidateQueries(),
  });
}
export function useLive(path: string | undefined) {
  const client = useQueryClient();
  useEffect(() => {
    if (!path) return;
    const stream = new EventSource(endpoint(path));
    const refresh = () => {
      void client.invalidateQueries();
    };
    stream.addEventListener("delta", refresh);
    stream.addEventListener("reset", refresh);
    stream.addEventListener("plan", refresh);
    stream.onmessage = refresh;
    return () => stream.close();
  }, [path, client]);
}
