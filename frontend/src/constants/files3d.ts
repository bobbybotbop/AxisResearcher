export const DOWNLOAD_MODE_FULL_ZIP = "full_zip" as const;
export const DOWNLOAD_MODE_SINGLE_FILE = "single_file" as const;
// Frontend-only mode: fetches the full zip, unzips client-side, saves every file
export const DOWNLOAD_MODE_FILES = "files" as const;
export type DownloadMode = typeof DOWNLOAD_MODE_FULL_ZIP | typeof DOWNLOAD_MODE_SINGLE_FILE | typeof DOWNLOAD_MODE_FILES;

export interface ThreeDSiteInfo {
  site: string;
  supported: boolean;
  requiresAuth?: boolean;
}

export const THREE_D_SITES: ThreeDSiteInfo[] = [
  { site: "makerworld.com", supported: true, requiresAuth: true },
  { site: "printables.com", supported: true },
  { site: "cults3d.com", supported: true, requiresAuth: true },
  { site: "thingiverse.com", supported: true },
  { site: "thangs.com", supported: true },
];

export type ThreeDSiteStatus = Record<string, { ok: boolean; message: string }>;

// Sites that require a login. The API route prefix used for their
// session/probe endpoints: /api/{prefix}-session/* and /api/{prefix}-probe.
export type ThreeDAuthSite = "makerworld.com" | "cults3d.com";
export const THREE_D_AUTH_SITE_API_PREFIX: Record<ThreeDAuthSite, string> = {
  "makerworld.com": "makerworld",
  "cults3d.com": "cults3d",
};

export interface ThreeDCredentialStatus {
  has_credentials: boolean;
  auth_type: string | null;
  email: string;
  profile_present?: boolean;
}

// Download-capable sites are auto-tested on page load, at most once per the
// shared operation cooldown (DEFAULT_OPERATION_COOLDOWN_HOURS in ./cooldown,
// user-configurable in Settings).
export const THREE_D_SITE_STATUS_STORAGE_KEY = "axis3dSiteStatus";
export const THREE_D_SITE_TESTED_AT_STORAGE_KEY = "axis3dSiteTestedAt";
export const THREE_D_SITE_IMAGE_STATUS_STORAGE_KEY = "axis3dSiteImageStatus";
export const THREE_D_SITES_ENABLED_STORAGE_KEY = "axis3dSitesEnabled";
export const THREE_D_SITE_PRIORITY_STORAGE_KEY = "axis3dSitePriority";

// Pipelines that can produce a 3D file link for the shared download step
export const PIPELINE_IMAGE_SEARCH = "image_search" as const;
export const PIPELINE_TITLE_SEARCH = "title_search" as const;
export type Pipeline = typeof PIPELINE_IMAGE_SEARCH | typeof PIPELINE_TITLE_SEARCH;

// Match labels recorded on a Saved 3D File: "confirmed" = an eBay photo
// matched a site image (pHash); "unconfirmed" = title-search link without an
// image confirmation
export const MATCH_LABEL_CONFIRMED_IMAGE_MATCH = "confirmed_image_match" as const;
export const MATCH_LABEL_UNCONFIRMED_TITLE_MATCH = "unconfirmed_title_match" as const;
export type MatchLabel = typeof MATCH_LABEL_CONFIRMED_IMAGE_MATCH | typeof MATCH_LABEL_UNCONFIRMED_TITLE_MATCH;

// The user's site-priority order, most-preferred first. Stored order may be
// stale (sites added/removed), so reconcile against the canonical list:
// keep stored sites that still exist, then append any new sites in default order.
export function normalizeThreeDSitePriority(stored: unknown): string[] {
  const all = THREE_D_SITES.map(({ site }) => site);
  const storedList = Array.isArray(stored) ? stored.filter((s): s is string => typeof s === "string") : [];
  const kept = storedList.filter((s) => all.includes(s));
  const missing = all.filter((s) => !kept.includes(s));
  return [...kept, ...missing];
}

// Map a result link to its 3D site key (e.g. "printables.com"), or null if not a known site
export function threeDSiteKeyFromLink(link: string): string | null {
  try {
    const host = new URL(link).hostname.toLowerCase().replace(/^www\./, "");
    for (const { site } of THREE_D_SITES) {
      if (host === site || host.endsWith("." + site)) return site;
    }
  } catch {
    // not a parseable URL
  }
  return null;
}
