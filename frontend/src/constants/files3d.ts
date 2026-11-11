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
  { site: "yeggi.com", supported: false },
  { site: "cults3d.com", supported: true, requiresAuth: true },
  { site: "thingiverse.com", supported: true },
  { site: "thangs.com", supported: true },
];

export type ThreeDSiteStatus = Record<string, { ok: boolean; message: string }>;

// Download-capable sites are auto-tested on page load, at most once per the
// shared operation cooldown (DEFAULT_OPERATION_COOLDOWN_HOURS in ./cooldown,
// user-configurable in Settings).
export const THREE_D_SITE_STATUS_STORAGE_KEY = "axis3dSiteStatus";
export const THREE_D_SITE_TESTED_AT_STORAGE_KEY = "axis3dSiteTestedAt";

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
