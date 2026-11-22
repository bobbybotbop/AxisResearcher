export type TabName = "create" | "upload" | "saved-3d-files" | "data-browser" | "logs" | "test-workflow" | "testing" | "settings";

export const TAB_PATHS: Record<TabName, string> = {
  create: "/create",
  upload: "/history",
  "saved-3d-files": "/saved-3d-files",
  "data-browser": "/data-browser",
  logs: "/logs",
  "test-workflow": "/test-workflow",
  testing: "/testing",
  settings: "/settings",
};
