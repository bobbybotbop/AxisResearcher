import type { Listing } from "../types/listing";

export const LISTING_PLACEHOLDER = "[need to change]";

/** Returns true when the listing is missing data required to upload to eBay. */
export function isIncomplete(listing: Partial<Listing> | null | undefined): boolean {
  // Manual listings are already live on eBay — upload-readiness does not apply.
  if (listing?.isManualListing) return false;
  const title = String(listing?.title ?? "").trim();
  if (!title || title === LISTING_PLACEHOLDER) return true;
  const urls = listing?.imageUrls;
  if (!Array.isArray(urls) || urls.length === 0) return true;
  const price = listing?.price;
  if (!price || String(price).trim() === "N/A") return true;
  const categoryId = listing?.categoryId;
  if (!categoryId || String(categoryId).trim() === "N/A") return true;
  return false;
}

/** SKU shown to the user: the seller's own SKU when known, else the internal SKU. */
export function displaySku(listing: Partial<Listing> | null | undefined): string {
  const sellerSku = String(listing?.sellerSku ?? "").trim();
  return sellerSku || String(listing?.sku ?? "");
}

/** Returns true when the listing has been published to eBay (has a valid ebayListingId). */
export function isUploaded(listing: Partial<Listing> | null | undefined): boolean {
  return Boolean(String(listing?.ebayListingId ?? "").trim());
}

/** Returns true when the listing is a draft: incomplete, not yet uploaded, or no longer found on eBay. */
export function isDraft(listing: Partial<Listing> | null | undefined): boolean {
  return (
    isIncomplete(listing) ||
    !isUploaded(listing) ||
    (listing?.ebay_status as string | undefined) === "not_found"
  );
}

/** Returns true when the listing is a draft that has all required data and can be uploaded. */
export function isReadyToUpload(
  listing: Partial<Listing> | null | undefined,
): boolean {
  return isDraft(listing) && !isIncomplete(listing);
}
