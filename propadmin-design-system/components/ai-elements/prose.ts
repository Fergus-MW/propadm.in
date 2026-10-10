/**
 * Rendered markdown in the one ink, on the canvas. Typography's own greys are
 * a second neutral ramp and need `dark:prose-invert`; these map every prose
 * colour to a token instead, so both schemes follow the palette.
 */
export const PROSE_CLASS =
  "prose prose-sm max-w-none [--tw-prose-body:var(--foreground)] [--tw-prose-headings:var(--foreground)] [--tw-prose-lead:var(--foreground)] [--tw-prose-links:var(--foreground)] [--tw-prose-bold:var(--foreground)] [--tw-prose-counters:var(--foreground)] [--tw-prose-bullets:var(--foreground)] [--tw-prose-hr:var(--border)] [--tw-prose-quotes:var(--foreground)] [--tw-prose-quote-borders:var(--foreground)] [--tw-prose-captions:var(--foreground)] [--tw-prose-kbd:var(--foreground)] [--tw-prose-code:var(--foreground)] [--tw-prose-pre-code:var(--foreground)] [--tw-prose-pre-bg:transparent] [--tw-prose-th-borders:var(--border)] [--tw-prose-td-borders:var(--border)] prose-pre:border-l-4 prose-pre:border-foreground prose-pre:rounded-none prose-pre:pl-3 prose-code:before:content-none prose-code:after:content-none";
