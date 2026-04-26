import { useLayoutEffect, useRef, useState } from "react";
import { btnPill } from "../styles/buttonPill";

const THUMB_PX = 80;
const THUMB_GAP = 8;

/** Thumbnails for all images except the hero; overflow → last slot blurred with +N. */
function RestGalleryStrip({ urls, heroIndex, onPickIndex }) {
  const containerRef = useRef(null);
  const [maxSlots, setMaxSlots] = useState(12);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const measure = () => {
      const w = el.getBoundingClientRect().width;
      const stride = THUMB_PX + THUMB_GAP;
      const n = Math.max(1, Math.floor((w + THUMB_GAP) / stride));
      setMaxSlots(n);
    };

    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const items = urls
    .map((url, i) => ({ url, i }))
    .filter(({ i }) => i !== heroIndex);

  if (items.length === 0) return null;

  const overflow = items.length > maxSlots;
  const clearCount = overflow ? maxSlots - 1 : items.length;
  const visibleClear = items.slice(0, clearCount);
  const overflowPeek = overflow ? items[clearCount] : null;
  const moreCount = overflow ? items.length - maxSlots : 0;

  return (
    <div
      ref={containerRef}
      className="flex min-w-0 flex-nowrap gap-2"
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
    >
      {visibleClear.map(({ url, i }) => (
        <button
          key={i}
          type="button"
          aria-label={`Show image ${i + 1} in main preview`}
          className="h-20 w-20 shrink-0 overflow-hidden rounded-md border border-border-default bg-surface-muted ring-offset-2 transition-shadow hover:ring-2 hover:ring-primary/40 focus:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          onClick={(e) => {
            e.stopPropagation();
            onPickIndex(i);
          }}
        >
          <img src={url} alt="" className="h-full w-full object-cover" />
        </button>
      ))}
      {overflow && overflowPeek && (
        <div
          className="relative h-20 w-20 shrink-0 overflow-hidden rounded-md border border-border-default"
          title={`${moreCount} more image${moreCount === 1 ? "" : "s"} not shown`}
        >
          <img
            src={overflowPeek.url}
            alt=""
            aria-hidden
            className="h-full w-full scale-110 object-cover blur-sm"
          />
          <div className="absolute inset-0 flex items-center justify-center bg-black/45">
            <span className="text-sm font-bold tabular-nums text-white">
              +{moreCount}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}

function formatPrice(value, currency = "USD") {
  if (value === undefined || value === null || value === "N/A") return "—";
  const num = Number(value);
  if (Number.isNaN(num)) return `$${value}`;
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: currency || "USD",
      maximumFractionDigits: 2,
    }).format(num);
  } catch {
    return `$${value}`;
  }
}

/** e.g. 3/7/2026, 10:08 PM — no leading zeros on month/day; local time. */
function formatListingDateTime(iso) {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    const m = d.getMonth() + 1;
    const day = d.getDate();
    const y = d.getFullYear();
    const time = d.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
      hour12: true,
    });
    return `${m}/${day}/${y}, ${time}`;
  } catch {
    return "—";
  }
}

export default function GeneratedListingCard({
  listing,
  onCardClick,
  onUpload,
  isUploading,
  uploadResult,
}) {
  const urls = Array.isArray(listing.imageUrls) ? listing.imageUrls : [];
  const [imageIndex, setImageIndex] = useState(0);

  const safeIndex = urls.length ? imageIndex % urls.length : 0;
  const title = listing.title || "No title";
  const imageCount = listing.imageCount ?? urls.length ?? 0;
  const categoryId = String(listing.categoryId ?? "—");
  const categoryShort =
    categoryId.length > 10 ? `${categoryId.slice(0, 8)}…` : categoryId;

  const ebayListingId = String(listing.ebayListingId ?? "").trim();
  const ebayItemUrl = ebayListingId
    ? `https://www.ebay.com/itm/${ebayListingId}`
    : "";

  const descriptionHtml =
    typeof listing.description === "string" ? listing.description.trim() : "";

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
      {/* Image column — hero + dots + upload below image */}
      <div className="flex w-full shrink-0 flex-col border-b border-border-default md:w-[30%] md:max-w-md md:border-b-0 md:border-r md:border-border-default">
        <div className="relative w-full">
          <div className="aspect-square w-full border-b border-border-default bg-surface-muted md:border-b-0">
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
            <div className="absolute bottom-3 left-0 right-0 flex justify-center gap-1.5">
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
          className="border-t border-border-default bg-surface-panel p-3 sm:p-4"
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
              <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-white p-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-green-700 bg-white text-lg font-bold text-green-800">
                  ✓
                </div>
                <div className="min-w-0 flex-1 text-sm text-text-primary">
                  {uploadResult.listingId && (
                    <div>
                      <strong>Listing ID:</strong>{" "}
                      <a
                        href={`https://www.ebay.com/itm/${uploadResult.listingId}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-primary underline hover:no-underline"
                      >
                        {uploadResult.listingId}
                      </a>
                    </div>
                  )}
                  {uploadResult.href && (
                    <div>
                      <a
                        href={uploadResult.href}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-primary underline hover:no-underline"
                      >
                        View on eBay →
                      </a>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Content column — capped to the left column's height on md; description scrolls */}
      <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4 p-4 sm:p-5 md:overflow-hidden">
        {/* Header */}
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="line-clamp-2 text-lg font-bold leading-tight text-text-primary sm:text-xl">
                {title}
              </h3>
            </div>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-text-muted">
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
            </p>
          </div>
          <div className="shrink-0 text-left sm:text-right">
            <div className="text-xl font-bold text-text-primary sm:text-2xl">
              {formatPrice(listing.price, listing.currency)}
            </div>
          </div>
        </div>

        <div
          className="flex min-h-0 flex-1 flex-col gap-3 border-t border-border-default pt-4"
          onClick={(e) => e.stopPropagation()}
          onKeyDown={(e) => e.stopPropagation()}
        >
          <RestGalleryStrip
            urls={urls}
            heroIndex={safeIndex}
            onPickIndex={setImageIndex}
          />

          {descriptionHtml ? (
            <div className="rounded-lg border border-border-default bg-surface-muted p-3">
              <div
                className="max-h-[calc(1.625em*6)] min-h-0 overflow-y-auto overflow-x-hidden overscroll-contain text-left text-sm leading-relaxed text-text-primary [&_a]:text-primary [&_a]:underline [&_h1]:mb-2 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mb-2 [&_h2]:text-sm [&_h2]:font-semibold [&_img]:h-auto [&_img]:max-w-full [&_li]:my-0.5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_p]:first:mt-0 [&_table]:my-2 [&_table]:max-w-full [&_td]:border [&_td]:border-border-default [&_td]:p-1.5 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5"
                dangerouslySetInnerHTML={{ __html: descriptionHtml }}
              />
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
