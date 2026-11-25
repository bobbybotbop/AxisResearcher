import type { ReactNode } from "react";
import { btnPillSm } from "../styles/buttonPill";

export type StepStatus = "pending" | "running" | "success" | "error";

export interface StepProgress {
  current: number;
  total: number;
}

/** The per-step waiting state every workflow holds in local state (ADR 0003). */
export interface StepState {
  status: StepStatus;
  statusText?: string;
  error?: string;
}

export interface StepCardProps {
  /** Step title, e.g. "Step 1 — Fetch eBay Photos". Carries the sequence. */
  title: string;
  status: StepStatus;
  /**
   * Single-line activity message ("Fetching photos…"), replaced as the step
   * reports updates — not a scrolling log.
   */
  statusText?: string;
  /** Determinate progress rendered in the header as "N of M". */
  progress?: StepProgress;
  /** Error message shown inline with the Retry button when status is "error". */
  error?: string;
  /** Retries the step; when omitted, errors render without a Retry button. */
  onRetry?: () => void;
  /** Greys out the card when the step's dependencies aren't met. */
  disabled?: boolean;
  children?: ReactNode;
}

function StepStateIcon({ status }: { status: StepStatus }) {
  if (status === "running") {
    return (
      <span
        className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-text-muted/40 border-t-primary"
        aria-hidden="true"
      />
    );
  }
  if (status === "success") {
    return (
      <span className="shrink-0 text-sm font-bold text-success/70" aria-hidden="true">
        ✓
      </span>
    );
  }
  if (status === "error") {
    return (
      <span className="shrink-0 text-sm font-bold text-danger" aria-hidden="true">
        ✕
      </span>
    );
  }
  return (
    <span
      className="h-4 w-4 shrink-0 rounded-full border-2 border-text-muted/30"
      aria-hidden="true"
    />
  );
}

/**
 * One step of a workflow owns its own waiting-state display (ADR 0003).
 * Fully controlled: the parent workflow holds each step's state in useState
 * and passes it down; step content reports up via callbacks. The header shows
 * the state icon (dimmed pending / spinner running / persistent subtle green
 * check success / red error) and optional determinate progress; the body shows
 * a single-line status text; on error the message + Retry render inline at the
 * card so a failure is visible without scrolling.
 */
function StepCard({
  title,
  status,
  statusText,
  progress,
  error,
  onRetry,
  disabled = false,
  children,
}: StepCardProps) {
  return (
    <div
      className={`flex flex-col gap-3 rounded-xl border border-border-default bg-surface-panel p-4${
        disabled ? " pointer-events-none opacity-50" : ""
      }`}
      aria-disabled={disabled || undefined}
    >
      <div className="flex items-center gap-2">
        <StepStateIcon status={status} />
        <p className="text-sm font-semibold text-text-primary">{title}</p>
        {progress && (
          <span className="ml-auto shrink-0 text-xs text-text-muted">
            {progress.current} of {progress.total}
          </span>
        )}
      </div>
      {statusText && (
        <p className="truncate text-xs text-text-muted" aria-live="polite">
          {statusText}
        </p>
      )}
      {status === "error" && error && (
        <div className="flex items-center gap-3" role="alert">
          <p className="min-w-0 flex-1 text-xs text-danger">{error}</p>
          {onRetry && (
            <button type="button" className={btnPillSm} onClick={onRetry}>
              Retry
            </button>
          )}
        </div>
      )}
      {children}
    </div>
  );
}

export default StepCard;
