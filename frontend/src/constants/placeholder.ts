/**
 * Placeholder image mode (test users only): locally-rendered stand-in images
 * used in place of AI-generated images so the create workflow can be exercised
 * without spending image-generation credits.
 */

export const PLACEHOLDER_IMAGE_SIZE = 1024;
export const PLACEHOLDER_BACKGROUND_COLOR = "#d1d5db";
export const PLACEHOLDER_TEXT_COLOR = "#6b7280";
export const PLACEHOLDER_SUBTEXT_COLOR = "#9ca3af";

/**
 * Offline SVG data URL placeholder. Used by the mock Test Workflow tab, which
 * never performs real network or eBay upload calls.
 */
export function createPlaceholderImageDataUrl(index: number): string {
  const svg =
    `<svg xmlns="http://www.w3.org/2000/svg" width="${PLACEHOLDER_IMAGE_SIZE}" height="${PLACEHOLDER_IMAGE_SIZE}">` +
    `<rect fill="${PLACEHOLDER_BACKGROUND_COLOR}" width="${PLACEHOLDER_IMAGE_SIZE}" height="${PLACEHOLDER_IMAGE_SIZE}"/>` +
    `<text fill="${PLACEHOLDER_TEXT_COLOR}" font-family="sans-serif" font-size="72" font-weight="bold" x="50%" y="47%" text-anchor="middle">PLACEHOLDER</text>` +
    `<text fill="${PLACEHOLDER_SUBTEXT_COLOR}" font-family="sans-serif" font-size="44" x="50%" y="58%" text-anchor="middle">Image ${index}</text>` +
    `</svg>`;
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

/**
 * Renders the placeholder as a real PNG Blob via an offscreen canvas. The PNG
 * can be uploaded to eBay Picture Services (POST /api/upload-image) so the
 * resulting EPS URL is valid in a live listing's imageUrls.
 */
export function renderPlaceholderImagePngBlob(index: number): Promise<Blob> {
  const canvas = document.createElement("canvas");
  canvas.width = PLACEHOLDER_IMAGE_SIZE;
  canvas.height = PLACEHOLDER_IMAGE_SIZE;
  const ctx = canvas.getContext("2d");
  if (!ctx) {
    return Promise.reject(new Error("Could not create canvas context"));
  }

  ctx.fillStyle = PLACEHOLDER_BACKGROUND_COLOR;
  ctx.fillRect(0, 0, PLACEHOLDER_IMAGE_SIZE, PLACEHOLDER_IMAGE_SIZE);

  ctx.textAlign = "center";
  ctx.textBaseline = "middle";

  ctx.fillStyle = PLACEHOLDER_TEXT_COLOR;
  ctx.font = "bold 72px sans-serif";
  ctx.fillText("PLACEHOLDER", PLACEHOLDER_IMAGE_SIZE / 2, PLACEHOLDER_IMAGE_SIZE * 0.47);

  ctx.fillStyle = PLACEHOLDER_SUBTEXT_COLOR;
  ctx.font = "44px sans-serif";
  ctx.fillText(`Image ${index}`, PLACEHOLDER_IMAGE_SIZE / 2, PLACEHOLDER_IMAGE_SIZE * 0.58);

  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) =>
        blob
          ? resolve(blob)
          : reject(new Error("Failed to render placeholder image")),
      "image/png",
    );
  });
}
