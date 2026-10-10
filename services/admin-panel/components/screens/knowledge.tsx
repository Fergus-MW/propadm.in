"use client";
import { bytesBase64, sourceMime } from "@/lib/source";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { FileText, Search as SearchIcon, Upload } from "lucide-react";
import { Header, State, Section, Status, Records, Json } from "../common";
import { Button } from "../ui/Button";
import { FormInput, FormSelect, FormTextarea } from "../ui/Input";
import { StatGrid } from "../library/StatGrid";
import { EmptyState } from "../library/EmptyState";
import { object, rows, str, time, type RecordData } from "@/lib/api";
import { useAction, useData, useItems } from "@/lib/hooks";
export function Overview() {
  const data = useData<RecordData>("overview");
  return (
    <>
      <Header title="Overview">
        <Link className="draw-underline" href="/actions">
          View change log
        </Link>
        <Button asChild>
          <Link href="/ingestion">
            <Upload size={16} />
            Add knowledge
          </Link>
        </Button>
      </Header>
      <State
        pending={data.isPending}
        error={data.error}
        retry={() => void data.refetch()}
      />
      {data.data && (
        <>
          <StatGrid
            stats={Object.entries(object(data.data.counts))
              .filter(([, value]) => Number(value) > 0)
              .map(([label, value]) => ({
                label: label.replaceAll("_", " "),
                value: Number(value).toLocaleString("en-GB"),
              }))}
            className="!gap-y-8 [&_dd]:!text-5xl"
          />
          <div className="two-columns">
            <Section title="Recent activity">
              <Records
                items={rows(data.data.recent_actions)}
                columns={[
                  {
                    key: "reason",
                    title: "Action",
                    render: (row) => (
                      <div>
                        <p className="whitespace-normal max-w-sm">
                          {str(row.reason ?? row.kind ?? row.tool)}
                        </p>
                        <span className="caption">
                          {str(row.actor ?? row.run_id)}
                        </span>
                      </div>
                    ),
                  },
                  {
                    key: "status",
                    title: "Status",
                    render: (row) => (
                      <Status value={row.status ?? "recorded"} />
                    ),
                  },
                  {
                    key: "created_at",
                    title: "When",
                    render: (row) => time(row.created_at),
                  },
                ]}
              />
            </Section>
            <div>
              <Section title="Runtime">
                <dl className="fact-grid">
                  {Object.entries(object(data.data.runtime)).map(
                    ([key, value]) => (
                      <div className="fact" key={key}>
                        <dt>{key.replaceAll("_", " ")}</dt>
                        <dd>{str(value)}</dd>
                      </div>
                    ),
                  )}
                </dl>
              </Section>
              <Section title="Workspaces">
                <div className="result">
                  <Link className="draw-underline" href="/graph">
                    Explore the knowledge graph ↗
                  </Link>
                  <p className="caption">
                    Entities, sources and their connections.
                  </p>
                </div>
                <div className="result">
                  <Link className="draw-underline" href="/rules">
                    Review connection rules ↗
                  </Link>
                  <p className="caption">
                    Versioned criteria and matched evidence.
                  </p>
                </div>
              </Section>
            </div>
          </div>
        </>
      )}
    </>
  );
}
export function Documents({ id }: { id?: string }) {
  const list = useItems("documents");
  const detail = useData<RecordData>(
    `documents/${encodeURIComponent(id ?? "")}`,
    Boolean(id),
  );
  const search = useSearchParams();
  if (id) {
    if (!detail.data)
      return (
        <State
          pending={detail.isPending}
          error={detail.error}
          retry={() => void detail.refetch()}
        />
      );
    const doc = detail.data;
    const text = str(doc.text);
    const start = Math.max(0, Number(search.get("start") ?? 0));
    const end = Math.min(text.length, Number(search.get("end") ?? 0));
    return (
      <>
        <Header title={str(doc.title ?? doc.filename)}>
          <Link className="draw-underline" href="/documents">
            All documents
          </Link>
        </Header>
        <div className="actions caption">
          <Status value={doc.status} />
          <span>{str(doc.origin)}</span>
          <span>{time(doc.created_at)}</span>
        </div>
        <div className="two-columns">
          <Section title="Source">
            <article className="source-text">
              {end > start ? (
                <>
                  {text.slice(0, start)}
                  <mark id="source-highlight">{text.slice(start, end)}</mark>
                  {text.slice(end)}
                </>
              ) : (
                text
              )}
            </article>
          </Section>
          <div>
            <Section title="Mentions">
              <Records
                items={rows(doc.mentions).map((row, index) => ({
                  ...row,
                  id:
                    row.id ??
                    `${row.entity_id}-${object(row.span).start}-${index}`,
                }))}
                columns={[
                  {
                    key: "entity_id",
                    title: "Entity",
                    render: (row) => (
                      <Link
                        className="draw-underline"
                        href={`/entities/${encodeURIComponent(str(row.entity_id ?? row.entity))}`}
                      >
                        {str(row.name ?? row.entity_id ?? row.entity)}
                      </Link>
                    ),
                  },
                  { key: "confidence", title: "Confidence" },
                ]}
              />
            </Section>
            <Section title="Extracted facts">
              <Json value={doc.facts ?? []} />
            </Section>
            <Section title="Chunks">
              <Json value={doc.chunks ?? []} />
            </Section>
          </div>
        </div>
      </>
    );
  }
  return (
    <>
      <Header title="Documents">
        <Button asChild>
          <Link href="/ingestion">
            <FileText size={16} />
            Add document
          </Link>
        </Button>
      </Header>
      <State
        pending={list.isPending}
        error={list.error}
        retry={() => void list.refetch()}
      />
      {list.data && (
        <Records
          items={list.data.items}
          columns={[
            {
              key: "title",
              title: "Source",
              render: (row) => (
                <Link
                  className="draw-underline font-medium"
                  href={`/documents/${encodeURIComponent(row.id)}`}
                >
                  {str(row.title ?? row.filename)}
                </Link>
              ),
            },
            { key: "origin", title: "Origin" },
            {
              key: "status",
              title: "Status",
              render: (row) => <Status value={row.status} />,
            },
            {
              key: "created_at",
              title: "Added",
              render: (row) => time(row.created_at),
            },
          ]}
        />
      )}
    </>
  );
}
export function Search() {
  const [query, setQuery] = useState("");
  const [type, setType] = useState("");
  const [expand, setExpand] = useState(true);
  const action = useAction<{
    results: RecordData[];
    elapsed_ms: number;
    embedding_provider?: string;
  }>();
  const types = useItems("entity-types");
  return (
    <>
      <Header title="Search" />
      <form
        onSubmit={(e) => {
          e.preventDefault();
          action.mutate({
            path: "search",
            body: {
              query,
              ...(type ? { types: [type] } : {}),
              expand,
              limit: 20,
            },
          });
        }}
      >
        <div className="filter-row">
          <FormInput
            label="Search knowledge"
            placeholder="Who handles repairs at Northfield House?"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            required
          />
          <FormSelect
            label="Type"
            value={type}
            onChange={(e) => setType(e.target.value)}
            options={[
              { value: "", label: "All types" },
              ...(types.data?.items ?? []).map((row) => ({
                value: row.id,
                label: str(row.name),
              })),
            ]}
          />
          <div className="actions">
            <Button loading={action.isPending}>
              <SearchIcon size={16} />
              Search
            </Button>
          </div>
        </div>
        <label className="caption flex gap-2 items-center">
          <input
            type="checkbox"
            checked={expand}
            onChange={(e) => setExpand(e.target.checked)}
          />
          Include connected entities
        </label>
      </form>
      <State error={action.error} />
      {action.data ? (
        <Section title="Results">
          <p className="caption mb-4">
            {action.data.elapsed_ms} ms · Hybrid search ·{" "}
            {action.data.embedding_provider ?? "Embedding provider unavailable"}
          </p>
          {!action.data.results.length && (
            <EmptyState message="No matches found." />
          )}
          {action.data.results.map((result) => (
            <div className="result" key={result.id}>
              <div className="actions justify-between">
                <h3>
                  <Link
                    className="draw-underline"
                    href={`/entities/${encodeURIComponent(result.id)}`}
                  >
                    {str(result.name)}
                  </Link>
                </h3>
                <span className="caption tabular-nums">
                  {Number(result.score).toFixed(3)} · {str(result.type)}
                </span>
              </div>
              <p>{str(result.description)}</p>
              <div className="actions caption">
                {rows(result.citations).map((citation, i) => (
                  <Link
                    className="draw-underline"
                    key={citation.id ?? i}
                    href={`/documents/${encodeURIComponent(str(citation.document_id ?? citation.document))}`}
                  >
                    {str(
                      citation.filename ??
                        citation.document_id ??
                        citation.document,
                    )}
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </Section>
      ) : (
        <EmptyState message="Search across entities and source evidence." />
      )}
    </>
  );
}
export function Ingestion() {
  const [contentBase64, setContentBase64] = useState("");
  const [sourceType, setSourceType] = useState("");
  const [reading, setReading] = useState(false);
  const [filename, setFilename] = useState("");
  const [text, setText] = useState("");
  const [origin, setOrigin] = useState("manual");
  const [mime, setMime] = useState("text/plain");
  const [error, setError] = useState<Error | null>(null);
  const action = useAction();
  const jobs = useItems("ingest/jobs");
  return (
    <>
      <Header title="Ingestion">
        <Button
          variant="ghost"
          loading={action.isPending}
          onClick={() => action.mutate({ path: "ingest/sync", body: {} })}
        >
          Sync local sources
        </Button>
      </Header>
      <div className="two-columns">
        <Section title="Add a source">
          <form
            className="form"
            onSubmit={(e) => {
              e.preventDefault();
              action.mutate(
                {
                  path: "ingest/upload",
                  body: {
                    filename,
                    ...(contentBase64
                      ? { content_base64: contentBase64 }
                      : { text }),
                    origin,
                    mime,
                    ...(sourceType ? { source_type: sourceType } : {}),
                  },
                },
                {
                  onSuccess: () => {
                    setText("");
                    setFilename("");
                    setContentBase64("");
                  },
                },
              );
            }}
          >
            <div>
              <label className="caption block mb-2" htmlFor="upload">
                Document, image, bank statement, invoice or receipt
              </label>
              <input
                id="upload"
                disabled={reading}
                type="file"
                accept=".txt,.md,.json,.csv,.ofx,.qfx,.pdf,.jpg,.jpeg,.png,.gif,.webp,text/*,application/json,application/pdf,image/jpeg,image/png,image/gif,image/webp"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  setError(null);
                  const mime = sourceMime(file.name, file.type);
                  const binary = mime === "application/pdf" || mime.startsWith("image/");
                  if (file.size > (binary ? 5_000_000 : 2_000_000)) {
                    setError(
                      new Error(
                        binary
                          ? "Choose a PDF or image under 5 MB"
                          : "Choose a text file under 2 MB",
                      ),
                    );
                    return;
                  }
                  setReading(true);
                  try {
                    setFilename(file.name);
                    setMime(mime);
                    if (binary) {
                      setContentBase64(
                        bytesBase64(new Uint8Array(await file.arrayBuffer())),
                      );
                      setText("");
                    } else {
                      setText(await file.text());
                      setContentBase64("");
                    }
                  } catch {
                    setError(
                      new Error("Cannot read this file. Choose it again."),
                    );
                  } finally {
                    setReading(false);
                  }
                }}
              />
            </div>
            <FormInput
              label="Filename"
              required
              value={filename}
              onChange={(e) => setFilename(e.target.value)}
            />
            <FormSelect
              label="Origin"
              value={origin}
              onChange={(e) => setOrigin(e.target.value)}
              options={["manual", "email", "call", "export"].map((value) => ({
                value,
                label: value,
              }))}
            />
            <FormSelect
              label="Source type"
              value={sourceType}
              onChange={(e) => setSourceType(e.target.value)}
              options={[
                { value: "", label: "General document" },
                ...[
                  "bank_statement",
                  "invoice",
                  "receipt",
                  "remittance",
                  "tenancy_agreement",
                  "rent_schedule",
                ].map((value) => ({
                  value,
                  label: value.replaceAll("_", " "),
                })),
              ]}
            />
            {contentBase64 ? (
              <div className="actions">
                <p className="caption">PDF ready for extraction: {filename}</p>
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setContentBase64("");
                    setMime("text/plain");
                    setFilename("");
                  }}
                >
                  Remove file
                </Button>
              </div>
            ) : (
              <FormTextarea
                label="Source text"
                rows={8}
                value={text}
                required
                onChange={(e) => setText(e.target.value)}
              />
            )}
            <State error={error ?? action.error} />
            <Button
              loading={action.isPending || reading}
              disabled={
                reading || (!text.trim() && !contentBase64) || Boolean(error)
              }
            >
              <Upload size={16} />
              Ingest source
            </Button>
            {action.data && (
              <Status value={action.data.status ?? "completed"} />
            )}
            <p className="caption">
              Local extraction preserves source spans. AI extraction requires a
              configured provider.
            </p>
          </form>
        </Section>
        <Section title="Jobs">
          <State
            pending={jobs.isPending}
            error={jobs.error}
            retry={() => void jobs.refetch()}
          />
          {jobs.data && (
            <Records
              items={jobs.data.items}
              columns={[
                {
                  key: "filename",
                  title: "Source",
                  render: (row) =>
                    row.document_id ? (
                      <Link
                        className="draw-underline"
                        href={`/documents/${encodeURIComponent(str(row.document_id))}`}
                      >
                        {str(row.filename ?? row.document_id)}
                      </Link>
                    ) : (
                      str(row.filename ?? row.id)
                    ),
                },
                {
                  key: "status",
                  title: "Status",
                  render: (row) => <Status value={row.status} />,
                },
                {
                  key: "created_at",
                  title: "When",
                  render: (row) => time(row.created_at),
                },
              ]}
            />
          )}
        </Section>
      </div>
    </>
  );
}
