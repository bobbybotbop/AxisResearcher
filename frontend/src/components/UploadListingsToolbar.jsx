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
      <div className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2.5 shadow-sm transition-colors focus-within:border-gray-400 focus-within:ring-1 focus-within:ring-gray-200">
        <Search size={20} className="shrink-0 text-gray-400" aria-hidden />
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by title…"
          className="min-w-0 flex-1 border-0 bg-transparent text-sm text-gray-900 outline-none placeholder:text-gray-400"
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
          className="relative flex h-10 w-10 items-center justify-center rounded-lg border border-gray-200 bg-white text-gray-700 shadow-sm transition-colors hover:border-gray-300 hover:bg-gray-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-gray-300"
        >
          <Filter size={20} aria-hidden />
          {filtersActive ? (
            <span
              className="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full bg-gray-900"
              aria-hidden
            />
          ) : null}
        </button>

        {menuOpen ? (
          <div
            role="menu"
            aria-label="Listing filters"
            className="absolute right-0 top-full z-30 mt-2 w-[min(calc(100vw-2rem),17rem)] origin-top-right rounded-xl border border-gray-200/90 bg-white py-3 shadow-[0_8px_30px_rgb(0,0,0,0.06)] ring-1 ring-black/3"
          >
            <div className="px-4 pb-2">
              <p className="text-[0.65rem] font-medium uppercase tracking-[0.12em] text-gray-400">
                Visibility
              </p>
              <label className="mt-2 flex cursor-pointer items-center gap-3 text-sm text-gray-800">
                <input
                  type="checkbox"
                  checked={showIncompleteListings}
                  onChange={(e) =>
                    onShowIncompleteListingsChange(e.target.checked)
                  }
                  className="h-3.5 w-3.5 rounded border-gray-300 text-gray-900 focus:ring-gray-400"
                />
                <span className="leading-snug">Show incomplete history</span>
              </label>
            </div>

            <div className="my-2 h-px bg-gray-100" />

            <div className="px-4 pt-1">
              <div className="flex items-baseline justify-between gap-2">
                <p className="text-[0.65rem] font-medium uppercase tracking-[0.12em] text-gray-400">
                  Created
                </p>
                {(dateFrom || dateTo) && (
                  <button
                    type="button"
                    onClick={clearDates}
                    className="text-xs font-medium text-gray-500 underline-offset-2 hover:text-gray-800 hover:underline"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="mt-3 grid grid-cols-1 gap-2.5">
                <label className="block">
                  <span className="mb-1 block text-xs text-gray-500">From</span>
                  <input
                    type="date"
                    value={dateFrom}
                    onChange={(e) => onDateFromChange(e.target.value)}
                    className="w-full rounded-md border border-gray-200 bg-gray-50/80 px-2.5 py-1.5 text-sm text-gray-900 transition-colors focus:border-gray-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-gray-200"
                  />
                </label>
                <label className="block">
                  <span className="mb-1 block text-xs text-gray-500">To</span>
                  <input
                    type="date"
                    value={dateTo}
                    onChange={(e) => onDateToChange(e.target.value)}
                    className="w-full rounded-md border border-gray-200 bg-gray-50/80 px-2.5 py-1.5 text-sm text-gray-900 transition-colors focus:border-gray-400 focus:bg-white focus:outline-none focus:ring-1 focus:ring-gray-200"
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
