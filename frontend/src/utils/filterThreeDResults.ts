import { threeDSiteKeyFromLink, type ThreeDSiteStatus } from "../constants/files3d";

interface SiteTypedResult {
  link: string;
  site_type?: string;
}

interface FilteredThreeDResults<T> {
  /** Whitelisted results whose site's operational test did not fail */
  filtered: T[];
  /** Site keys skipped because their operational test failed */
  skippedSites: string[];
}

/**
 * Keep whitelisted results only, dropping any from 3D sites whose scraper
 * failed its operational test (Settings > 3D File Sites). Shared by the
 * Image Search and Title Search pipelines.
 */
export function filterOperationalThreeDResults<T extends SiteTypedResult>(
  results: T[] | undefined,
  siteStatus: ThreeDSiteStatus | null,
): FilteredThreeDResults<T> {
  const whitelisted = (results || []).filter((r) => r.site_type === "whitelisted");
  const skipped = new Set<string>();
  const filtered = whitelisted.filter((r) => {
    const key = threeDSiteKeyFromLink(r.link);
    if (key && siteStatus?.[key] && !siteStatus[key].ok) {
      skipped.add(key);
      return false;
    }
    return true;
  });
  return { filtered, skippedSites: [...skipped] };
}

/** Toast describing the sites skipped by filterOperationalThreeDResults, if any. */
export function toastSkippedSites(
  addToast: ((type: string, message: string) => void) | undefined,
  skippedSites: string[],
): void {
  if (skippedSites.length > 0) {
    addToast?.("info", `Skipped results from ${skippedSites.join(", ")} — site failed its operational test (see Settings > 3D File Sites)`);
  }
}
