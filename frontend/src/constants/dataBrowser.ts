// Tables exposed by /api/data-browser/<table> — mirrors
// DATA_BROWSER_TABLES in backend/constants/data_browser.py
export const DATA_BROWSER_TABLES = ["listings", "preferences", "logs", "prompts"] as const;
export type DataBrowserTableName = (typeof DATA_BROWSER_TABLES)[number];
