export const LISTING_PLACEHOLDER = "[need to change]";

/** Returns true when the listing is missing data required to upload to eBay. */
export function isIncomplete(listing) {
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

/** Returns true when the listing has been published to eBay (has a valid ebayListingId). */
export function isUploaded(listing) {
  return Boolean(String(listing?.ebayListingId ?? "").trim());
}
