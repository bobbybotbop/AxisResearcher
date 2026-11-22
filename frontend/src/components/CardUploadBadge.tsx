/** Per-card upload waiting state, owned by the Status Store (ADR 0002). */
export type CardUploadStatus = "uploading" | "success" | "error";

interface CardUploadBadgeProps {
  status: CardUploadStatus;
  /** Positioning classes for the absolutely-placed wrapper (per-card layout). */
  className?: string;
}

/**
 * Per-card upload status badge (spinner → check/error), shared by the compact
 * row and the detailed card. Waiting-state UI only (ADR 0002).
 */
export default function CardUploadBadge({ status, className = "" }: CardUploadBadgeProps) {
  return (
    <div
      className={`absolute z-10 ${className}`}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      <span
        role={status === "error" ? "alert" : "status"}
        title={
          status === "uploading"
            ? "Uploading to eBay…"
            : status === "success"
              ? "Uploaded to eBay"
              : "Upload failed"
        }
        className={`flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold shadow-sm ${
          status === "uploading"
            ? "border-border-default bg-surface-panel text-text-primary"
            : status === "success"
              ? "border-success/30 bg-success text-white"
              : "border-danger/30 bg-danger text-white"
        }`}
      >
        {status === "uploading" ? (
          <span
            className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
            aria-hidden="true"
          />
        ) : (
          <span aria-hidden="true">{status === "success" ? "✓" : "✕"}</span>
        )}
        {status === "uploading" ? "Uploading" : status === "success" ? "Uploaded" : "Failed"}
      </span>
    </div>
  );
}
