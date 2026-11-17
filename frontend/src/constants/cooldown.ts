// Shared cooldown for automatic background operations (History-tab stock
// refresh, 3D site auto-test). The live value is user-configurable in Settings
// and persisted backend-side (listingPreferences.json); this is the fallback
// used until the setting is fetched.
export const DEFAULT_OPERATION_COOLDOWN_HOURS = 24;
export const MS_PER_HOUR = 60 * 60 * 1000;
export const IMPORT_SYNC_COOLDOWN_MS = 24 * MS_PER_HOUR;

// localStorage keys for the History-tab stock snapshot. Bumped to v2: the v1
// cache could hold lifetime listed totals (stock + sold) instead of available
// stock, and was keyed by the retired MANUAL_* SKU format.
export const STOCK_REFRESHED_AT_STORAGE_KEY = "axisStockRefreshedAtV2";
export const STOCK_QUANTITIES_STORAGE_KEY = "axisStockQuantitiesV2";

// localStorage key for the startup eBay status sync (soft-deletes listings
// ended outside the app). Runs at most once per operationCooldownHours.
export const EBAY_STARTUP_SYNCED_AT_STORAGE_KEY = "axisEbayStartupSyncedAt";

// Window event name carrying the startup sync summary. Startup toasts are
// wired directly in App.tsx; the event remains for other consumers.
export const EBAY_STARTUP_SYNC_EVENT = "axis:ebay-startup-sync";

export interface EbayStartupSyncSummary {
  removed: number;
  healed: number;
  aborted: boolean;
  reason?: string;
  error?: string;
}
