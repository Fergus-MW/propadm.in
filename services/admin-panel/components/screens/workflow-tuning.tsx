"use client";

import { useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, time } from "@/lib/api";
import { exampleTestCase, parseTestCases, type PrivateTestCase } from "@/lib/workflow-tuning";
import { Header, Section, State, Status } from "../common";
import { Button } from "../ui/Button";
import { FormInput, FormTextarea } from "../ui/Input";
import { StatusText } from "../library/StatusText";
import { EmptyState } from "../library/EmptyState";
import { StatGrid } from "../library/StatGrid";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../ui/Table";

type Result = {
  id: string; case_id: string; after_step: number; answer: string; reasoning: string;
  expected: string; score?: number; passed?: boolean; explanation: string;
  differences: string[]; skill_versions: Record<string, number>; created_at: string;
};
type Job = {
  id: string; kind: string; name: string; status: string; phase: string; streak: number;
  target: number; trials: number; max_trials: number; error?: string; after_step?: number;
  case_id?: string; created_at: string; history: Result[];
  changes: { skill_id: string; version: number; summary: string; old_text: string;
    new_text: string; created_at: string }[];
  rejected: { validation: { phase: string; explanation: string }[] }[];
};
type Summary = Pick<Job, "id" | "name" | "kind" | "status" | "phase" | "created_at" | "streak" | "target" | "trials" | "max_trials">;
type Overview = { cases: number; transitions: number; items: Summary[] };
const base = "/workflow-tuning";

function ResultDetail({ result }: { result: Result }) {
  return <div className="space-y-4 py-4">
    <div><h3>Answer</h3><p className="whitespace-pre-wrap break-words">{result.answer}</p></div>
    <div><h3>Reasoning</h3><p className="whitespace-pre-wrap break-words">{result.reasoning}</p></div>
    {result.expected && <div><h3>Recorded next step</h3><p className="whitespace-pre-wrap break-words">{result.expected}</p></div>}
    <p className="break-words">{result.explanation}</p>
    {result.differences.length > 0 && <ul className="list-disc pl-5">{result.differences.map((text, i) => <li key={i}>{text}</li>)}</ul>}
    <details><summary className="cursor-pointer draw-underline">Skill versions used</summary>
      <ul className="space-y-1 pt-2">{Object.entries(result.skill_versions).map(([key, version]) =>
        <li key={key}><code>{key}</code> · version {version}</li>)}</ul>
    </details>
  </div>;
}

