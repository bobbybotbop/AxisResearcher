export type TabName = "create" | "upload" | "data-browser" | "logs" | "test-workflow" | "testing" | "settings";

export const TAB_PATHS: Record<TabName, string> = {
  create: "/create",
  upload: "/history",
  "data-browser": "/data-browser",
  logs: "/logs",
  "test-workflow": "/test-workflow",
  testing: "/testing",
  settings: "/settings",
};
