"use client";
import { useState } from "react";
import { ArrowUpRight } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Header, State, Status } from "../common";
import { Button } from "../ui/Button";
import { FormSelect, FormTextarea } from "../ui/Input";
import { StatusText } from "../library/StatusText";
import { EmptyState } from "../library/EmptyState";
import { api, rows, str, time, type RecordData } from "@/lib/api";
import { useData } from "@/lib/hooks";

type Run = RecordData & { status: string; transcript?: RecordData[] };

function Entry({ entry }: { entry: RecordData }) {
  if (entry.type === "user.message" || entry.type === "agent.message")
    return (
      <div className="section">
        <p className="caption">
          {entry.type === "user.message" ? "You" : "Admin agent"} ·{" "}
          {time(entry.at)}
        </p>
        <article className="source-text">{str(entry.text)}</article>
      </div>
    );
  if (entry.tool)
    return (
      <p className="caption">
        Used <code>{str(entry.tool)}</code>
      </p>
    );
  if (entry.error)
    return <StatusText variant="error">{str(entry.error)}</StatusText>;
  return null;
}

export function AdminAgent() {
  const client = useQueryClient();
  const [id, setId] = useState("");
  const [draft, setDraft] = useState("");
  const chats = useData<{ items: Run[] }>("agent-runs?kind=admin");
  // Syncing relays new session events; the agent service returns early once a chat is idle.
  const run = useQuery<Run>({
    queryKey: ["admin-chat", id],
    queryFn: () =>
      api<Run>(`agent-runs/${encodeURIComponent(id)}/sync`, {}),
    enabled: Boolean(id),
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 2000 : false,
  });
  const send = useMutation<Run, Error, string>({
    mutationFn: (message) =>
      api<Run>("admin-chat", { message, run_id: id || null }),
    onSuccess: (saved) => {
      setDraft("");
      setId(saved.id);
      client.setQueryData(["admin-chat", saved.id], saved);
      void chats.refetch();
    },
  });
  const transcript = rows(run.data?.transcript);
  const working = run.data?.status === "running" || send.isPending;
  return (
    <>
      <Header title="Admin agent">
        {id && (
          <Button variant="ghost" onClick={() => setId("")}>
            New chat
          </Button>
        )}
      </Header>
      {rows(chats.data?.items).length > 0 && (
        <div className="form">
          <FormSelect
            label="Chat"
            value={id}
            onChange={(event) => setId(event.target.value)}
            options={[
              { value: "", label: "New chat" },
              ...rows(chats.data?.items).map((chat) => ({
                value: chat.id,
                label: `${str(chat.goal).slice(0, 80)} · ${time(chat.created_at)}`,
              })),
            ]}
          />
        </div>
      )}
      {id && (
        <div className="actions caption section">
          <Status value={run.data?.status ?? "loading"} />
        </div>
      )}
      <State
        pending={Boolean(id) && run.isPending}
        error={run.error}
        retry={() => void run.refetch()}
      />
      <div aria-live="polite">
        {id ? (
          transcript.map((entry, index) => (
            <Entry key={str(entry.id ?? index)} entry={entry} />
          ))
        ) : (
          <EmptyState message="Ask about the graph, rules, schema, providers or settings." />
        )}
      </div>
      {working && (
        <div className="loading section">
          <div className="shimmer-fill" data-active="" />
          Working…
        </div>
      )}
      <form
        className="form section"
        onSubmit={(event) => {
          event.preventDefault();
          if (draft.trim()) send.mutate(draft.trim());
        }}
      >
        <FormTextarea
          label="Message"
          rows={4}
          required
          value={draft}
          disabled={working}
          placeholder="e.g. Add a notes field to the contractor type"
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && (event.metaKey || event.ctrlKey))
              event.currentTarget.form?.requestSubmit();
          }}
        />
        <State error={send.error} />
        <div className="actions">
          <Button type="submit" loading={send.isPending} disabled={working}>
            Send <ArrowUpRight size={16} />
          </Button>
          <span className="caption">⌘/Ctrl + Enter</span>
        </div>
      </form>
    </>
  );
}
