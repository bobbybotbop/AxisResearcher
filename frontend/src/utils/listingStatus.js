export const LISTING_PLACEHOLDER = "[need to change]";

/** Draft / placeholder rows hidden from Upload tab by default. */
export function isIncomplete(listing) {
  const title = String(listing?.title ?? "").trim();
  if (title === LISTING_PLACEHOLDER) return true;
  const urls = listing?.imageUrls;
  const hasImages = Array.isArray(urls) && urls.length > 0;
  if (hasImages) return false;
  const desc = String(listing?.description ?? "").trim();
  return desc === LISTING_PLACEHOLDER;
}
