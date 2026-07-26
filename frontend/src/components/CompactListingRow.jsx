import { useState } from "react";
import { btnPill } from "../styles/buttonPill";
import {
  formatPrice,
  formatListingDateTime,
  formatCategoryShort,
} from "../utils/listingDisplay";

export default function CompactListingRow({
  listing,
  onCardClick,
  onUpload,
  isUploading,
  uploadResult,
  quantity,
  loadingQuantity,
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
      className="flex w-full cursor-pointer flex-col overflow-hidden rounded-xl border border-border-default bg-surface-panel shadow-sm transition-shadow hover:shadow-md md:flex-row md:items-stretch"
    >
      {/* Image column — fixed h-24 hero + upload button */}
      <div className="flex w-full shrink-0 flex-col border-b border-border-default md:w-[30%] md:max-w-md md:border-b-0 md:border-r md:border-border-default">
        <div className="relative w-full">
          <div className="h-24 w-full bg-surface-muted">
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
          </div>
          {urls.length > 1 && (
            <div className="absolute bottom-2 left-0 right-0 flex justify-center gap-1.5">
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
        <div
          className="border-t border-border-default bg-surface-panel p-2 sm:p-3"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <div className="flex flex-col gap-2">
            {ebayItemUrl ? (
              <a
                href={ebayItemUrl}
                target="_blank"
                rel="noopener noreferrer"
                className={`inline-flex w-full items-center justify-center no-underline ${btnPill}`}
                onClick={(e) => e.stopPropagation()}
              >
                View on eBay
              </a>
            ) : (
              <button
                type="button"
                className={`w-full ${btnPill} disabled:transform-none`}
                onClick={() => onUpload?.(listing)}
                disabled={isUploading}
              >
                {isUploading ? "Uploading..." : "Upload to eBay"}
              </button>
            )}
            {uploadResult && (
              <div className="flex items-center gap-2 rounded-lg border border-green-200 bg-white p-2">
                <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-green-700 bg-white text-sm font-bold text-green-800">
                  ✓
                </div>
                <div className="min-w-0 flex-1 text-xs text-text-primary">
                  {uploadResult.listingId && (
                    <a
                      href={`https://www.ebay.com/itm/${uploadResult.listingId}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="font-semibold text-primary underline hover:no-underline"
                    >
                      {uploadResult.listingId}
                    </a>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content column — title + meta only, no description, no gallery strip */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col justify-center gap-2 p-3 sm:p-4">
        <div className="flex shrink-0 flex-col gap-1 sm:flex-row sm:items-center sm:justify-between sm:gap-4">
          <div className="min-w-0 flex-1">
            <h3 className="line-clamp-1 text-base font-semibold leading-snug text-text-primary">
              {title}
            </h3>
            <p className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-sm text-text-muted">
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
          <div className="shrink-0 text-left sm:text-right">
            <div className="text-lg font-bold text-text-primary">
              {formatPrice(listing.price, listing.currency)}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