export function WorkflowTuning({ id }: { id?: string }) {
  const client = useQueryClient();
  const [maxTrials, setMaxTrials] = useState("200");
  const [cases, setCases] = useState<PrivateTestCase[]>([]);
  const [uploadError, setUploadError] = useState<Error | null>(null);
  const [submitted, setSubmitted] = useState(0);
  const [context, setContext] = useState("");
  const [history, setHistory] = useState("");
  const [expected, setExpected] = useState("");
  const overview = useQuery<Overview>({
    queryKey: [base], queryFn: () => api(base), retry: false,
    refetchInterval: (query) => query.state.data?.items.some((job) => job.status === "running") ? 3000 : 30000,
  });
  const selectedId = id ?? overview.data?.items[0]?.id;
  const detail = useQuery<Job>({
    queryKey: [base, selectedId], enabled: !!selectedId, retry: false,
    queryFn: () => api(`${base}/runs/${encodeURIComponent(selectedId!)}`),
    refetchInterval: (query) => query.state.data?.status === "running" ? 3000 : false,
  });
  const selected = detail.data;
  const active = overview.data?.items.find((job) => job.kind === "workflow_tuning" && job.status === "running");
  const refresh = () => client.invalidateQueries({ queryKey: [base] });
  const start = useMutation({
    mutationFn: () => api<Job>(`${base}/runs`, { max_trials: Number(maxTrials) }),
    onSuccess: refresh,
  });
  const stop = useMutation({
    mutationFn: (key: string) => api(`${base}/runs/${encodeURIComponent(key)}/stop`, {}),
    onSuccess: refresh,
  });
  const upload = useMutation({
    mutationFn: async (items: PrivateTestCase[]) => {
      setSubmitted(0);
      for (let i = 0; i < items.length; i++) {
        await api(`${base}/tests`, items[i]);
        setSubmitted(i + 1);
        setCases(items.slice(i + 1));
      }
    },
    onSettled: refresh,
    onSuccess: () => { setCases([]); setHistory(""); setExpected(""); setContext(""); },
  });
  async function load(file?: File) {
    if (!file) return;
    try {
      if (file.size > 3_500_000) throw new Error("Case file must be smaller than 3.5 MB.");
      setCases(parseTestCases(await file.text()));
      setUploadError(null);
      setSubmitted(0);
    } catch (reason) { setUploadError(reason instanceof Error ? reason : new Error("Cannot read cases.")); }
  }
  const steps = history.split(/^---\s*$/m).map((step) => step.trim()).filter(Boolean);
  const trialsError = !Number.isInteger(Number(maxTrials)) || Number(maxTrials) < 10 || Number(maxTrials) > 10000
    ? "Enter a whole number from 10 to 10,000. At least 10 trials are needed for 10 consecutive passes."
    : undefined;
  return <>
    <Header title="Performance tuning" />
    <State pending={overview.isPending} error={overview.error} retry={() => void overview.refetch()} />
    <Section title="Workflow hill climbing">
      <p className="mb-4">Hide one case and all its sources, predict the next action from a random history prefix,
        and automatically test small skill corrections until 10 different samples pass in a row.</p>
      <StatGrid stats={[
        { label: "Corpus cases", value: overview.data?.cases ?? "—" },
        { label: "Eligible next steps", value: overview.data?.transitions ?? "—" },
        { label: "Consecutive passes", value: `${active?.streak ?? (selected?.kind === "workflow_tuning" ? selected.streak : 0)} / 10` },
      ]} />
      <div className="form-row mt-4 items-end">
        <FormInput label="Maximum trials (minimum 10)" type="number" min={10} max={10000} value={maxTrials} error={trialsError}
          disabled={!!active} onChange={(event) => setMaxTrials(event.target.value)} />
        <div className="actions">
          {active ? <Button variant="ghost" loading={stop.isPending} onClick={() => stop.mutate(active.id)}>Stop tuning</Button> :
            <Button loading={start.isPending} disabled={!overview.data || overview.data.transitions < 10 ||
              !!trialsError}
              onClick={() => start.mutate()}>Start tuning</Button>}
        </div>
      </div>
      <p className="caption mt-3">The agent can read the graph and skills. Email, calls and operational writes are unavailable.
        Uploaded test cases stay separate. Corrections publish without human approval after validation.</p>
      <State error={start.error ?? stop.error} />
    </Section>
    <Section title="Test an unseen case">
      <p className="mb-4">Supply ordered steps and ask for the next action. These cases stay outside the knowledge graph
        and never change skills. Add a reference step if you want a score.</p>
      <div className="form">
        <FormInput label="Load JSON cases" type="file" accept=".json,application/json" disabled={upload.isPending}
          onChange={(event) => { void load(event.target.files?.[0]); event.target.value = ""; }} />
        <a className="draw-underline w-fit" download="next-step-test.json"
          href={`data:application/json;charset=utf-8,${encodeURIComponent(JSON.stringify(exampleTestCase, null, 2))}`}>Download a 9-step example</a>
        {cases.length > 0 ? <>
          <p>{cases.length} cases ready: {cases.map((item) => `${item.name} (${item.steps.length} steps)`).join(", ")}</p>
          <div className="actions"><Button loading={upload.isPending}
            onClick={() => upload.mutate(cases)}>Test loaded cases</Button>
            <Button variant="ghost" disabled={upload.isPending} onClick={() => setCases([])}>Clear</Button></div>
        </> : <form className="form" onSubmit={(event) => {
          event.preventDefault(); upload.mutate([{ name: "Manual next-step test", initial_context: context, steps, expected }]);
        }}>
          <FormTextarea label="Initial context" value={context} maxLength={20000} onChange={(event) => setContext(event.target.value)} />
          <FormTextarea label="History steps — separate each step with a line containing ---" rows={8} value={history}
            required onChange={(event) => setHistory(event.target.value)} />
          <FormTextarea label="Reference next step (optional, hidden from the agent)" value={expected} maxLength={30000}
            onChange={(event) => setExpected(event.target.value)} />
          <div className="actions"><Button type="submit" loading={upload.isPending} disabled={!steps.length}>Predict next step</Button>
            <span>{steps.length} steps supplied</span></div>
        </form>}
        <State error={uploadError ?? upload.error} />
        {upload.error && submitted > 0 && <p>{submitted} cases submitted before the error.</p>}
      </div>
    </Section>
    <Section title="Runs">
      {!overview.data?.items.length ? <EmptyState message="No tuning runs yet." /> :
        <Table><TableHeader><TableRow><TableHead>Run</TableHead><TableHead>Status</TableHead>
          <TableHead>Progress</TableHead><TableHead>Started</TableHead></TableRow></TableHeader><TableBody>
          {overview.data.items.map((job) => <TableRow key={job.id}>
            <TableCell><Link href={`/tuning/${encodeURIComponent(job.id)}`} className="draw-underline">{job.name}</Link></TableCell>
            <TableCell><Status value={job.status} /></TableCell>
            <TableCell className="tabular-nums">{job.kind === "workflow_tuning" ? `${job.streak} / 10 · ${job.trials} trials` : `${job.trials} test`}</TableCell>
            <TableCell>{time(job.created_at)}</TableCell>
          </TableRow>)}</TableBody></Table>}
    </Section>
    <State pending={!!selectedId && detail.isPending} error={detail.error} retry={() => void detail.refetch()} />
    {selected && <Section title={selected.name}>
      <div className="actions mb-4"><Status value={selected.status} />
        {selected.status === "running" && <><span>{selected.phase.replaceAll("_", " ")}
          {selected.after_step ? ` · ${selected.after_step} history steps` : ""}</span>
          {selected.kind === "workflow_test" && <Button variant="ghost" onClick={() => stop.mutate(selected.id)}>Stop test</Button>}</>}
      </div>
      {selected.error && <p role="alert"><StatusText variant="error">{selected.error}</StatusText></p>}
      {selected.status === "exhausted" && <p>Reached {selected.max_trials} trials before achieving 10 consecutive passes.</p>}
      {!selected.history.length && <EmptyState message="Waiting for the first prediction." />}
      {[...selected.history].reverse().map((result) => <details key={result.id} className="border-b border-line py-3">
        <summary className="cursor-pointer flex flex-wrap items-center gap-3"><span className="font-mono break-all">{result.case_id}</span>
          <span>After step {result.after_step}</span>
          <StatusText variant={result.passed === undefined ? "info" : result.passed ? "success" : "error"}>
            {result.passed === undefined ? "Predicted" : result.passed ? "Passed" : "Missed"}</StatusText>
          {result.score !== undefined && <span className="tabular-nums">{result.score} / 100</span>}
        </summary><ResultDetail result={result} /></details>)}
      {selected.changes.length > 0 && <div className="mt-6 space-y-3"><h3>Published skill updates</h3>
        {selected.changes.map((change) => <details key={`${change.skill_id}-${change.version}`}>
          <summary className="cursor-pointer draw-underline">{change.skill_id} · version {change.version}</summary>
          <p className="py-2">{change.summary}</p>
          {change.old_text && <div><h3>Replaced</h3><pre className="code whitespace-pre-wrap break-words">{change.old_text}</pre></div>}
          <div><h3>New text</h3><pre className="code whitespace-pre-wrap break-words">{change.new_text}</pre></div>
        </details>)}</div>}
      {selected.rejected.length > 0 && <details className="mt-4"><summary className="cursor-pointer draw-underline">
        {selected.rejected.length} candidate edits rejected by tests</summary>
        {selected.rejected.map((item, i) => <p className="py-2" key={i}>{item.validation.filter((r) => r.explanation)
          .map((r) => `${r.phase}: ${r.explanation}`).join(" · ")}</p>)}
      </details>}
    </Section>}
  </>;
}
