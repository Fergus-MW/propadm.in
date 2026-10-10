import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { PROSE_CLASS } from "@/components/ai-elements/prose";
import { cn } from "@/lib/utils";

interface MarkdownProps {
  content: string;
  className?: string;
}

export function Markdown({ content, className }: MarkdownProps) {
  return (
    <div
      className={cn(
        PROSE_CLASS,
        // Headings
        "prose-headings:font-semibold",
        // Lists
        "prose-ul:my-2 prose-ol:my-2 prose-li:my-0",
        // Paragraphs
        "prose-p:my-2 prose-p:leading-relaxed",
        // Code
        "prose-code:text-sm",
        // Pre/code blocks
        // Links
        "prose-a:text-brand prose-a:underline-offset-2",
        // Strong/bold
        "prose-strong:font-semibold",
        className,
      )}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  );
}
