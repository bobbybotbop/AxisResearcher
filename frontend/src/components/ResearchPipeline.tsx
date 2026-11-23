import { useEffect, useMemo, useRef, useState } from "react";
import { fetchWithProgress } from "../utils/fetchWithProgress";
import PipelineTracker from "./PipelineTracker";
import ProductCandidateRow from "./ProductCandidateRow";
import NumberInput from "./NumberInput";
import { btnPill } from "../styles/buttonPill";
import { estimateApiCallCost } from "../constants/research";
import {
  dismissPipeline,
  startPipelineWithId,
  toast,
  type PipelineHandle,
} from "../utils/statusStore";
import type {
  CopySellerResult,
  PipelineRun,
  PipelineRunSummary,
  ProductCandidate,
  SortMetric,
} from "../types/research";

const STEP_BUDGET = "Checking API budget";
const STEP_COLLECT = "Collecting seller listings";
const STEP_DETAILS = "Fetching listing details";
const STEP_METRICS = "Computing metrics";
const PIPELINE_STEPS = [STEP_BUDGET, STEP_COLLECT, STEP_DETAILS, STEP_METRICS];

const SORT_OPTIONS: { value: SortMetric; label: string }[] = [
  { value: "demand", label: "Demand Coefficient" },
  { value: "competition", label: "Competition Count" },
  { value: "velocity", label: "Sold Velocity" },
];

const inputClass =
  "rounded-lg border-2 border-border-default bg-surface-panel px-4 py-2 text-text-primary transition-colors focus:border-primary focus:outline-none disabled:bg-surface-hover";

