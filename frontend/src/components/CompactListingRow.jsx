import { useState } from "react";
import {
  formatPrice,
  formatListingDateTime,
  formatCategoryShort,
} from "../utils/listingDisplay";

function LinkIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path d="M12.232 4.232a2.5 2.5 0 0 1 3.536 3.536l-1.225 1.224a.75.75 0 0 0 1.061 1.06l1.224-1.224a4 4 0 0 0-5.656-5.656l-3 3a4 4 0 0 0 .225 5.865.75.75 0 0 0 .977-1.138 2.5 2.5 0 0 1-.14-3.667l2.998-2.999Z" />
      <path d="M11.603 7.963a.75.75 0 0 0-.977 1.138 2.5 2.5 0 0 1 .14 3.667l-3 3a2.5 2.5 0 0 1-3.536-3.536l1.225-1.224a.75.75 0 0 0-1.061-1.06l-1.224 1.224a4 4 0 1 0 5.656 5.656l3-3a4 4 0 0 0-.223-5.865Z" />
    </svg>
  );
}

function UploadIcon() {
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      className="h-4 w-4"
    >
      <path d="M9.25 13.25a.75.75 0 0 0 1.5 0V4.636l2.955 3.129a.75.75 0 0 0 1.09-1.03l-4.25-4.5a.75.75 0 0 0-1.09 0l-4.25 4.5a.75.75 0 1 0 1.09 1.03L9.25 4.636v8.614Z" />
      <path d="M3.5 12.75a.75.75 0 0 0-1.5 0v2.5A2.75 2.75 0 0 0 4.75 18h10.5A2.75 2.75 0 0 0 18 15.25v-2.5a.75.75 0 0 0-1.5 0v2.5c0 .69-.56 1.25-1.25 1.25H4.75c-.69 0-1.25-.56-1.25-1.25v-2.5Z" />
    </svg>
  );
}

