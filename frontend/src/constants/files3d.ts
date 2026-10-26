export const DOWNLOAD_MODE_FULL_ZIP = "full_zip" as const;
export const DOWNLOAD_MODE_SINGLE_FILE = "single_file" as const;
export type DownloadMode = typeof DOWNLOAD_MODE_FULL_ZIP | typeof DOWNLOAD_MODE_SINGLE_FILE;
