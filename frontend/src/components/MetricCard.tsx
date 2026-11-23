import { useEffect, useState, type ReactNode } from "react";
import type { MetricInfo } from "../constants/metricInfo";
import type { MetricRange, SortMetric } from "../types/research";

const inputClass =
  "rounded-lg border-2 border-border-default bg-surface-panel px-4 py-2 text-text-primary transition-colors focus:border-primary focus:outline-none disabled:bg-surface-hover";

interface OptionalBoundInputProps {
  value: number | null;
  onCommit: (value: number | null) => void;
  ariaLabel: string;
  className?: string;
}

/**
 * Number input for an optional range bound. Empty field = null = "any" (that
 * side does not filter). Commits on every valid edit and on blur.
 */
function OptionalBoundInput({
  value,
  onCommit,
  ariaLabel,
  className,
}: OptionalBoundInputProps) {
  const [draft, setDraft] = useState(value === null ? "" : String(value));
  const [focused, setFocused] = useState(false);

  useEffect(() => {
    if (!focused) setDraft(value === null ? "" : String(value));
  }, [value, focused]);

  const commit = (raw: string): void => {
    const trimmed = raw.trim();
    if (trimmed === "") {
      if (value !== null) onCommit(null);
      return;
    }
    const parsed = parseFloat(trimmed);
    if (!Number.isFinite(parsed)) return;
    if (parsed !== value) onCommit(parsed);
  };

  return (
    <input
      type="number"
      value={draft}
      placeholder="any"
      onFocus={() => setFocused(true)}
      onChange={(e) => {
        setDraft(e.target.value);
        commit(e.target.value);
      }}
      onBlur={() => {
        setFocused(false);
        commit(draft);
      }}
      aria-label={ariaLabel}
      className={className}
    />
  );
}

interface MetricRangeInputsProps {
  label: string;
  range: MetricRange;
  onChange: (next: MetricRange) => void;
  disabled?: boolean;
}

function MetricRangeInputs({
  label,
  range,
  onChange,
  disabled,
}: MetricRangeInputsProps) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-xs font-semibold text-text-primary">{label}</span>
      <div className="flex items-center gap-2">
        <OptionalBoundInput
          value={range.min}
          onCommit={(min) => onChange({ ...range, min })}
          ariaLabel={`${label} minimum`}
          className={`${inputClass} w-24 px-2 py-1 text-sm`}
        />
        <span className="text-xs text-text-muted">to</span>
        <OptionalBoundInput
          value={range.max}
          onCommit={(max) => onChange({ ...range, max })}
          ariaLabel={`${label} maximum`}
          className={`${inputClass} w-24 px-2 py-1 text-sm`}
        />
      </div>
      {disabled && (
        <span className="text-xs text-text-muted">
          Not collected — the filter only applies when this metric is collected.
        </span>
      )}
    </div>
  );
}

interface MetricCardProps {
  metric: SortMetric;
  info: MetricInfo;
  range: MetricRange;
  onRangeChange: (next: MetricRange) => void;
  isRunning: boolean;
  /** Collection toggle (Demand score only). When set, the card shows it. */
  collected?: boolean;
  onCollectedChange?: (collected: boolean) => void;
  /** Extra controls belonging to this metric (e.g. "Listings to check for demand"). */
  children?: ReactNode;
}

/**
 * One self-contained card per metric: its plain-English label, a "?" tooltip
 * explaining exactly how the metric is calculated, its collection toggle
 * (Demand score only), and its acceptable-range inputs.
 */
export default function MetricCard({
  metric,
  info,
  range,
  onRangeChange,
  isRunning,
  collected,
  onCollectedChange,
  children,
}: MetricCardProps) {
  const hasToggle = onCollectedChange !== undefined;
  const isCollected = collected ?? true;

  return (
    <section
      aria-label={`${info.label} metric`}
      data-metric={metric}
      className="flex flex-col gap-3 rounded-xl border border-border-default bg-surface-panel p-4"
    >
      <div className="flex items-center gap-2">
        <h4 className="text-sm font-semibold text-text-primary">{info.label}</h4>
        <span
          role="img"
          tabIndex={0}
          aria-label={`How ${info.label} is calculated: ${info.calculation}`}
          title={`${info.calculation} ${info.direction}`}
          className="flex h-4 w-4 cursor-help items-center justify-center rounded-full border border-border-default text-[10px] font-semibold leading-none text-text-muted"
        >
          ?
        </span>
        {hasToggle && (
          <label className="ml-auto flex items-center gap-2">
            <input
              type="checkbox"
              aria-label={`Collect ${info.label}`}
              checked={isCollected}
              onChange={(e) => onCollectedChange(e.target.checked)}
              disabled={isRunning}
              className="h-4 w-4 accent-primary"
            />
            <span className="text-xs text-text-muted">
              {isCollected ? "Collected" : "Not collected"}
            </span>
          </label>
        )}
      </div>

      {children}

      <MetricRangeInputs
        label="Acceptable range"
        range={range}
        onChange={onRangeChange}
        disabled={!isCollected}
      />
    </section>
  );
}
