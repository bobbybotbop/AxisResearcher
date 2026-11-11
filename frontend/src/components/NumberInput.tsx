import { useEffect, useState } from "react";

interface NumberInputProps {
  value: number;
  onCommit: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  /**
   * "change" commits every valid edit (for live-persisted settings);
   * "blur" commits only when the field loses focus.
   */
  commitOn?: "change" | "blur";
  /** Value committed when the field is left empty on blur. Defaults to min ?? 0. */
  emptyValue?: number;
  className?: string;
  ariaLabel?: string;
}

const clampNumber = (n: number, min?: number, max?: number): number => {
  if (min !== undefined && n < min) return min;
  if (max !== undefined && n > max) return max;
  return n;
};

/**
 * Number input that keeps a raw text draft while focused, so the user can
 * always delete every digit. Commits a parsed, clamped number on change
 * and/or blur; an empty field on blur commits `emptyValue` (default: min ?? 0).
 */
export default function NumberInput({
  value,
  onCommit,
  min,
  max,
  step,
  commitOn = "change",
  emptyValue,
  className,
  ariaLabel,
}: NumberInputProps) {
  const [draft, setDraft] = useState(String(value));
  const [focused, setFocused] = useState(false);

  // While unfocused, mirror the externally committed value. Also runs after
  // blur, so a commit the parent rejected snaps back to the previous value.
  useEffect(() => {
    if (!focused) setDraft(String(value));
  }, [value, focused]);

  const handleChange = (raw: string): void => {
    setDraft(raw);
    if (commitOn !== "change") return;
    const parsed = parseFloat(raw);
    if (!Number.isFinite(parsed)) return;
    const next = clampNumber(parsed, min, max);
    if (next !== value) onCommit(next);
  };

  const handleBlur = (): void => {
    setFocused(false);
    const parsed = parseFloat(draft);
    const fallback = emptyValue ?? min ?? 0;
    const next = Number.isFinite(parsed)
      ? clampNumber(parsed, min, max)
      : clampNumber(fallback, min, max);
    if (next !== value) onCommit(next);
  };

  return (
    <input
      type="number"
      min={min}
      max={max}
      step={step}
      value={draft}
      onFocus={() => setFocused(true)}
      onChange={(e) => handleChange(e.target.value)}
      onBlur={handleBlur}
      aria-label={ariaLabel}
      className={className}
    />
  );
}
