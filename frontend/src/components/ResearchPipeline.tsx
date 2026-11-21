import { useMemo, useState } from "react";
import { fetchWithProgress } from "../utils/fetchWithProgress";
import ProgressIndicator from "./ProgressIndicator";
import ProductCandidateRow from "./ProductCandidateRow";
import NumberInput from "./NumberInput";
import { btnPill } from "../styles/buttonPill";
import { rankCandidates } from "../utils/ranking";
import type { CopySellerResult, ProductCandidate } from "../types/research";

/** Mirrors SELLER_SETUP_CALLS in backend/copy_seller.py. */
const SELLER_SETUP_CALLS = 5;

/** Mirrors estimate_api_call_cost in backend/copy_seller.py: N×(1+K) + setup. */
function estimateApiCallCost(topN: number, k: number): number {
  return topN * (1 + k) + SELLER_SETUP_CALLS;
}

const STEP_BUDGET = "Checking API budget";
const STEP_COLLECT = "Collecting seller listings";
const STEP_DETAILS = "Fetching listing details";
const STEP_METRICS = "Computing metrics";
const PIPELINE_STEPS = [STEP_BUDGET, STEP_COLLECT, STEP_DETAILS, STEP_METRICS];

const sliderClass = "w-full accent-primary";
const inputClass =
  "rounded-lg border-2 border-border-default bg-surface-panel px-4 py-2 text-text-primary transition-colors focus:border-primary focus:outline-none disabled:bg-surface-hover";

interface ResearchPipelineProps {
  addToast?: (type: string, message: string) => void;
}

interface MetricsProgress {
  current: number;
  total: number;
  title: string;
}

export default function ResearchPipeline({ addToast }: ResearchPipelineProps) {
  const [seller, setSeller] = useState("");
  const [topN, setTopN] = useState(25);
  const [k, setK] = useState(20);
  const [minSold, setMinSold] = useState(1);
  const [weightDemand, setWeightDemand] = useState(1);
  const [weightCompetition, setWeightCompetition] = useState(1);
  const [weightVelocity, setWeightVelocity] = useState(1);

  const [isRunning, setIsRunning] = useState(false);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [completedSteps, setCompletedSteps] = useState<string[]>([]);
  const [metricsProgress, setMetricsProgress] = useState<MetricsProgress | null>(null);
  const [candidates, setCandidates] = useState<ProductCandidate[]>([]);
  const [runSummary, setRunSummary] = useState<CopySellerResult | null>(null);

  const estimatedCost = useMemo(() => estimateApiCallCost(topN, k), [topN, k]);

  // Live re-ranking: recomputed from cached metrics whenever a weight slider
  // moves — no pipeline re-run.
  const rankedCandidates = useMemo(
    () =>
      rankCandidates(candidates, {
        demand: weightDemand,
        competition: weightCompetition,
        velocity: weightVelocity,
      }),
    [candidates, weightDemand, weightCompetition, weightVelocity],
  );

  const handleRun = async (): Promise<void> => {
    const trimmedSeller = seller.trim();
    if (!trimmedSeller) {
      addToast?.("error", "Please enter a seller username");
      return;
    }
    setIsRunning(true);
    setCurrentStep(null);
    setCompletedSteps([]);
    setMetricsProgress(null);
    setCandidates([]);
    setRunSummary(null);

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
          }),
        },
        (event) => {
          const step = typeof event.step === "string" ? event.step : "";
          const status = event.status;
          // The backend streams "Computing metrics (i/N)" as one step per
          // listing; ProgressIndicator shows it as a single named step.
          const baseStep = step.startsWith(STEP_METRICS) ? STEP_METRICS : step;

          if (step.startsWith(STEP_METRICS)) {
            const match = step.match(/\((\d+)\/(\d+)\)/);
            if (match) {
              setMetricsProgress({
                current: Number(match[1]),
                total: Number(match[2]),
                title: typeof event.title === "string" ? event.title : "",
              });
            }
          }

          if (status === "in_progress") {
            setCurrentStep(baseStep);
          } else if (status === "completed" && baseStep) {
            setCompletedSteps((prev) =>
              prev.includes(baseStep) ? prev : [...prev, baseStep],
            );
            setCurrentStep((prev) => (prev === baseStep ? null : prev));
          }
        },
      )) as CopySellerResult;

      setRunSummary(data);
      setCandidates(
        Array.isArray(data?.product_candidates) ? data.product_candidates : [],
      );
      setCompletedSteps(PIPELINE_STEPS);
      setCurrentStep(null);
      addToast?.(
        "success",
        `Copy Seller run complete: ${data?.product_candidates?.length ?? 0} Product Candidates`,
      );
    } catch (err) {
      addToast?.("error", (err as Error).message || "Copy Seller run failed");
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
          Find a seller's best products and score them by demand metrics.
          Weight sliders re-rank instantly from cached metrics — no re-run.
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
        </div>

        {/* Weight sliders — re-rank live from cached metrics */}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">
              Demand Coefficient weight ({weightDemand.toFixed(2)})
            </span>
            <input
              type="range"
              aria-label="Demand Coefficient weight"
              min={0}
              max={2}
              step={0.05}
              value={weightDemand}
              onChange={(e) => setWeightDemand(Number(e.target.value))}
              disabled={isRunning}
              className={sliderClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">
              Competition Count weight ({weightCompetition.toFixed(2)})
            </span>
            <input
              type="range"
              aria-label="Competition Count weight"
              min={0}
              max={2}
              step={0.05}
              value={weightCompetition}
              onChange={(e) => setWeightCompetition(Number(e.target.value))}
              disabled={isRunning}
              className={sliderClass}
            />
          </label>
          <label className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">
              Sold Velocity weight ({weightVelocity.toFixed(2)})
            </span>
            <input
              type="range"
              aria-label="Sold Velocity weight"
              min={0}
              max={2}
              step={0.05}
              value={weightVelocity}
              onChange={(e) => setWeightVelocity(Number(e.target.value))}
              disabled={isRunning}
              className={sliderClass}
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

      {/* Live progress */}
      {(isRunning || completedSteps.length > 0) && (
        <div>
          <ProgressIndicator
            steps={PIPELINE_STEPS}
            currentStep={currentStep}
            completedSteps={completedSteps}
          />
          {metricsProgress && isRunning && (
            <p className="-mt-3 text-sm text-text-muted">
              Metrics {metricsProgress.current} of {metricsProgress.total}
              {metricsProgress.title ? ` — ${metricsProgress.title}` : ""}
            </p>
          )}
        </div>
      )}

      {/* Results */}
      {candidates.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-sm text-text-muted">
            {candidates.length} Product Candidate
            {candidates.length !== 1 ? "s" : ""}
            {runSummary
              ? ` — ${runSummary.api_calls_made} API calls made, ${runSummary.api_calls_used_today} used today`
              : ""}
          </p>
          {rankedCandidates.map((ranked, index) => (
            <ProductCandidateRow
              key={`${ranked.candidate.listing_url}-${index}`}
              ranked={ranked}
            />
          ))}
        </div>
      )}
    </div>
  );
}
