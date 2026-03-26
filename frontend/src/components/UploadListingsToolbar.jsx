import { Search, Filter } from "@mynaui/icons-react";

export default function UploadListingsToolbar({
  searchQuery,
  onSearchChange,
  showIncompleteListings,
  onShowIncompleteListingsChange,
}) {
  return (
    <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between md:gap-4">
      <div className="flex min-w-0 flex-1 items-center gap-2 rounded-lg border-2 border-gray-300 bg-white px-3 py-2 transition-colors focus-within:border-primary">
        <Search
          size={20}
          className="shrink-0 text-gray-500"
          aria-hidden
        />
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Search by title…"
          className="min-w-0 flex-1 border-0 bg-transparent text-gray-900 outline-none placeholder:text-gray-400 disabled:bg-transparent"
          aria-label="Search listings by title"
        />
      </div>
      <label className="flex cursor-pointer items-center gap-2 text-sm text-gray-700 select-none md:shrink-0">
        <Filter size={20} className="shrink-0 text-gray-500" aria-hidden />
        <input
          type="checkbox"
          checked={showIncompleteListings}
          onChange={(e) => onShowIncompleteListingsChange(e.target.checked)}
          className="h-4 w-4 rounded border-gray-300 text-primary focus:ring-primary"
        />
        <span>Show incomplete listings</span>
      </label>
    </div>
  );
}
