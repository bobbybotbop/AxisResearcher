import {
  formatPrice,
  formatListingDateTime,
  formatCategoryShort,
} from "../utils/listingDisplay";

function ListingDetails({ listing, photos, sku }) {
  if (!listing) {
    return null;
  }

  const title = listing.title || "No title";
  const identifier = sku || listing.itemId || "—";
  const imageCount = Array.isArray(photos) ? photos.length : 0;
  const categoryId = String(listing.categoryId ?? "—");
  const categoryShort = formatCategoryShort(listing.categoryId);
  const description =
    typeof listing.description === "string" ? listing.description.trim() : "";
  const hasDescription =
    description && description !== "No description available";

  return (
    <div className="mb-6 rounded-xl border border-border-default bg-surface-panel px-4 pb-4 pt-6 shadow-sm sm:px-5 sm:pb-5 sm:pt-7">
      <div className="flex flex-col gap-4">
        <div className="flex shrink-0 flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="line-clamp-2 text-lg font-bold leading-tight text-text-primary sm:text-xl">
                {title}
              </h3>
            </div>
            <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-text-muted">
              <span className="font-mono text-text-muted">{identifier}</span>
              {listing.itemCreationDate && (
                <>
                  <span className="text-text-muted">·</span>
                  <span>{formatListingDateTime(listing.itemCreationDate)}</span>
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

        {hasDescription && (
          <div className="rounded-lg border border-border-default bg-surface-muted p-3">
            <p className="max-h-[calc(1.625em*6)] min-h-0 overflow-y-auto overflow-x-hidden overscroll-contain whitespace-pre-wrap text-left text-sm leading-relaxed text-text-primary">
              {description}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

export default ListingDetails;
