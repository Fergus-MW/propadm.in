export function sourceMime(filename: string, reported = ""): string {
  const extension = filename.split(".").pop()?.toLowerCase();
  return (
    (
      {
        pdf: "application/pdf",
        csv: "text/csv",
        ofx: "application/x-ofx",
        qfx: "application/x-ofx",
        md: "text/markdown",
        json: "application/json",
      } as Record<string, string>
    )[extension ?? ""] ??
    (reported || "text/plain")
  );
}
export function bytesBase64(bytes: Uint8Array): string {
  const chunks: string[] = [];
  for (let start = 0; start < bytes.length; start += 8192)
    chunks.push(String.fromCharCode(...bytes.subarray(start, start + 8192)));
  return btoa(chunks.join(""));
}
