/**
 * Thin indeterminate loading bar, pinned to the top of its container.
 * Used for table-style loads (Data Browser, Logs) per ADR 0002: tables get
 * a top loading bar instead of a spinner. The parent container must be
 * `relative` (or the bar positions against the nearest positioned ancestor).
 */
export default function LoadingBar({ active }: { active: boolean }) {
  if (!active) return null;
  return (
    <div
      role="progressbar"
      aria-label="Loading"
      className="pointer-events-none absolute inset-x-0 top-0 z-10 h-0.5 overflow-hidden bg-primary/15"
    >
      <div className="h-full w-1/3 rounded-full bg-primary animate-loading-bar" />
    </div>
  );
}
