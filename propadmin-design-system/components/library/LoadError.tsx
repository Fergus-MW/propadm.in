"use client";

import { RotateCw } from "lucide-react";

import { Button } from "@/components/ui";

import { TEXT_ACTION_CLASS } from "./styles";
import { Surface } from "./Surface";

/**
 * What failed to load, what to do, and a retry. Announced to screen readers.
 * `bare` drops the surface and heading, for use inside a section that already
 * has both.
 */
export function LoadError({
  title,
  message,
  onRetry,
  bare = false,
}: {
  title: string;
  message?: string | null;
  onRetry: () => void;
  bare?: boolean;
}) {
  const body = (
    <>
      {bare ? (
        <p className="text-sm font-semibold">{title}</p>
      ) : (
        <h2 className="text-base font-semibold">{title}</h2>
      )}
      {message ? <p className="text-sm">{message.trim()}</p> : null}
      <Button variant="ghost" onClick={onRetry} className={TEXT_ACTION_CLASS}>
        <RotateCw />
        Try again
      </Button>
    </>
  );
  const layout = "flex flex-col items-start gap-3";
  return bare ? (
    <div role="alert" className={layout}>
      {body}
    </div>
  ) : (
    <Surface role="alert" className={layout}>
      {body}
    </Surface>
  );
}