export default function CompactListingRow({
  listing,
  onCardClick,
  onUpload,
  isUploading,
  uploadResult,
  quantity,
  loadingQuantity,
  isManual = false,
}) {
  const urls = Array.isArray(listing.imageUrls) ? listing.imageUrls : [];
  const [imageIndex, setImageIndex] = useState(0);

  const safeIndex = urls.length ? imageIndex % urls.length : 0;
  const title = listing.title || "No title";
  const imageCount = listing.imageCount ?? urls.length ?? 0;
  const categoryId = String(listing.categoryId ?? "—");
  const categoryShort = formatCategoryShort(listing.categoryId);

  const ebayListingId = String(listing.ebayListingId ?? "").trim();
  const ebayItemUrl = ebayListingId
    ? `https://www.ebay.com/itm/${ebayListingId}`
    : "";

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => onCardClick?.(listing)}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onCardClick?.(listing);
        }
      }}
      className={`flex w-full cursor-pointer overflow-hidden rounded-xl bg-surface-panel shadow-sm transition-shadow hover:shadow-md ${isManual ? "border-2 border-border-default" : "border border-border-default"}`}
    >
      {/* Thumbnail */}
      <div className="relative h-20 w-24 shrink-0 bg-surface-muted">
        {urls.length > 0 ? (
          <div className="flex h-full w-full items-center justify-center">
            <img
              src={urls[safeIndex]}
              alt={title}
              className="max-h-full max-w-full object-contain"
            />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-text-muted">
            No image
          </div>
        )}
        {urls.length > 1 && (
          <div className="absolute bottom-1.5 left-0 right-0 flex justify-center gap-1.5">
            {urls.map((_, i) => (
              <button
                key={i}
                type="button"
                aria-label={`Show image ${i + 1}`}
                className={`h-1.5 w-1.5 rounded-full ring-1 ring-white ring-offset-0 transition-all ${
                  i === safeIndex
                    ? "w-4 bg-black"
                    : "bg-black/50 hover:bg-black/80"
                }`}
                onClick={(e) => {
                  e.stopPropagation();
                  setImageIndex(i);
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* eBay action strip — side by side with image */}
      <div
        className="flex h-20 w-8 shrink-0 border-l border-r border-border-default"
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.stopPropagation()}
      >
        {ebayItemUrl ? (
          <a
            href={ebayItemUrl}
            target="_blank"
            rel="noopener noreferrer"
            title="View on eBay"
            className="flex h-full w-full items-center justify-center bg-surface-muted text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary"
            onClick={(e) => e.stopPropagation()}
          >
            <LinkIcon />
          </a>
        ) : (
          <button
            type="button"
            title={isUploading ? "Uploading..." : "Upload to eBay"}
            className="flex h-full w-full cursor-pointer items-center justify-center bg-surface-muted text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary disabled:cursor-not-allowed disabled:opacity-50"
            onClick={(e) => {
              e.stopPropagation();
              onUpload?.(listing);
            }}
            disabled={isUploading}
          >
            {isUploading ? (
              <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
            ) : (
              <UploadIcon />
            )}
          </button>
        )}
      </div>

      {/* Content column */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col justify-center gap-1 px-3 py-2">
        <div className="flex shrink-0 items-center justify-between gap-4">
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-1 text-base font-semibold leading-snug text-text-primary">
              {title}
            </h3>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0 text-sm text-text-muted">
              <span className="font-mono text-text-muted">{listing.sku}</span>
              {listing.createdDateTime && (
                <>
                  <span className="text-text-muted">·</span>
                  <span>{formatListingDateTime(listing.createdDateTime)}</span>
                </>
              )}
              <span className="text-text-muted">·</span>
              <span
                className="whitespace-nowrap"
                title="Number of images on the listing"
              >
                {imageCount} {imageCount === 1 ? "image" : "images"}
              </span>
              <span className="text-text-muted">·</span>
              <span
                className="whitespace-nowrap font-medium text-text-muted"
                title={
                  categoryId !== "—" ? `Category ID: ${categoryId}` : undefined
                }
              >
                {categoryShort === "—" ? "—" : `Cat ${categoryShort}`}
              </span>
              {String(listing.ebayListingId ?? "").trim() ? (
                <>
                  <span className="text-text-muted">·</span>
                  {quantity != null ? (
                    <span
                      className="whitespace-nowrap"
                      title="Live eBay stock quantity"
                    >
                      Qty: {quantity}
                    </span>
                  ) : loadingQuantity ? (
                    <span
                      className="inline-flex items-center gap-1 whitespace-nowrap text-text-muted"
                      title="Loading quantity"
                    >
                      Qty:{" "}
                      <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent opacity-50" />
                    </span>
                  ) : (
                    <span
                      className="whitespace-nowrap text-text-muted"
                      title="Quantity unavailable"
                    >
                      Qty: —
                    </span>
                  )}
                </>
              ) : null}
            </p>
          </div>
          <div className="shrink-0 text-right">
            <div className="text-lg font-bold text-text-primary">
              {formatPrice(listing.price, listing.currency)}
            </div>
          </div>
        </div>

        {uploadResult && (
          <div
            className="flex items-center gap-2 rounded border border-green-200 bg-white px-2 py-1"
            onClick={(e) => e.stopPropagation()}
          >
            <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-full border border-green-700 bg-white text-xs font-bold text-green-800">
              ✓
            </span>
            <div className="flex min-w-0 gap-2 text-xs">
              {uploadResult.listingId && (
                <a
                  href={`https://www.ebay.com/itm/${uploadResult.listingId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-primary underline hover:no-underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  {uploadResult.listingId}
                </a>
              )}
              {uploadResult.href && (
                <a
                  href={uploadResult.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="font-semibold text-primary underline hover:no-underline"
                  onClick={(e) => e.stopPropagation()}
                >
                  View on eBay →
                </a>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
