import { useEffect, useRef, useState } from "react";
import { Search, Filter } from "@mynaui/icons-react";
import { RefreshCw } from "lucide-react";
import { btnPillSm } from "../styles/buttonPill";

export default function UploadListingsToolbar({
  searchQuery,
  onSearchChange,
  showIncompleteListings,
  onShowIncompleteListingsChange,
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
  onRefresh,
  isRefreshing,
  autoRestockEnabled,
  autoRestockQuantity,
  onAutoRestockEnabledChange,
  onAutoRestockQuantityChange,
  onManualRestock,
  isRestocking,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const rootRef = useRef(null);
  const [quantityDraft, setQuantityDraft] = useState(
    String(autoRestockQuantity ?? ""),
  );

  useEffect(() => {
    setQuantityDraft(String(autoRestockQuantity ?? ""));
  }, [autoRestockQuantity]);

  const filtersActive =
    showIncompleteListings ||
    Boolean(dateFrom?.trim()) ||
    Boolean(dateTo?.trim());

  useEffect(() => {
    if (!menuOpen) return;

    const onPointerDown = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setMenuOpen(false);
      }
    };
    const onKeyDown = (e) => {
      if (e.key === "Escape") setMenuOpen(false);
    };

    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [menuOpen]);

  const clearDates = () => {
    onDateFromChange("");
    onDateToChange("");
  };

  return (
    <div className="mb-5 mt-8 flex items-center gap-3">
      {/* Search bar + Refresh: connected group, fills available space */}
      <div className="flex h-10 min-w-0 flex-1 items-stretch overflow-hidden rounded-lg border border-border-default bg-surface-panel shadow-sm transition-colors focus-within:ring-1 focus-within:ring-border-default/40">
        <div className="flex flex-1 items-center gap-2 px-3">
          <Search size={20} className="shrink-0 text-text-muted" aria-hidden />
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search by title…"
            className="min-w-0 flex-1 border-0 bg-transparent text-sm text-text-primary outline-none placeholder:text-text-muted"
            aria-label="Search history by title"
          />
        </div>

        {onRefresh && (
          <>
            <span className="w-px bg-border-default" aria-hidden />
            <button
              type="button"
              aria-label="Refresh quantities"
              title="Refresh quantities"
              disabled={isRefreshing}
              onClick={onRefresh}
              className="flex w-10 shrink-0 items-center justify-center text-text-primary transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-border-default/40 disabled:opacity-50"
            >
              <RefreshCw
                size={18}
                aria-hidden
                className={isRefreshing ? "animate-spin" : ""}
              />
            </button>
          </>
        )}
      </div>

      {/* Filter button: separate from search bar so its dropdown isn't clipped by overflow-hidden */}
      <div className="relative shrink-0" ref={rootRef}>
        <button
          type="button"
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          aria-label="Open filters"
          onClick={() => setMenuOpen((o) => !o)}
          className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-border-default bg-surface-panel text-text-primary shadow-sm transition-colors hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-default/40"
        >
          <Filter size={20} aria-hidden />
          {filtersActive ? (
            <span
              className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-text-primary"
              aria-hidden
            />
          ) : null}
        </button>

        {menuOpen ? (
          <div
            role="menu"
            aria-label="Listing filters"
            className="absolute right-0 top-full z-30 mt-2 w-[min(calc(100vw-2rem),17rem)] origin-top-right rounded-xl border border-border-default bg-surface-panel py-3 shadow-[0_8px_30px_rgb(0,0,0,0.2)] ring-1 ring-border-default/40"
          >
              <div className="px-4 pb-2">
                <p className="text-[0.65rem] font-medium uppercase tracking-[0.12em] text-text-muted">
                  Visibility
                </p>
                <label className="mt-2 flex cursor-pointer items-center gap-3 text-sm text-text-primary">
                  <input
                    type="checkbox"
                    checked={showIncompleteListings}
                    onChange={(e) =>
                      onShowIncompleteListingsChange(e.target.checked)
                    }
                    className="h-3.5 w-3.5 rounded border-border-default text-text-primary focus:ring-border-default"
                  />
                  <span className="leading-snug">Show incomplete history</span>
                </label>
              </div>

              <div className="my-2 h-px bg-border-default" />

              <div className="px-4 pt-1">
                <div className="flex items-baseline justify-between gap-2">
                  <p className="text-[0.65rem] font-medium uppercase tracking-[0.12em] text-text-muted">
                    Created
                  </p>
                  {(dateFrom || dateTo) && (
                    <button
                      type="button"
                      onClick={clearDates}
                      className="text-xs font-medium text-text-muted underline-offset-2 hover:text-text-primary hover:underline"
                    >
                      Clear
                    </button>
                  )}
                </div>
                <div className="mt-3 grid grid-cols-1 gap-2.5">
                  <label className="block">
                    <span className="mb-1 block text-xs text-text-muted">
                      From
                    </span>
                    <input
                      type="date"
                      value={dateFrom}
                      onChange={(e) => onDateFromChange(e.target.value)}
                      className="w-full rounded-md border border-border-default bg-surface-muted px-2.5 py-1.5 text-sm text-text-primary transition-colors focus:border-border-default focus:bg-surface-panel focus:outline-none focus:ring-1 focus:ring-border-default/40"
                    />
                  </label>
                  <label className="block">
                    <span className="mb-1 block text-xs text-text-muted">
                      To
                    </span>
                    <input
                      type="date"
                      value={dateTo}
                      onChange={(e) => onDateToChange(e.target.value)}
                      className="w-full rounded-md border border-border-default bg-surface-muted px-2.5 py-1.5 text-sm text-text-primary transition-colors focus:border-border-default focus:bg-surface-panel focus:outline-none focus:ring-1 focus:ring-border-default/40"
                    />
                  </label>
                </div>
              </div>
            </div>
          ) : null}
        </div>

      {/* Auto-restock: far right */}
      {onAutoRestockEnabledChange && (
        <div className="flex h-10 shrink-0 items-center gap-3 rounded-lg border border-border-default bg-surface-panel px-3 shadow-sm">
          <label className="flex cursor-pointer items-center gap-2 text-sm text-text-primary">
            <input
              type="checkbox"
              checked={autoRestockEnabled}
              onChange={(e) => onAutoRestockEnabledChange(e.target.checked)}
              className="h-3.5 w-3.5 rounded border-border-default text-text-primary focus:ring-border-default"
            />
            <span className="whitespace-nowrap">Auto-restock</span>
          </label>
          <input
            type="number"
            min="0"
            value={quantityDraft}
            onChange={(e) => setQuantityDraft(e.target.value)}
            onBlur={() => {
              const n = parseInt(quantityDraft, 10);
              if (Number.isFinite(n) && n >= 0) {
                onAutoRestockQuantityChange(n);
              } else {
                setQuantityDraft(String(autoRestockQuantity ?? ""));
              }
            }}
            aria-label="Auto-restock target quantity"
            className="w-14 rounded border border-border-default bg-surface-muted px-2 py-1 text-sm text-text-primary"
          />
        </div>
      )}

      <button
        type="button"
        onClick={onManualRestock}
        disabled={isRestocking}
        className={btnPillSm}
      >
        {isRestocking ? "Restocking…" : "Restock now"}
      </button>
    </div>
  );
}
