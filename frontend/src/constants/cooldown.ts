// Shared cooldown for automatic background operations (History-tab stock
// refresh, 3D site auto-test). The live value is user-configurable in Settings
// and persisted backend-side (listingPreferences.json); this is the fallback
// used until the setting is fetched.
export const DEFAULT_OPERATION_COOLDOWN_HOURS = 24;
export const MS_PER_HOUR = 60 * 60 * 1000;
export const IMPORT_SYNC_COOLDOWN_MS = 24 * MS_PER_HOUR;

// localStorage keys for the History-tab stock snapshot
export const STOCK_REFRESHED_AT_STORAGE_KEY = "axisStockRefreshedAt";
export const STOCK_QUANTITIES_STORAGE_KEY = "axisStockQuantities";
