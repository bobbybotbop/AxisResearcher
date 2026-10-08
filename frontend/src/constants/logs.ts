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
};

export const LOG_FILTER_CHIPS: FilterOption[] = [
  { key: "all", label: "All" },
  { key: "upload", label: "Uploads" },
  { key: "restock", label: "Restocks" },
  { key: "draft_created", label: "Drafts Created" },
  { key: "draft_completed", label: "Drafts Completed" },
  { key: "import", label: "Imports" },
];
