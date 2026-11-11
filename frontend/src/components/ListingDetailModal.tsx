import { useState } from "react";
import { X, ExternalLink, FileJson, LayoutGrid, Package } from "lucide-react";
import Lightbox from "./Lightbox";
import { formatPrice, formatListingDateTime } from "../utils/listingDisplay";

interface ListingDetailModalProps {
  sku: string;
  data: unknown;
  loading: boolean;
  onClose: () => void;
}

interface NormalizedListing {
  sku: string;
  title: string;
  descriptionHtml: string;
  imageUrls: string[];
  aspects: [string, string][];
  condition: string;
  price: string;
  currency: string;
  quantity: number | null;
  format: string;
  marketplaceId: string;
  listingDuration: string;
  categoryId: string;
  merchantLocationKey: string;
  fulfillmentPolicyId: string;
  paymentPolicyId: string;
  returnPolicyId: string;
  weight: string;
  dimensions: string;
  createdDateTime: string;
  ebayListingId: string;
  textModel: string;
  imageModel: string;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : value == null ? "" : String(value);
}

function formatCondition(raw: string): string {
  if (!raw) return "";
  return raw
    .replace(/_/g, " ")
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function normalizeListing(data: unknown, fallbackSku: string): NormalizedListing {
  const root = asRecord(data);
  const inventoryItem = asRecord(root.inventoryItem);
  const product = asRecord(inventoryItem.product);
  const availability = asRecord(inventoryItem.availability);
  const shipTo = asRecord(availability.shipToLocationAvailability);
  const pws = asRecord(inventoryItem.packageWeightAndSize);
  const weight = asRecord(pws.weight);
  const dims = asRecord(pws.dimensions);
  const offer = asRecord(root.offer);
  const pricing = asRecord(offer.pricingSummary);
  const price = asRecord(pricing.price);
  const policies = asRecord(offer.listingPolicies);
  const models = asRecord(root.models);

  const aspectsRaw = asRecord(product.aspects);
  const aspects: [string, string][] = Object.entries(aspectsRaw).map(
    ([key, value]) => [
      key,
      Array.isArray(value) ? value.map(asString).join(", ") : asString(value),
    ],
  );

  const imageUrls = Array.isArray(product.imageUrls)
    ? product.imageUrls.map(asString).filter(Boolean)
    : [];

  const quantityRaw =
    typeof offer.quantity === "number"
      ? offer.quantity
      : typeof shipTo.quantity === "number"
        ? shipTo.quantity
        : null;

  const dimParts = [dims.length, dims.width, dims.height]
    .map(asString)
    .filter(Boolean);

  return {
    sku: asString(root.sku) || fallbackSku,
    title: asString(product.title),
    descriptionHtml: asString(product.description).trim(),
    imageUrls,
    aspects,
    condition: formatCondition(asString(inventoryItem.condition)),
    price: asString(price.value),
    currency: asString(price.currency) || "USD",
    quantity: quantityRaw,
    format: asString(offer.format),
    marketplaceId: asString(offer.marketplaceId),
    listingDuration: asString(offer.listingDuration),
    categoryId: asString(offer.categoryId),
    merchantLocationKey: asString(offer.merchantLocationKey),
    fulfillmentPolicyId: asString(policies.fulfillmentPolicyId),
    paymentPolicyId: asString(policies.paymentPolicyId),
    returnPolicyId: asString(policies.returnPolicyId),
    weight: weight.value
      ? `${asString(weight.value)} ${asString(weight.unit).toLowerCase()}`
      : "",
    dimensions: dimParts.length
      ? `${dimParts.join(" × ")} ${asString(dims.unit).toLowerCase()}`
      : "",
    createdDateTime: asString(root.createdDateTime),
    ebayListingId: asString(root.ebayListingId).trim(),
    textModel: asString(models.text_model),
    imageModel: asString(models.image_model),
  };
}

function MetaRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
  if (!value) return null;
  return (
    <div className="flex items-baseline justify-between gap-4 py-1.5">
      <span className="shrink-0 text-sm text-text-muted">{label}</span>
      <span
        className={`truncate text-right text-sm font-medium text-text-primary ${mono ? "font-mono text-xs" : ""}`}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="mb-3 border-b border-border-default pb-2 text-base font-semibold text-text-primary">
      {children}
    </h3>
  );
}

