"use client";
import { useState } from "react";
import { ArrowUp, Plus } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Conversation,
  ConversationContent,
  ConversationEmptyState,
  ConversationScrollButton,
} from "../ai-elements/conversation";
import {
  Message,
  MessageContent,
  MessageResponse,
} from "../ai-elements/message";
import { State } from "../common";
import { Button } from "../ui/Button";
import { Textarea } from "../ui/textarea";
import { StatusText } from "../library/StatusText";
import { api, rows, str, time, type RecordData } from "@/lib/api";
import { useData } from "@/lib/hooks";

type Run = RecordData & { status: string; transcript?: RecordData[] };

/** Consecutive tool calls collapse into one "Used a, b" line between messages. */
export function groupTools(transcript: RecordData[]): RecordData[] {
  const grouped: RecordData[] = [];
  for (const entry of transcript) {
    const last = grouped.at(-1);
    if (!entry.tool) grouped.push(entry);
    else if (last && Array.isArray(last.tools)) last.tools.push(entry.tool);
    else grouped.push({ id: entry.id, tools: [entry.tool] });
  }
  return grouped;
}

function Entry({ entry }: { entry: RecordData }) {
  if (entry.type === "user.message")
    return (
      <Message from="user">
        <MessageContent>{str(entry.text)}</MessageContent>
      </Message>
    );
  if (entry.type === "agent.message")
    return (
      <Message from="assistant">
        <MessageContent>
          <MessageResponse>{str(entry.text)}</MessageResponse>
        </MessageContent>
      </Message>
    );
  if (Array.isArray(entry.tools))
    return (
      <p className="caption -my-4">
        Used{" "}
        {entry.tools.map((tool, index) => (
          <span key={index}>
            {index > 0 && ", "}
            <code>{str(tool)}</code>
          </span>
        ))}
      </p>
    );
  if (entry.error)
    return (
      <StatusText variant="error" className="whitespace-normal">
        {str(entry.error)}
      </StatusText>
    );
  return null;
}

export function AdminAgent() {
  const client = useQueryClient();
  const [id, setId] = useState("");
  const [draft, setDraft] = useState("");
  const [sent, setSent] = useState("");
  const threads = useData<{ items: Run[] }>("agent-runs?kind=admin");
  // Syncing relays new session events; the agent service returns early once a chat is idle.
  const run = useQuery<Run>({
    queryKey: ["admin-chat", id],
    queryFn: () => api<Run>(`agent-runs/${encodeURIComponent(id)}/sync`, {}),
    enabled: Boolean(id),
    retry: false,
    refetchInterval: (query) =>
      query.state.data?.status === "running" ? 2000 : false,
  });
  const send = useMutation<Run, Error, string>({
    mutationFn: (message) =>
      api<Run>("admin-chat", { message, run_id: id || null }),
    onMutate: (message) => {
      setSent(message);
      setDraft("");
    },
    onError: (_error, message) => setDraft(message),
    onSuccess: (saved) => {
      setId(saved.id);
      client.setQueryData(["admin-chat", saved.id], saved);
      void threads.refetch();
    },
  });
  const transcript = rows(id ? run.data?.transcript : []);
  const working = send.isPending || (Boolean(id) && run.data?.status === "running");
  const lastUser = transcript.findLast((e) => e.type === "user.message");
  // Show the admin's message at once; the transcript catches up on the next sync.
  const optimistic = working && sent && lastUser?.text !== sent ? sent : "";
  const submit = () => {
    if (draft.trim() && !working) send.mutate(draft.trim());
  };
  return (
    <div className="admin-chat">
      <aside className="chat-threads" aria-label="Chat threads">
        <Button
          variant="ghost"
          className="justify-start"
          onClick={() => {
            setId("");
            setSent("");
          }}
        >
          <Plus size={16} /> New chat
        </Button>
        <nav className="chat-thread-list">
          {rows(threads.data?.items).map((thread) => (
            <button
              key={thread.id}
              type="button"
              className={`chat-thread ${thread.id === id ? "active" : ""}`}
              aria-current={thread.id === id ? "page" : undefined}
              onClick={() => setId(thread.id)}
            >
              <span className="truncate">{str(thread.goal)}</span>
              <span className="caption">{time(thread.created_at)}</span>
            </button>
          ))}
        </nav>
        <State error={threads.error} retry={() => void threads.refetch()} />
      </aside>
      <section className="chat-main">
        {id || optimistic ? (
          <Conversation>
            <ConversationContent>
              <State
                pending={Boolean(id) && run.isPending}
                error={run.error}
                retry={() => void run.refetch()}
              />
              {groupTools(transcript).map((entry, index) => (
                <Entry key={str(entry.id ?? index)} entry={entry} />
              ))}
              {optimistic && (
                <Message from="user">
                  <MessageContent>{optimistic}</MessageContent>
                </Message>
              )}
              {working && (
                <div className="loading" aria-live="polite">
                  <div className="shimmer-fill" data-active="" />
                  Working…
                </div>
              )}
            </ConversationContent>
            <ConversationScrollButton />
          </Conversation>
        ) : (
          <ConversationEmptyState
            title="What can I help with?"
            description="Ask about the graph, rules, entity types, providers or settings. The admin agent can read and change all of them."
          />
        )}
        <form
          className="chat-composer"
          onSubmit={(event) => {
            event.preventDefault();
            submit();
          }}
        >
          <State error={send.error} />
          <div className="chat-composer-box">
            <Textarea
              aria-label="Message the admin agent"
              rows={1}
              value={draft}
              placeholder="Message the admin agent"
              className="max-h-48 min-h-12 resize-none"
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  submit();
                }
              }}
            />
            <Button
              type="submit"
              size="icon"
              aria-label="Send message"
              disabled={!draft.trim() || working}
            >
              <ArrowUp />
            </Button>
          </div>
          <p className="caption">
            Enter to send · Shift + Enter for a new line
          </p>
        </form>
      </section>
    </div>
  );
}
