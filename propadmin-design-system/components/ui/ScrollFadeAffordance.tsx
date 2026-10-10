"use client";

import { ChevronDown } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { hasMoreContentBelow } from "@/components/ui/scrollFade";
import { cn } from "@/lib/utils";

/**
 * Tracks whether a scroll container still has content below the fold.
 * Pair `contentRef` + `onScroll` on the overflow element, then render
 * `ScrollFadeArrow` as its last child (sticky fade lives inside the scroller).
 */
export function useScrollFadeAffordance(active = true) {
  const contentRef = useRef<HTMLDivElement>(null);
  const isScrollableRef = useRef(false);
  const [hasMoreBelow, setHasMoreBelow] = useState(false);

  const syncScrollAffordance = useCallback(() => {
    const node = contentRef.current;
    if (!node || !isScrollableRef.current) {
      setHasMoreBelow(false);
      return;
    }
    setHasMoreBelow(
      hasMoreContentBelow(node.scrollTop, node.clientHeight, node.scrollHeight),
    );
  }, []);

  useEffect(() => {
    const node = contentRef.current;
    if (!active || !node) {
      return;
    }

    const { overflowY } = window.getComputedStyle(node);
    isScrollableRef.current = overflowY === "auto" || overflowY === "scroll";

    // ResizeObserver delivers an initial observation on observe(), which seeds
    // the affordance state — no synchronous measurement needed here.
    const observer = new ResizeObserver(syncScrollAffordance);
    observer.observe(node);
    // The first child grows/shrinks as content renders, which changes
    // scrollHeight without resizing `node`.
    if (node.firstElementChild) {
      observer.observe(node.firstElementChild);
    }

    return () => observer.disconnect();
  }, [active, syncScrollAffordance]);

  return {
    contentRef,
    hasMoreBelow,
    onScroll: syncScrollAffordance,
  };
}

interface ScrollFadeArrowProps {
  visible: boolean;
  /** Match the scroll container background so the fade blends. */
  from?: "background" | "card";
}

export function ScrollFadeArrow({
  visible,
  from = "background",
}: ScrollFadeArrowProps) {
  if (!visible) {
    return null;
  }

  return (
    /* Pinned to the bottom of the scroll container's viewport.
       `-mt-12` cancels its own height so it adds no scrollable space.
       `-bottom-1` reaches through the container's `p-1` bottom padding —
       sticky pins to the padding box, which would otherwise leave a
       sliver of unfaded content below the gradient. */
    <div
      aria-hidden
      className={cn(
        "pointer-events-none sticky -bottom-1 -mt-12 flex h-12 items-end justify-center pb-1",
        from === "card"
          ? "bg-gradient-to-t from-card from-20% via-card/80 to-transparent"
          : "bg-gradient-to-t from-background from-20% via-background/80 to-transparent",
      )}
    >
      <ChevronDown className="size-4 animate-bounce text-muted-foreground motion-reduce:animate-none" />
    </div>
  );
}
