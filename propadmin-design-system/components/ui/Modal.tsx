"use client";

import type { ReactNode } from "react";

import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  ScrollFadeArrow,
  useScrollFadeAffordance,
} from "@/components/ui/ScrollFadeAffordance";
import { cn } from "@/lib/utils";

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  className?: string;
  /** Override classes on the scrollable content wrapper */
  contentClassName?: string;
}

/**
 * A titled dialog with an optional footer. Built on `Dialog`, so it shares the
 * one dialog design (square, no border or shadow, focus trapped, Esc closes).
 */
export function Modal({
  isOpen,
  onClose,
  title,
  children,
  footer,
  className,
  contentClassName,
}: ModalProps) {
  const { contentRef, hasMoreBelow, onScroll } =
    useScrollFadeAffordance(isOpen);
  // DialogContent sizes itself with sm:max-w-lg; a caller's plain max-w-* width
  // must win at that breakpoint too, so it is applied at sm: as well.
  const width = className?.replace(/(^|\s)max-w-/g, "$1sm:max-w-");

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className={width}>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <div
          ref={contentRef}
          onScroll={onScroll}
          className={cn("max-h-[60vh] overflow-y-auto p-1", contentClassName)}
        >
          {children}
          <ScrollFadeArrow visible={hasMoreBelow} />
        </div>
        {footer ? <DialogFooter>{footer}</DialogFooter> : null}
      </DialogContent>
    </Dialog>
  );
}
