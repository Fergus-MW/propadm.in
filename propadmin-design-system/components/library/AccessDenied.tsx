/** One line for a page the viewer's role cannot open. */
export function AccessDenied({ what }: { what: string }) {
  return (
    <p role="alert" className="py-6 text-sm">
      Only workspace admins can manage {what}.
    </p>
  );
}
