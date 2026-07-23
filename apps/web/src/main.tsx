import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import "./styles.css";

const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const queryClient = new QueryClient();

type Scenario = {
  id: string;
  description: string;
  expected_root_cause: string | null;
};

type MetricPoint = { timestamp: string; value: number };
type MetricSeries = { scenario_id: string; series: Record<string, MetricPoint[]> };

type Incident = {
  incident_id: string;
  scenario_id: string | null;
  metrics_snapshot: Record<string, number>;
  anomaly: { is_anomalous: boolean; severity: string; metric: string | null; score: number; rule_id: string | null } | null;
  hypothesis: {
    root_cause: string;
    confidence: number;
    evidence: string[];
    counter_evidence: string[];
    recommended_actions: string[];
  } | null;
  remediation: { github_url: string | null; status: string; title: string } | null;
  trace_notes: string[];
  llm_calls: number;
  status: string;
  error: string | null;
};

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `API request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

function MetricChart({ metric, points }: { metric: string; points: MetricPoint[] }) {
  const chartData = points.map((point) => ({ ...point, time: new Date(point.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) }));
  return (
    <article className="metric-card">
      <div className="metric-heading">
        <h3>{metric.replaceAll("_", " ")}</h3>
        <span>{points.at(-1)?.value.toFixed(3) ?? "—"}</span>
      </div>
      <div className="chart-wrap">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={chartData} margin={{ top: 4, right: 6, bottom: 0, left: -22 }}>
            <XAxis dataKey="time" hide />
            <YAxis hide domain={["auto", "auto"]} />
            <Tooltip labelStyle={{ color: "#142033" }} />
            <Line type="monotone" dataKey="value" stroke="#56d6be" strokeWidth={2} dot={false} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </article>
  );
}

function Dashboard() {
  const queryClientForView = useQueryClient();
  const [selectedScenario, setSelectedScenario] = useState("");
  const [incident, setIncident] = useState<Incident | null>(null);

  const scenarios = useQuery({ queryKey: ["scenarios"], queryFn: () => api<Scenario[]>("/scenarios") });
  useEffect(() => {
    if (!selectedScenario && scenarios.data?.[0]) setSelectedScenario(scenarios.data[0].id);
  }, [scenarios.data, selectedScenario]);

  const metrics = useQuery({
    queryKey: ["metrics", selectedScenario],
    queryFn: () => api<MetricSeries>(`/metrics/series?scenario_id=${encodeURIComponent(selectedScenario)}`),
    enabled: Boolean(selectedScenario),
  });

  const inject = useMutation({
    mutationFn: () => api(`/scenarios/${encodeURIComponent(selectedScenario)}/inject`, { method: "POST" }),
    onSuccess: () => queryClientForView.invalidateQueries({ queryKey: ["metrics", selectedScenario] }),
  });
  const run = useMutation({
    mutationFn: () => api<Incident>("/incidents/run", {
      method: "POST",
      body: JSON.stringify({ scenario_id: selectedScenario, use_fake_llm: true }),
    }),
    onSuccess: (result) => {
      setIncident(result);
      queryClientForView.invalidateQueries({ queryKey: ["metrics", selectedScenario] });
    },
  });

  const error = scenarios.error ?? metrics.error ?? inject.error ?? run.error;
  const allMetrics = metrics.data?.series ?? {};
  const preferredMetrics = ["error_rate", "latency_p95", "db_pool_util"];
  const metricNames = [...preferredMetrics.filter((name) => allMetrics[name]), ...Object.keys(allMetrics).filter((name) => !preferredMetrics.includes(name))].slice(0, 3);
  const draftPath = incident?.remediation?.github_url;
  const isExternalDraft = draftPath?.startsWith("http");

  return (
    <main className="app-shell">
      <header className="page-header">
        <div>
          <p className="eyebrow">IR-Copilot · operator console</p>
          <h1>Detect with stats. Diagnose with agents.</h1>
        </div>
        <span className="guardrail">Human review required</span>
      </header>

      <section className="control-bar" aria-label="Scenario controls">
        <label>
          Scenario
          <select value={selectedScenario} onChange={(event) => setSelectedScenario(event.target.value)} disabled={scenarios.isLoading}>
            {scenarios.data?.map((scenario) => <option value={scenario.id} key={scenario.id}>{scenario.id}</option>)}
          </select>
        </label>
        <button type="button" className="secondary" onClick={() => inject.mutate()} disabled={!selectedScenario || inject.isPending}>
          {inject.isPending ? "Injecting…" : "Inject"}
        </button>
        <button type="button" onClick={() => run.mutate()} disabled={!selectedScenario || run.isPending}>
          {run.isPending ? "Running…" : "Run incident"}
        </button>
        <span className="dev-badge">Offline fake LLM · dry-run GitHub</span>
      </section>

      {error instanceof Error && <p className="error-banner">{error.message}</p>}

      <section className="section-block" aria-labelledby="metrics-title">
        <div className="section-title"><h2 id="metrics-title">Metrics</h2><span>{metrics.isFetching ? "Refreshing…" : "Synthetic scenario data"}</span></div>
        <div className="metrics-grid">
          {metricNames.map((metric) => <MetricChart key={metric} metric={metric} points={allMetrics[metric]} />)}
          {!metricNames.length && <p className="empty-state">Select a scenario to load its metric series.</p>}
        </div>
      </section>

      <section className="results-grid">
        <article className="panel incident-panel">
          <div className="section-title">
            <h2>Incident result</h2>
            {incident && <span className={`status status-${incident.status}`}>{incident.status}</span>}
          </div>
          {!incident && <p className="empty-state">Inject a scenario, then run the fixed incident workflow.</p>}
          {incident && <>
            <dl className="result-facts">
              <div><dt>Severity</dt><dd>{incident.anomaly?.severity ?? "none"}</dd></div>
              <div><dt>LLM calls</dt><dd>{incident.llm_calls} / 3</dd></div>
              <div><dt>Cost</dt><dd>{incident.llm_calls === 0 ? "$0 (gated)" : "Unavailable in fake mode"}</dd></div>
            </dl>
            {incident.status === "skipped" && <p className="skipped-note">No high-severity anomaly was detected. The gate skipped all LLM calls.</p>}
            {incident.hypothesis && <div className="hypothesis">
              <p className="label">Root cause</p><h3>{incident.hypothesis.root_cause}</h3>
              <p>Confidence: {Math.round(incident.hypothesis.confidence * 100)}%</p>
              <p className="label">Evidence</p>
              <ul>{incident.hypothesis.evidence.map((item) => <li key={item}>{item}</li>)}</ul>
            </div>}
            {incident.error && <p className="error-banner">{incident.error}</p>}
          </>}
        </article>

        <article className="panel trace-panel">
          <div className="section-title"><h2>Trace timeline</h2><span>Auditable steps</span></div>
          <ol className="timeline">
            {(incident?.trace_notes ?? ["Awaiting an incident run."]).map((note, index) => <li key={`${index}-${note}`}>{note}</li>)}
          </ol>
        </article>
      </section>

      <section className="panel draft-card">
        <div>
          <p className="label">GitHub remediation</p>
          <h2>{incident?.remediation?.status === "dry_run" ? "Draft artifact created locally" : "Draft-only workflow"}</h2>
          <p>IR-Copilot never merges, deploys, or mutates infrastructure. A human must review every draft.</p>
        </div>
        {draftPath ? isExternalDraft ? <a className="draft-link" href={draftPath} target="_blank" rel="noreferrer">Open GitHub draft</a> : <code className="outbox-path">Dry-run outbox: {draftPath}</code> : <span className="outbox-path">No draft created yet</span>}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode><QueryClientProvider client={queryClient}><Dashboard /></QueryClientProvider></StrictMode>,
);
