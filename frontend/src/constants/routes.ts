export type TabName = "create" | "upload" | "logs" | "test-workflow" | "testing" | "settings";

export const TAB_PATHS: Record<TabName, string> = {
  create: "/create",
  upload: "/history",
  logs: "/logs",
  "test-workflow": "/test-workflow",
  testing: "/testing",
  settings: "/settings",
};
