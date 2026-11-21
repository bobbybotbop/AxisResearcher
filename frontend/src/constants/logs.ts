export interface FilterOption {
  key: string;
  label: string;
}

export const LOG_EVENT_LABELS: Record<string, string> = {
  draft_created: "Draft Created",
  draft_completed: "Draft Completed",
  upload: "Upload",
  restock: "Restock",
  import: "Import",
  sync_startup: "Sync (Startup)",
  sync_active: "Sync (Active)",
};

export const LOG_SECTION_LABELS = {
  restocked: "Restocked",
  failed: "Failed",
  notFound: "Not found on eBay",
  imported: "Imported",
  updated: "Updated",
  newlyInactive: "Newly inactive",
  removedEnded: "Removed (ended on eBay)",
  healed: "Healed",
  noSkus: "No SKUs",
} as const;

export const LOG_FILTER_CHIPS: FilterOption[] = [
  { key: "all", label: "All" },
  { key: "upload", label: "Uploads" },
  { key: "restock", label: "Restocks" },
  { key: "draft_created", label: "Drafts Created" },
  { key: "draft_completed", label: "Drafts Completed" },
  { key: "import", label: "Imports" },
  { key: "sync_startup", label: "Syncs (Startup)" },
  { key: "sync_active", label: "Syncs (Active)" },
];
