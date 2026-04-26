import { useEffect, useRef, useState } from "react";
import { Search, Filter } from "@mynaui/icons-react";

export default function UploadListingsToolbar({
  searchQuery,
  onSearchChange,
  showIncompleteListings,
  onShowIncompleteListingsChange,
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const rootRef = useRef(null);

  const filtersActive =
    showIncompleteListings || Boolean(dateFrom?.trim()) || Boolean(dateTo?.trim());

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
    <div className="mb-5 mt-8 flex flex-col gap-3 md:flex-row md:items-start md:justify-between md:gap-4">
      <div className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-border-default bg-surface-panel px-3 py-2.5 shadow-sm transition-colors focus-within:border-border-default focus-within:ring-1 focus-within:ring-border-default/40">
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

      <div className="relative shrink-0 self-end md:self-start" ref={rootRef}>
        <button
          type="button"
          aria-expanded={menuOpen}
          aria-haspopup="menu"
          aria-label="Open filters"
          onClick={() => setMenuOpen((o) => !o)}
          className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-border-default bg-surface-panel text-text-primary shadow-sm transition-colors hover:border-border-default hover:bg-surface-hover focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-border-default/40"
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
                  <span className="mb-1 block text-xs text-text-muted">From</span>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => onDateFromChange(e.target.value)}
                    className="w-full rounded-md border border-border-default bg-surface-muted px-2.5 py-1.5 text-sm text-text-primary transition-colors focus:border-border-default focus:bg-surface-panel focus:outline-none focus:ring-1 focus:ring-border-default/40"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-text-muted">To</span>
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
    </div>
  );
}