export default function ListingDetailModal({
  sku,
  data,
  loading,
  onClose,
}: ListingDetailModalProps) {
  const [showJson, setShowJson] = useState(false);
  const [heroIndex, setHeroIndex] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  const listing = data ? normalizeListing(data, sku) : null;
  const images = listing?.imageUrls ?? [];
  const safeHero = images.length ? heroIndex % images.length : 0;
  const ebayUrl = listing?.ebayListingId
    ? `https://www.ebay.com/itm/${listing.ebayListingId}`
    : "";

  return (
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60 p-4"
      onClick={onClose}
    >
      <div
        className="flex max-h-[92vh] w-full max-w-5xl flex-col overflow-hidden rounded-xl bg-surface-panel shadow-2xl animate-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Top bar */}
        <div className="flex items-center justify-between gap-3 border-b border-border-default px-5 py-3">
          <div className="flex min-w-0 items-center gap-2">
            <span className="rounded-md bg-surface-muted px-2.5 py-1 font-mono text-xs font-semibold text-text-primary">
              {sku}
            </span>
            {listing?.ebayListingId && (
              <span className="rounded-md bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
                Live on eBay
              </span>
            )}
          </div>
          <button
            type="button"
            aria-label="Close"
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-none bg-surface-muted text-xl text-text-muted transition-all hover:rotate-90 hover:bg-surface-hover hover:text-text-primary"
            onClick={onClose}
          >
            <X size={18} />
          </button>
        </div>

        {/* Body */}
        {loading ? (
          <div className="flex flex-col items-center justify-center gap-4 py-16">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-border-default border-t-primary" />
            <p className="text-text-muted">Loading listing details...</p>
          </div>
        ) : !listing ? (
          <div className="p-10 text-center text-danger">
            Failed to load listing details
          </div>
        ) : showJson ? (
          <div className="flex-1 overflow-auto p-4">
            <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-lg border border-border-default bg-surface-muted p-4 font-mono text-sm text-text-primary">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        ) : (
          <div className="flex-1 overflow-y-auto">
            {/* Product layout */}
            <div className="grid gap-6 p-5 md:grid-cols-2">
              {/* Gallery */}
              <div className="flex min-w-0 flex-col gap-3">
                <button
                  type="button"
                  className="relative aspect-square w-full cursor-zoom-in overflow-hidden rounded-lg border border-border-default bg-surface-muted"
                  onClick={() => images.length && setLightboxOpen(true)}
                  aria-label="Open image viewer"
                >
                  {images.length > 0 ? (
                    <img
                      src={images[safeHero]}
                      alt={listing.title}
                      className="h-full w-full object-contain"
                    />
                  ) : (
                    <span className="flex h-full items-center justify-center text-sm text-text-muted">
                      No images
                    </span>
                  )}
                  {images.length > 0 && (
                    <span className="absolute bottom-2 right-2 rounded-md bg-black/55 px-2 py-0.5 text-xs font-medium text-white">
                      {safeHero + 1} / {images.length}
                    </span>
                  )}
                </button>
                {images.length > 1 && (
                  <div className="flex gap-2 overflow-x-auto pb-1">
                    {images.map((url, i) => (
                      <button
                        key={i}
                        type="button"
                        aria-label={`Show image ${i + 1}`}
                        className={`h-16 w-16 shrink-0 overflow-hidden rounded-md border bg-surface-muted transition-shadow ${
                          i === safeHero
                            ? "border-primary ring-2 ring-primary/40"
                            : "border-border-default hover:ring-2 hover:ring-primary/25"
                        }`}
                        onClick={() => setHeroIndex(i)}
                      >
                        <img
                          src={url}
                          alt=""
                          className="h-full w-full object-cover"
                        />
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Buy box */}
              <div className="flex min-w-0 flex-col gap-4">
                <div>
                  {listing.condition && (
                    <span className="mb-2 inline-block rounded-md bg-surface-muted px-2 py-0.5 text-xs font-semibold uppercase tracking-wide text-text-secondary">
                      Condition: {listing.condition}
                    </span>
                  )}
                  <h2 className="text-xl font-bold leading-snug text-text-primary md:text-2xl">
                    {listing.title || "Untitled listing"}
                  </h2>
                </div>

                <div className="rounded-xl border border-border-default bg-surface-muted p-4">
                  <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
                    <span className="text-3xl font-bold text-text-primary">
                      {formatPrice(listing.price, listing.currency)}
                    </span>
                    {listing.format && (
                      <span className="text-sm text-text-muted">
                        {listing.format === "FIXED_PRICE"
                          ? "Buy It Now"
                          : listing.format}
                      </span>
                    )}
                  </div>
                  <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-text-secondary">
                    {listing.quantity != null && (
                      <span>
                        <strong className="text-text-primary">
                          {listing.quantity}
                        </strong>{" "}
                        available
                      </span>
                    )}
                    {listing.listingDuration && (
                      <span>
                        Duration:{" "}
                        <strong className="text-text-primary">
                          {listing.listingDuration === "GTC"
                            ? "Good 'Til Cancelled"
                            : listing.listingDuration}
                        </strong>
                      </span>
                    )}
                  </div>
                  {ebayUrl && (
                    <a
                      href={ebayUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white no-underline transition-opacity hover:opacity-90"
                    >
                      View on eBay <ExternalLink size={15} />
                    </a>
                  )}
                </div>

                <div className="divide-y divide-border-default rounded-xl border border-border-default px-4 py-1">
                  <MetaRow label="SKU" value={listing.sku} mono />
                  <MetaRow label="Category ID" value={listing.categoryId} mono />
                  <MetaRow label="Marketplace" value={listing.marketplaceId} />
                  <MetaRow
                    label="Location"
                    value={listing.merchantLocationKey}
                  />
                  <MetaRow
                    label="Created"
                    value={
                      listing.createdDateTime
                        ? formatListingDateTime(listing.createdDateTime)
                        : ""
                    }
                  />
                  {listing.ebayListingId && (
                    <MetaRow
                      label="eBay Item ID"
                      value={listing.ebayListingId}
                      mono
                    />
                  )}
                </div>
              </div>
            </div>

            {/* Sections */}
            <div className="flex flex-col gap-6 px-5 pb-5">
              {listing.aspects.length > 0 && (
                <section>
                  <SectionHeading>Item specifics</SectionHeading>
                  <dl className="grid grid-cols-1 gap-x-8 gap-y-1 sm:grid-cols-2">
                    {listing.aspects.map(([key, value]) => (
                      <div
                        key={key}
                        className="flex items-baseline justify-between gap-4 border-b border-border-default/50 py-1.5"
                      >
                        <dt className="shrink-0 text-sm text-text-muted">
                          {key}
                        </dt>
                        <dd className="text-right text-sm font-medium text-text-primary">
                          {value}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </section>
              )}

              {listing.descriptionHtml && (
                <section>
                  <SectionHeading>About this item</SectionHeading>
                  <div
                    className="rounded-lg border border-border-default bg-surface-muted p-4 text-sm leading-relaxed text-text-primary [&_a]:text-primary [&_a]:underline [&_h1]:mb-2 [&_h1]:text-base [&_h1]:font-semibold [&_h2]:mb-2 [&_h2]:text-sm [&_h2]:font-semibold [&_img]:h-auto [&_img]:max-w-full [&_li]:my-0.5 [&_ol]:my-2 [&_ol]:list-decimal [&_ol]:pl-5 [&_p]:my-2 [&_p]:first:mt-0 [&_table]:my-2 [&_table]:max-w-full [&_td]:border [&_td]:border-border-default [&_td]:p-1.5 [&_ul]:my-2 [&_ul]:list-disc [&_ul]:pl-5"
                    dangerouslySetInnerHTML={{
                      __html: listing.descriptionHtml,
                    }}
                  />
                </section>
              )}

              {(listing.weight || listing.dimensions) && (
                <section>
                  <SectionHeading>
                    <span className="inline-flex items-center gap-2">
                      <Package size={16} /> Shipping & packaging
                    </span>
                  </SectionHeading>
                  <div className="flex flex-wrap gap-3">
                    {listing.weight && (
                      <div className="rounded-lg border border-border-default bg-surface-muted px-4 py-2.5">
                        <div className="text-xs text-text-muted">Weight</div>
                        <div className="text-sm font-semibold text-text-primary">
                          {listing.weight}
                        </div>
                      </div>
                    )}
                    {listing.dimensions && (
                      <div className="rounded-lg border border-border-default bg-surface-muted px-4 py-2.5">
                        <div className="text-xs text-text-muted">
                          Package dimensions
                        </div>
                        <div className="text-sm font-semibold text-text-primary">
                          {listing.dimensions}
                        </div>
                      </div>
                    )}
                  </div>
                </section>
              )}

              <section>
                <SectionHeading>eBay details</SectionHeading>
                <div className="grid grid-cols-1 gap-x-8 sm:grid-cols-2">
                  <MetaRow
                    label="Fulfillment policy"
                    value={listing.fulfillmentPolicyId}
                    mono
                  />
                  <MetaRow
                    label="Payment policy"
                    value={listing.paymentPolicyId}
                    mono
                  />
                  <MetaRow
                    label="Return policy"
                    value={listing.returnPolicyId}
                    mono
                  />
                  <MetaRow
                    label="Listing format"
                    value={listing.format}
                  />
                  <MetaRow label="Text model" value={listing.textModel} mono />
                  <MetaRow
                    label="Image model"
                    value={listing.imageModel}
                    mono
                  />
                </div>
              </section>
            </div>
          </div>
        )}

        {/* Footer */}
        {!loading && listing && (
          <div className="flex items-center justify-between gap-3 border-t border-border-default px-5 py-3">
            <button
              type="button"
              className="inline-flex items-center gap-2 rounded-lg border border-border-default bg-surface-panel px-4 py-2 text-sm font-semibold text-text-primary shadow-sm transition-colors hover:bg-surface-hover"
              onClick={() => setShowJson((v) => !v)}
            >
              {showJson ? (
                <>
                  <LayoutGrid size={15} /> Back to listing
                </>
              ) : (
                <>
                  <FileJson size={15} /> View JSON
                </>
              )}
            </button>
            <button
              type="button"
              className="rounded-lg border border-border-default bg-surface-panel px-4 py-2 text-sm text-text-primary transition-colors hover:bg-surface-hover"
              onClick={onClose}
            >
              Close
            </button>
          </div>
        )}
      </div>

      {lightboxOpen && images.length > 0 && (
        <Lightbox
          photos={images}
          currentIndex={safeHero}
          onClose={() => setLightboxOpen(false)}
          onNavigate={(dir) =>
            setHeroIndex((i) =>
              dir === "next"
                ? (i + 1) % images.length
                : (i - 1 + images.length) % images.length,
            )
          }
        />
      )}
    </div>
  );
}