/** Today's date as a YYYY-MM-DD string (local calendar day). */
function todayIsoDate(): string {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

interface MetricsProgress {
  current: number;
  total: number;
  title: string;
}

export default function ResearchPipeline() {
  const [seller, setSeller] = useState("");
  const [topN, setTopN] = useState(25);
  const [k, setK] = useState(20);
  const [minSold, setMinSold] = useState(1);
  const [sortBy, setSortBy] = useState<SortMetric>("demand");
  // Date-Posted Range (ticket 12): collection-time filter on the seller's own
  // listings. Default today→today; picking a past start day sets end to today.
  const [datePostedStart, setDatePostedStart] = useState(todayIsoDate);
  const [datePostedEnd, setDatePostedEnd] = useState(todayIsoDate);

  const handleDatePostedStartChange = (value: string): void => {
    setDatePostedStart(value);
    // Picking a past start day sets the range from that day to today.
    if (value && value < datePostedEnd) {
      setDatePostedEnd(todayIsoDate());
    }
  };

  const [isRunning, setIsRunning] = useState(false);
  // Waiting state lives in the Status Store as a Pipeline (ADR 0002); only the
  // pipeline id is local. The metrics sub-progress title stays local as a
  // bespoke detail rendered below the PipelineTracker.
  const [pipelineId, setPipelineId] = useState<number | null>(null);
  const pipelineRef = useRef<PipelineHandle | null>(null);
  const [metricsProgress, setMetricsProgress] = useState<MetricsProgress | null>(null);
  const [candidates, setCandidates] = useState<ProductCandidate[]>([]);
  const [runSummary, setRunSummary] = useState<CopySellerResult | null>(null);

  const [pastRuns, setPastRuns] = useState<PipelineRunSummary[]>([]);
  const [loadedRunId, setLoadedRunId] = useState<string | null>(null);
  const [isLoadingRun, setIsLoadingRun] = useState(false);

  const estimatedCost = useMemo(() => estimateApiCallCost(topN, k), [topN, k]);

  const fetchPastRuns = async (): Promise<void> => {
    try {
      const res = await fetch("/api/research/copy-seller/runs");
      const body = (await res.json()) as {
        runs?: PipelineRunSummary[];
        error?: string | null;
      };
      if (res.ok && Array.isArray(body.runs)) {
        setPastRuns(body.runs);
      }
    } catch {
      // Past runs are a convenience; a fetch failure must not break the form.
    }
  };

  // Load past runs on mount so a previous Pipeline Run can be reloaded.
  useEffect(() => {
    void fetchPastRuns();
  }, []);

  const handleLoadRun = async (runId: string): Promise<void> => {
    setIsLoadingRun(true);
    try {
      const res = await fetch(`/api/research/copy-seller/runs/${runId}`);
      const body = (await res.json()) as { run?: PipelineRun; error?: string | null };
      if (!res.ok || !body.run) {
        toast.error(body.error || "Failed to load run");
        return;
      }
      const run = body.run;
      const loadedCandidates = Array.isArray(run.product_candidates)
        ? run.product_candidates
        : [];
      // Feed the loaded run's cached candidates into live sorting — no
      // pipeline re-run. Legacy runs may carry a weights field; it is ignored.
      setCandidates(loadedCandidates);
      setSeller(run.seller);
      setRunSummary(null);
      setLoadedRunId(run.run_id);
      toast.success(`Loaded run from ${new Date(run.timestamp).toLocaleString()} — ${loadedCandidates.length} Product Candidates`,
      );
    } catch (err) {
      toast.error((err as Error).message || "Failed to load run");
    } finally {
      setIsLoadingRun(false);
    }
  };

  // Live sorting: order the cached candidates greatest-to-least by the chosen
  // metric — no pipeline re-run. A null Sold Velocity sorts last.
  const sortedCandidates = useMemo(() => {
    const metricValue = (c: ProductCandidate): number => {
      switch (sortBy) {
        case "demand":
          return c.demand_coefficient;
        case "competition":
          return c.competition_count;
        case "velocity":
          return c.sold_velocity ?? Number.NEGATIVE_INFINITY;
      }
    };
    return [...candidates].sort((a, b) => metricValue(b) - metricValue(a));
  }, [candidates, sortBy]);

  const handleRun = async (): Promise<void> => {
    const trimmedSeller = seller.trim();
    if (!trimmedSeller) {
      toast.error("Please enter a seller username");
      return;
    }
    setIsRunning(true);
    setMetricsProgress(null);
    setCandidates([]);
    setRunSummary(null);
    setLoadedRunId(null);
    if (pipelineId != null) dismissPipeline(pipelineId);
    const { id: newPipelineId, handle: pipeline } = startPipelineWithId(
      "Copy Seller",
      PIPELINE_STEPS,
    );
    pipelineRef.current = pipeline;
    setPipelineId(newPipelineId);

    try {
      const data = (await fetchWithProgress(
        "/api/research/copy-seller",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            seller: trimmedSeller,
            top_n: topN,
            k,
            min_sold: minSold,
            date_posted_start: datePostedStart || null,
            date_posted_end: datePostedEnd || null,
          }),
        },
        (event) => {
          const step = typeof event.step === "string" ? event.step : "";
          const status = event.status;
          // The backend streams "Computing metrics (i/N)" as one step per
          // listing; the Pipeline shows it as a single named step whose
          // determinate progress is the (i/N) count.
          const baseStep = step.startsWith(STEP_METRICS) ? STEP_METRICS : step;

          if (step.startsWith(STEP_METRICS)) {
            const match = step.match(/\((\d+)\/(\d+)\)/);
            if (match) {
              const current = Number(match[1]);
              const total = Number(match[2]);
              setMetricsProgress({
                current,
                total,
                title: typeof event.title === "string" ? event.title : "",
              });
              pipeline.progress(current, total);
            }
          }

          // Metrics streams one completed event per listing — those only carry
          // determinate progress; the step itself completes when the run's
          // result arrives (pipeline.succeed below).
          if (status === "completed" && baseStep && baseStep !== STEP_METRICS) {
            // Steps may complete while the pipeline rests on an earlier step —
            // advancePast marks everything up to it done.
            pipeline.advancePast(baseStep);
          }
        },
      )) as CopySellerResult;

      setRunSummary(data);
      setCandidates(
        Array.isArray(data?.product_candidates) ? data.product_candidates : [],
      );
      setLoadedRunId(data?.run_id ?? null);
      pipeline.succeed();
      toast.success(`Copy Seller run complete: ${data?.product_candidates?.length ?? 0} Product Candidates`,
      );
      // The run was persisted on the backend; refresh the past-runs list.
      void fetchPastRuns();
    } catch (err) {
      pipeline.fail((err as Error).message || "Copy Seller run failed");
      toast.error((err as Error).message || "Copy Seller run failed");
    } finally {
      setIsRunning(false);
      setMetricsProgress(null);
    }
  };

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h3 className="mb-1 text-lg font-semibold text-text-primary">
          Research Pipeline — Copy Seller
        </h3>
        <p className="text-sm text-text-muted">
          Find a seller's best products and sort them by demand metrics. The
          sort-by control re-orders instantly from cached metrics — no re-run.
        </p>
      </div>

      {/* Run form */}
      <div className="flex flex-col gap-4 rounded-xl border border-border-default bg-surface-panel p-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-primary">
              Seller username
            </span>
            <input
              type="text"
              aria-label="Seller username"
              value={seller}
              onChange={(e) => setSeller(e.target.value)}
              placeholder="e.g. worldofprints"
              disabled={isRunning}
              className={inputClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-primary">
              Top N listings
            </span>
            <NumberInput
              value={topN}
              onCommit={setTopN}
              min={1}
              max={200}
              ariaLabel="Top N listings"
              className={inputClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-primary">
              K (demand sold-sum)
            </span>
            <NumberInput
              value={k}
              onCommit={setK}
              min={1}
              max={200}
              ariaLabel="K for demand coefficient"
              className={inputClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-primary">
              Min sold threshold
            </span>
            <NumberInput
              value={minSold}
              onCommit={setMinSold}
              min={0}
              ariaLabel="Minimum sold threshold"
              className={inputClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-primary">
              Date posted from
            </span>
            <input
              type="date"
              aria-label="Date posted from"
              value={datePostedStart}
              max={todayIsoDate()}
              onChange={(e) => handleDatePostedStartChange(e.target.value)}
              disabled={isRunning}
              className={inputClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs font-semibold text-text-primary">
              Date posted to
            </span>
            <input
              type="date"
              aria-label="Date posted to"
              value={datePostedEnd}
              min={datePostedStart}
              max={todayIsoDate()}
              onChange={(e) => setDatePostedEnd(e.target.value)}
              disabled={isRunning}
              className={inputClass}
            />
          </label>
        </div>

        <div className="flex flex-wrap items-center gap-4">
          <button
            type="button"
            className={`w-fit ${btnPill}`}
            onClick={handleRun}
            disabled={isRunning}
          >
            {isRunning ? "Running..." : "Run Copy Seller"}
          </button>
          <span
            className="text-sm text-text-muted"
            title="Estimated eBay API calls: N×(1+K) + seller setup"
          >
            Estimated cost: ~{estimatedCost.toLocaleString()} API calls
          </span>
        </div>
      </div>

      {/* Past runs — reload one to re-sort its cached candidates live */}
      {pastRuns.length > 0 && (
        <div className="flex flex-col gap-2 rounded-xl border border-border-default bg-surface-panel p-4">
          <h4 className="text-sm font-semibold text-text-primary">
            Past Pipeline Runs
          </h4>
          <p className="text-xs text-text-muted">
            Reload a run to restore its cached metrics, then re-sort live — no
            re-run.
          </p>
          <ul className="flex flex-col divide-y divide-border-default">
            {pastRuns.map((run) => (
              <li key={run.run_id}>
                <button
                  type="button"
                  onClick={() => void handleLoadRun(run.run_id)}
                  disabled={isRunning || isLoadingRun}
                  className={`flex w-full flex-wrap items-center gap-x-3 gap-y-1 py-2 text-left text-sm transition-colors hover:text-primary ${
                    loadedRunId === run.run_id
                      ? "font-semibold text-primary"
                      : "text-text-primary"
                  }`}
                >
                  <span className="font-medium">{run.seller}</span>
                  <span className="text-text-muted">
                    {new Date(run.timestamp).toLocaleString()}
                  </span>
                  <span className="text-text-muted">
                    {run.candidate_count} candidate
                    {run.candidate_count !== 1 ? "s" : ""}
                  </span>
                  {loadedRunId === run.run_id && (
                    <span className="text-xs text-primary">(loaded)</span>
                  )}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Waiting state: the run's Pipeline from the Status Store (ADR 0002);
          the metrics sub-progress title stays as a bespoke detail below it. */}
      <div>
        <PipelineTracker pipelineId={pipelineId} onRetry={() => void handleRun()} />
        {metricsProgress && isRunning && (
          <p className="-mt-3 text-sm text-text-muted">
            Metrics {metricsProgress.current} of {metricsProgress.total}
            {metricsProgress.title ? ` — ${metricsProgress.title}` : ""}
          </p>
        )}
      </div>

      {/* Results */}
      {candidates.length > 0 && (
        <div className="flex flex-col gap-2">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
            <p className="text-sm text-text-muted">
              {candidates.length} Product Candidate
              {candidates.length !== 1 ? "s" : ""}
              {runSummary
                ? ` — ${runSummary.api_calls_made} API calls made, ${runSummary.api_calls_used_today} used today`
                : ""}
            </p>
            <label className="flex items-center gap-2 text-sm text-text-muted">
              Sort by
              <select
                aria-label="Sort by metric"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as SortMetric)}
                className={inputClass}
              >
                {SORT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {sortedCandidates.map((candidate, index) => (
            <ProductCandidateRow
              key={`${candidate.listing_url}-${index}`}
              candidate={candidate}
            />
          ))}
        </div>
      )}
    </div>
  );
}
