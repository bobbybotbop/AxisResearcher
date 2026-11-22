import { useSyncExternalStore } from "react";
import { statusStore, type Pipeline, type Task } from "../utils/statusStore";

interface PipelineTrackerProps {
  /** Id of the Pipeline in the Status Store to render. */
  pipelineId: number | null;
  /** Called when the user clicks Retry on a failed step. */
  onRetry?: () => void;
}

function StepIcon({ status }: { status: Task["status"] }) {
  switch (status) {
    case "success":
      return (
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-green-500 text-sm font-bold text-white">
          ✓
        </span>
      );
    case "running":
      return (
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-white">
          <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
        </span>
      );
    case "error":
      return (
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-danger text-sm font-bold text-white">
          ✕
        </span>
      );
    default:
      return (
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border-2 border-border-default bg-surface-hover text-sm font-bold text-text-muted">
          ○
        </span>
      );
  }
}

function StepRow({
  step,
  isActive,
  onRetry,
}: {
  step: Task;
  isActive: boolean;
  onRetry?: () => void;
}) {
  const statusColors: Record<Task["status"], string> = {
    success: "text-green-600",
    running: "font-semibold text-primary",
    error: "text-red-600",
    pending: "text-text-muted",
  };
  return (
    <div className={`flex flex-col gap-1 py-2 text-[0.95rem] ${statusColors[step.status]}`}>
      <div className="flex items-center gap-3">
        <StepIcon status={step.status} />
        <span className="flex-1">{step.name}</span>
        {isActive && step.progress && (
          <span className="text-sm font-semibold text-text-muted">
            {step.progress.current} of {step.progress.total}
          </span>
        )}
      </div>
      {step.status === "error" && (
        <div className="ml-9 flex flex-wrap items-center gap-2">
          <span className="text-sm text-red-600">{step.error}</span>
          {onRetry && (
            <button
              type="button"
              className="rounded-md border border-red-300 bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700 hover:bg-red-100"
              onClick={onRetry}
            >
              Retry
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * The single component that renders any Pipeline as a step tracker (ADR 0002):
 * per-step status icon, step name, and the active step's determinate progress
 * as text ("3 of 8"). A failed step turns red inline with the error message
 * and a Retry button. It is a pure status renderer — it reads a Pipeline from
 * the Status Store by id and renders waiting state only.
 */
function PipelineTracker({ pipelineId, onRetry }: PipelineTrackerProps) {
  const { pipelines } = useSyncExternalStore(
    statusStore.subscribe,
    statusStore.getSnapshot,
  );
  const pipeline: Pipeline | undefined =
    pipelineId == null ? undefined : pipelines.find((p) => p.id === pipelineId);

  if (!pipeline || pipeline.steps.length === 0) {
    return null;
  }

  const completedCount = pipeline.steps.filter((s) => s.status === "success").length;
  const totalCount = pipeline.steps.length;
  const progressPercent = totalCount > 0 ? (completedCount / totalCount) * 100 : 0;
  const barColor =
    pipeline.status === "error"
      ? "bg-gradient-to-r from-red-500 to-red-600"
      : "bg-gradient-to-r from-green-500 to-green-600";

  return (
    <div className="my-5 rounded-lg border border-border-default bg-surface-muted p-4">
      <div className="relative mb-4 h-6 w-full overflow-hidden rounded-xl bg-surface-hover">
        <div
          className={`h-full min-w-[2%] rounded-xl transition-[width] duration-300 ${barColor}`}
          style={{ width: `${progressPercent}%` }}
        />
        <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-sm font-semibold text-text-primary">
          {completedCount} of {totalCount} complete
        </div>
      </div>
      <div className="flex flex-col gap-2.5">
        {pipeline.steps.map((step, index) => (
          <StepRow
            key={step.id}
            step={step}
            isActive={index === pipeline.currentIndex && pipeline.status === "running"}
            onRetry={step.status === "error" ? onRetry : undefined}
          />
        ))}
      </div>
    </div>
  );
}

export default PipelineTracker;
