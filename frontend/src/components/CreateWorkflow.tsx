import { useEffect, useState } from "react";
import { motion } from "motion/react";
import PhotoGallery from "./PhotoGallery";
import ImageUploadModal from "./ImageUploadModal";
import type { PendingImage } from "./ImageUploadModal";
import MessageBarInput from "./MessageBarInput";
import Lightbox from "./Lightbox";
import StepCard from "./StepCard";
import ImageCanvas from "./ImageCanvas";
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import type { DropResult } from "@hello-pangea/dnd";
import { btnPill, btnPillLg, btnPillSm } from "../styles/buttonPill";
import {
  DEFAULT_CHAT_CONTEXT,
  getChatContextInputPlaceholder,
} from "../constants/chatContextModes";
import {
  formatPrice,
  formatListingDateTime,
  formatCategoryShort,
} from "../utils/listingDisplay";
import {
  CREATE_STEP_TITLES,
  initialCreateSteps,
  type CreateStepId,
  type CreateStepsState,
} from "../utils/createPipeline";
import {
  UPLOAD_STEP_TITLES,
  type UploadStepsState,
} from "../utils/uploadPipeline";

interface AutoSaveStatus {
  title: "idle" | "saving" | "saved";
  description: "idle" | "saving" | "saved";
}

interface UploadResult {
  listingId?: string;
  ebayId?: string;
  href?: string;
}

interface ListingData {
  sku?: string;
  offer?: {
    pricingSummary?: { price?: { value?: string | number } };
    categoryId?: string;
  };
  inventoryItem?: {
    product?: { imageUrls?: string[]; title?: string; description?: string };
  };
  createdDateTime?: string;
  [key: string]: unknown;
}

interface SourceListing {
  title?: string;
  description?: string;
  price?: string | number;
  currency?: string;
  categoryId?: string | number;
  itemCreationDate?: string;
  [key: string]: unknown;
}

interface CreateWorkflowProps {
  listingId: string;
  listingLinkSubmitted?: boolean;
  sidebarCollapsed?: boolean;
  photos?: string[];
  categories?: Record<string, string>;
  editableCategories?: Record<string, string>;
  listing?: SourceListing | null;
  currentSku?: string | null;
  skippedPhotos?: Set<string>;
  generatedImages?: string[];
  loading?: boolean;
  isConfirming?: boolean;
  isCreatingListing?: boolean;
  listingData?: ListingData | null;
  editableTitle?: string;
  editableDescription?: string;
  uploadResult?: UploadResult | null;
  isEditorOpen?: boolean;
  /** Per-step waiting state for the Create workflow (ADR 0003), owned by the parent. */
  createSteps?: CreateStepsState;
  /** Retries the failed Create step (re-runs its phase without restarting completed steps). */
  onRetryCreateStep?: (id: CreateStepId) => void;
  /** Per-step waiting state for the Upload-to-eBay flow (ADR 0003), owned by the parent. Null until the first upload run. */
  uploadSteps?: UploadStepsState | null;
  /** Retries a failed upload-to-eBay run (re-runs the whole upload request). */
  onRetryUpload?: () => void;
  uploadingSkus?: Set<string>;
  isTrimmingTitle?: boolean;
  autoSaveStatus?: AutoSaveStatus;
  isGeneratingText?: boolean;
  textGenStatus?: string;
  onCancelTextGen?: () => void;
  onListingIdChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  onChatSubmit: (prompt: string, context: string) => void;
  onCategoryChange?: (photoUrl: string, category: string) => void;
  onSkipPhoto?: (url: string) => void;
  onConfirmCategories?: () => void;
  onDragEnd: (result: DropResult) => void;
  onRemoveFromListing?: (index: number) => void;
  onAddToListing?: (url: string) => void;
  onAddToOriginalPhotos?: (urls: string[]) => void;
  onEditableTitleChange?: (value: string) => void;
  onTrimTitle?: () => void;
  onEditableDescriptionChange?: (value: string) => void;
  onUploadToEbay?: (sku: string, data?: ListingData | null) => void;
  onEditorToggle?: () => void;
  useRealEbayUpload?: boolean;
  onUseRealEbayUploadChange?: ((checked: boolean) => void) | null;
  onPhotoClick?: (index: number) => void;
  onCloseLightbox?: () => void;
  onNavigateLightbox?: (direction: "prev" | "next") => void;
  lightboxOpen?: boolean;
  lightboxIndex?: number;
  selectedImagesForRegen?: number[];
  onImageSelection?: (index: number) => void;
  onSelectAllImages?: () => void;
  onClearImageSelection?: () => void;
  classifyImagesEnabled?: boolean;
  testUserEnabled?: boolean;
  onUsePlaceholderImages?: (photoUrls: string[]) => void;
  photoSelectionActive?: boolean;
  pendingPhotoPrompt?: string;
  pendingImagePromptModifier?: string;
  onClearImagePromptModifier?: () => void;
  onConfirmPhotoRegeneration?: () => void;
  onCancelPhotoRegeneration?: () => void;
  onAddToGeneratedImages?: (url: string) => void;
  onDeleteGeneratedImages?: (indices: number[]) => void;
  onRemoveBackgroundGenerated?: (urls: string[]) => void;
  onDeleteOriginalPhotos?: (indices: number[]) => void;
  onRemoveBackgroundOriginal?: (urls: string[]) => void;
  autoBackgroundRemovalEnabled?: boolean;
  bgRemovedPhotos?: Record<string, string>;
  onError?: (message: string) => void;
  promptModifier?: string;
  customPrompt?: string;
  error?: string | null;
  isRegenerating?: boolean;
  isTrimming?: boolean;
  isAddingNewVersions?: boolean;
  onPromptModifierChange?: (value: string) => void;
  onRegenerateImages?: (prompt?: string) => void | Promise<void>;
  onTrimSelected?: () => void | Promise<void>;
  onAddNewVersions?: () => void | Promise<void>;
  onCustomPromptChange?: (value: string) => void;
}

const IDLE_CREATE_STEPS = initialCreateSteps();

function CreateWorkflow({
  listingId,
  listingLinkSubmitted = false,
  sidebarCollapsed = false,
  photos,
  categories,
  editableCategories,
  listing,
  currentSku,
  skippedPhotos,
  generatedImages,
  loading,
  isConfirming,
  isCreatingListing,
  listingData,
  editableTitle,
  editableDescription,
  uploadResult,
  isEditorOpen,
  createSteps,
  onRetryCreateStep,
  uploadSteps = null,
  onRetryUpload,
  uploadingSkus,
  isTrimmingTitle,
  autoSaveStatus = { title: "idle", description: "idle" },
  isGeneratingText = false,
  textGenStatus = "writing",
  onCancelTextGen = () => {},
  onListingIdChange,
  onSubmit,
  onChatSubmit,
  onCategoryChange,
  onSkipPhoto,
  onConfirmCategories,
  onDragEnd,
  onRemoveFromListing,
  onAddToListing,
  onAddToOriginalPhotos,
  onEditableTitleChange,
  onTrimTitle,
  onEditableDescriptionChange,
  onUploadToEbay,
  onEditorToggle,
  useRealEbayUpload,
  onUseRealEbayUploadChange,
  onPhotoClick,
  onCloseLightbox,
  onNavigateLightbox,
  lightboxOpen,
  lightboxIndex,
  selectedImagesForRegen = [],
  onImageSelection,
  onSelectAllImages,
  onClearImageSelection,
  classifyImagesEnabled = true,
  testUserEnabled = false,
  onUsePlaceholderImages,
  photoSelectionActive = false,
  pendingPhotoPrompt = "",
  pendingImagePromptModifier = "",
  onClearImagePromptModifier,
  onConfirmPhotoRegeneration,
  onCancelPhotoRegeneration,
  onAddToGeneratedImages,
  onDeleteGeneratedImages,
  onRemoveBackgroundGenerated,
  onDeleteOriginalPhotos,
  onRemoveBackgroundOriginal,
  autoBackgroundRemovalEnabled = false,
  bgRemovedPhotos,
  onError = () => {},
}: CreateWorkflowProps) {
  const [descriptionEditMode, setDescriptionEditMode] = useState(false);
  const [chatContext, setChatContext] = useState(DEFAULT_CHAT_CONTEXT);
  const [showOriginal, setShowOriginal] = useState(false);
  const [showMetadata, setShowMetadata] = useState(false);
  const [genSelectMode, setGenSelectMode] = useState(false);
  const [genSelectedPhotos, setGenSelectedPhotos] = useState(new Set<number>());
  const [genBulkDropdownOpen, setGenBulkDropdownOpen] = useState(false);
  const [showGenUploadModal, setShowGenUploadModal] = useState(false);

  useEffect(() => {
    if (!listingLinkSubmitted) {
      setChatContext(DEFAULT_CHAT_CONTEXT);
      setShowOriginal(false);
      setShowMetadata(false);
    }
  }, [listingLinkSubmitted]);

  useEffect(() => {
    if (!isEditorOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" && onEditorToggle) {
        onEditorToggle();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isEditorOpen, onEditorToggle]);

  const imageSelectionActive = chatContext === "photos" && (generatedImages?.length ?? 0) > 0;

  useEffect(() => {
    if (!genBulkDropdownOpen) return;
    const close = () => setGenBulkDropdownOpen(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [genBulkDropdownOpen]);

  const toggleGenSelectMode = () => {
    setGenSelectMode((prev) => {
      if (prev) {
        setGenSelectedPhotos(new Set());
        setGenBulkDropdownOpen(false);
      }
      return !prev;
    });
  };

  const toggleGenPhotoSelection = (index: number) => {
    setGenSelectedPhotos((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  useEffect(() => {
    if (imageSelectionActive) {
      onSelectAllImages?.();
    } else {
      onClearImageSelection?.();
    }
  }, [imageSelectionActive]);

  const [expandedPromptIndex, setExpandedPromptIndex] = useState<number | null>(null);

  // Every Create step owns its waiting state in a StepCard (ADR 0003). The
  // state itself is parent-owned and passed down; skipped optional steps
  // (categorize, bg removal) stay pending and render disabled.
  const steps = createSteps ?? IDLE_CREATE_STEPS;
  const createWorkflowActive = (loading ?? false) || listingLinkSubmitted;
  const categorizeSkipped = !classifyImagesEnabled;
  const bgRemovalSkipped = !autoBackgroundRemovalEnabled;
  const retryCreateStep = (id: CreateStepId) =>
    onRetryCreateStep ? () => onRetryCreateStep(id) : undefined;

  const sidebarLeft = sidebarCollapsed ? "4.25rem" : "15rem";
  const barWrapperClassName = listingLinkSubmitted
    ? "pointer-events-none fixed bottom-0 right-0 z-50 flex w-auto flex-col items-center justify-center bg-transparent px-6 py-4 md:px-8 transition-[left,padding] duration-500 ease-in-out"
    : "flex w-full flex-col items-center mb-[15%] min-h-[min(42vh,320px)] max-w-4xl self-center justify-center border-t border-transparent bg-transparent backdrop-blur-none transition-[margin,padding,min-height,background-color,border-color,backdrop-filter] duration-500 ease-in-out";

  return (
    <>
      <motion.div
        layout
        style={
          listingLinkSubmitted
            ? { left: sidebarLeft, right: 0 }
            : undefined
        }
        transition={{ type: "spring", stiffness: 260, damping: 30 }}
        className={barWrapperClassName}
      >
        <div
          className={`w-full overflow-hidden transition-[max-height,opacity,margin] duration-500 ease-in-out ${
            listingLinkSubmitted
              ? "pointer-events-none mb-0 max-h-0 opacity-0"
              : "mb-4 pb-1 opacity-100 md:mb-4"
          }`}
          aria-hidden={listingLinkSubmitted}
        >
          <h1 className="text-center text-6xl font-light leading-snug tracking-tight text-text-primary md:text-6xl">
            Reimagine Any Listing
          </h1>
        </div>
        <form
          onSubmit={(e) => {
            if (!listingLinkSubmitted) {
              onSubmit(e);
            } else {
              e.preventDefault();
              const prompt = listingId.trim();
              if (!prompt) return;
              onListingIdChange("");
              onChatSubmit(prompt, chatContext);
            }
          }}
          className={`mx-auto flex w-full max-w-[min(42rem,100%)] transition-[margin] duration-500 ease-in-out ${
            listingLinkSubmitted
              ? "pointer-events-auto mt-0"
              : "mt-12 md:mt-16"
          }`}
        >
          <MessageBarInput
            fullWidth
            value={listingId}
            onChange={onListingIdChange}
            placeholder={
              listingLinkSubmitted
                ? getChatContextInputPlaceholder(chatContext)
                : "Paste any eBay link"
            }
            disabled={loading}
            loading={loading}
            aria-label="eBay listing URL or ID"
            showChatContextSelector={listingLinkSubmitted}
            chatContext={chatContext}
            onChatContextChange={setChatContext}
          />
        </form>
      </motion.div>

      {loading && (photos?.length ?? 0) === 0 && (
        <div className="flex flex-col items-center justify-center gap-4 py-12">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-border-default border-t-primary" />
          <p className="text-text-muted">Fetching listing data...</p>
        </div>
      )}

      {/* Steps 1–3 run inside the single /api/photos request; their cards
          report the stream's step messages. */}
      {createWorkflowActive && (
        <div className="mt-4 flex flex-col gap-3">
          <StepCard
            title={CREATE_STEP_TITLES.fetch}
            status={steps.fetch.status}
            statusText={steps.fetch.statusText}
            error={steps.fetch.error}
            onRetry={retryCreateStep("fetch")}
          />
          <StepCard
            title={CREATE_STEP_TITLES.json}
            status={steps.json.status}
            statusText={steps.json.statusText}
            error={steps.json.error}
            onRetry={retryCreateStep("json")}
          />
          <StepCard
            title={CREATE_STEP_TITLES.categorize}
            status={steps.categorize.status}
            statusText={
              categorizeSkipped ? "Skipped in settings" : steps.categorize.statusText
            }
            error={steps.categorize.error}
            onRetry={retryCreateStep("categorize")}
            disabled={categorizeSkipped}
          />
        </div>
      )}

      {/* Step 6 narrates the streamed text generation; the stream keeps
          writing into the title/description inputs as before. */}
      {createWorkflowActive && (
        <StepCard
          title={CREATE_STEP_TITLES.textGen}
          status={steps.textGen.status}
          statusText={steps.textGen.statusText}
          error={steps.textGen.error}
          onRetry={retryCreateStep("textGen")}
        >
      {listing && (isGeneratingText || editableTitle !== "") && (
        <div>
          {/* Metadata row */}
          <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
            <div className="flex flex-wrap items-center gap-1.5">
              {currentSku && (
                <span className="rounded-md border border-border-default px-2 py-0.5 font-mono text-xs text-text-muted">
                  {currentSku}
                </span>
              )}
              {listing.itemCreationDate && (
                <span className="rounded-md border border-border-default px-2 py-0.5 text-xs text-text-muted">
                  {formatListingDateTime(String(listing.itemCreationDate))}
                </span>
              )}
              <span className="rounded-md border border-border-default px-2 py-0.5 text-xs text-text-muted">
                {generatedImages?.length ?? 0}{" "}
                {(generatedImages?.length ?? 0) === 1 ? "image" : "images"}
              </span>
              {listing.categoryId != null && (
                <span className="rounded-md border border-border-default px-2 py-0.5 text-xs text-text-muted">
                  Cat {formatCategoryShort(listing.categoryId)}
                </span>
              )}
            </div>
            <div className="shrink-0 text-xl font-bold text-text-primary">
              {formatPrice(listing.price, listing.currency)}
            </div>
          </div>
          <div className="space-y-4">
            <div className="flex flex-col gap-2 border-b border-border-default pb-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <strong className="text-primary">Title:</strong>
                  {autoSaveStatus.title === "saving" && (
                    <span className="ml-2 text-xs text-text-muted">Saving...</span>
                  )}
                  {autoSaveStatus.title === "saved" && (
                    <span className="ml-2 text-xs text-success">Saved</span>
                  )}
                  {isGeneratingText && (
                    <button
                      type="button"
                      className="rounded-md border border-border-default px-2 py-0.5 text-xs text-text-muted hover:border-red-400 hover:text-red-600"
                      onClick={onCancelTextGen}
                    >
                      Cancel
                    </button>
                  )}
                </div>
                <span
                  className={`rounded-full px-2.5 py-1 text-sm font-semibold ${
                    (editableTitle?.length ?? 0) > 80
                      ? "bg-red-100 text-red-700"
                      : (editableTitle?.length ?? 0) >= 73 &&
                          (editableTitle?.length ?? 0) <= 80
                        ? "bg-green-100 text-green-700"
                        : "bg-primary/10 text-primary"
                  }`}
                >
                  {editableTitle?.length ?? 0} / 80
                  {(editableTitle?.length ?? 0) > 80 &&
                    ` (${(editableTitle?.length ?? 0) - 80} over)`}
                </span>
              </div>
              <input
                type="text"
                className={`w-full rounded-lg border-2 px-3 py-2.5 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20 ${
                  isGeneratingText
                    ? "cursor-not-allowed border-border-default bg-surface-muted text-text-muted opacity-60"
                    : (editableTitle?.length ?? 0) > 80
                      ? "border-red-500 bg-red-50 focus:border-red-500 focus:ring-red-500/20"
                      : "border-border-default bg-surface-panel text-text-primary focus:border-primary"
                }`}
                value={editableTitle}
                onChange={(e) => onEditableTitleChange?.(e.target.value)}
                placeholder="Listing title..."
                disabled={isGeneratingText}
              />
              {isGeneratingText && (
                <p className="animate-pulse text-xs text-text-muted">
                  {textGenStatus === "nudging"
                    ? "Adjusting title length..."
                    : "AI is writing..."}
                </p>
              )}
              {(editableTitle?.length ?? 0) > 80 && (
                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  Title exceeds 80 characters. Edit manually or use AI to trim it.
                </div>
              )}
              {!isGeneratingText && (editableTitle?.length ?? 0) > 80 && (
                <button
                  type="button"
                  className={btnPillSm}
                  onClick={onTrimTitle}
                  disabled={isTrimmingTitle}
                >
                  {isTrimmingTitle ? "Trimming..." : "AI Trim Title"}
                </button>
              )}
            </div>
            <div className="border-b border-border-default pb-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <strong className="text-primary">Description:</strong>
                  {autoSaveStatus.description === "saving" && (
                    <span className="ml-2 text-xs text-text-muted">Saving...</span>
                  )}
                  {autoSaveStatus.description === "saved" && (
                    <span className="ml-2 text-xs text-success">Saved</span>
                  )}
                </div>
                {!isGeneratingText && (
                  <button
                    type="button"
                    className="rounded-lg border-2 border-border-default bg-surface-panel px-3 py-1.5 text-sm font-semibold text-text-primary transition-colors hover:border-primary hover:text-primary"
                    onClick={() => setDescriptionEditMode((v) => !v)}
                  >
                    {descriptionEditMode ? "Preview HTML" : "Edit HTML"}
                  </button>
                )}
              </div>
              {descriptionEditMode ? (
                <textarea
                  className={`mt-2 min-h-[200px] w-full resize-y rounded-lg border-2 p-3 font-mono text-sm transition-colors focus:outline-none ${
                    isGeneratingText
                      ? "cursor-not-allowed border-border-default bg-surface-muted text-text-muted opacity-60"
                      : "border-border-default bg-surface-panel text-text-primary focus:border-primary"
                  }`}
                  value={editableDescription}
                  onChange={(e) => onEditableDescriptionChange?.(e.target.value)}
                  placeholder="HTML description..."
                  rows={12}
                  spellCheck={false}
                  disabled={isGeneratingText}
                />
              ) : (
                <div
                  className="listing-description-html mt-2 rounded-md bg-surface-muted p-3 text-text-muted [&_a]:text-primary [&_a]:underline [&_li]:my-0.5 [&_ol]:list-decimal [&_ol]:pl-6 [&_p]:my-2 [&_p:first-child]:mt-0 [&_ul]:list-disc [&_ul]:pl-6"
                  dangerouslySetInnerHTML={{
                    __html:
                      (editableDescription && editableDescription.trim()) ||
                      '<p class="text-text-muted italic">N/A</p>',
                  }}
                />
              )}
            </div>
            {/* Original title/description disclosure */}
            <div>
              <button
                type="button"
                className="flex items-center gap-1 text-sm text-text-muted hover:text-text-primary"
                onClick={() => setShowOriginal((v) => !v)}
              >
                <span>{showOriginal ? "▼" : "▶"}</span>
                <span>
                  {showOriginal
                    ? "Hide original title and description"
                    : "View original title and description"}
                </span>
              </button>
              {showOriginal && (
                <div className="mt-3 space-y-2">
                  <p className="text-sm font-semibold text-text-primary">
                    {listing.title || "No title"}
                  </p>
                  {listing.description &&
                    String(listing.description).trim() !== "" &&
                    listing.description !== "No description available" && (
                      <div className="max-h-[calc(1.625em*6)] overflow-y-auto overscroll-contain rounded-lg border border-border-default bg-surface-muted p-3">
                        <p className="whitespace-pre-wrap text-sm leading-relaxed text-text-primary">
                          {String(listing.description).trim()}
                        </p>
                      </div>
                    )}
                </div>
              )}
            </div>
          </div>

          {(listing || listingData) && (
            <>
              {/* Listing details disclosure */}
              <div className="mt-4">
                <button
                  type="button"
                  className="flex items-center gap-1 text-sm text-text-muted hover:text-text-primary"
                  onClick={() => setShowMetadata((v) => !v)}
                >
                  <span>{showMetadata ? "▼" : "▶"}</span>
                  <span>
                    {showMetadata ? "Hide listing details" : "View listing details"}
                  </span>
                </button>
                {showMetadata && (
                  <div className="mt-3 space-y-4">
                    <div className="border-b border-border-default pb-4">
                      <strong className="text-primary">SKU:</strong>{" "}
                      {listingData?.sku || currentSku || "N/A"}
                    </div>
                    <div className="border-b border-border-default pb-4">
                      <strong className="text-primary">Price:</strong> $
                      {listingData?.offer?.pricingSummary?.price?.value || listing?.price || "N/A"}
                    </div>
                    <div className="border-b border-border-default pb-4">
                      <strong className="text-primary">Category ID:</strong>{" "}
                      {listingData?.offer?.categoryId || listing?.categoryId || "N/A"}
                    </div>
                    <div className="border-b border-border-default pb-4">
                      <strong className="text-primary">
                        Images (
                        {listingData?.inventoryItem?.product?.imageUrls?.length || 0}):
                      </strong>
                      <div className="mt-2 space-y-2">
                        {listingData?.inventoryItem?.product?.imageUrls?.map(
                          (url, idx) => (
                            <div
                              key={idx}
                              className="rounded-md bg-surface-muted p-2 text-sm text-text-muted break-all"
                            >
                              {idx + 1}. {url}
                            </div>
                          ),
                        ) || <span className="text-sm text-text-muted">Not yet generated</span>}
                      </div>
                    </div>
                    <div className="border-b border-border-default pb-4">
                      <strong className="text-primary">Created:</strong>{" "}
                      {listingData?.createdDateTime || listing?.itemCreationDate || "N/A"}
                    </div>
                  </div>
                )}
              </div>

              {uploadResult && (
                <div className="mt-8 rounded-xl bg-linear-to-br from-success to-emerald-600 p-6 text-white">
                  <h3 className="mb-4 text-2xl font-semibold">
                    Upload Successful!
                  </h3>
                  <div className="flex flex-col gap-3">
                    {uploadResult.listingId && (
                      <div>
                        <strong>Listing ID:</strong>{" "}
                        <a
                          href={`https://www.ebay.com/itm/${uploadResult.listingId}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-semibold underline hover:no-underline"
                        >
                          {uploadResult.listingId}
                        </a>
                      </div>
                    )}
                    {uploadResult.ebayId && (
                      <div>
                        <strong>eBay ID:</strong> {uploadResult.ebayId}
                      </div>
                    )}
                    {uploadResult.href && (
                      <div>
                        <strong>Listing URL:</strong>{" "}
                        <a
                          href={uploadResult.href}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="font-semibold underline hover:no-underline"
                        >
                          View on eBay
                        </a>
                      </div>
                    )}
                    <div>
                      <strong>Status:</strong> Listing is now live on eBay!
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
        </StepCard>
      )}

      {/* Skeleton thumbnails while the listing's photos are being fetched. */}
      {loading && (photos?.length ?? 0) === 0 && (
        <div className="mt-8 rounded-2xl border border-border-default bg-surface-panel p-6">
          <div className="mb-4 h-7 w-40 animate-pulse rounded bg-surface-hover" />
          <div className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-4 sm:grid-cols-[repeat(auto-fill,minmax(180px,1fr))] sm:gap-5">
            {Array.from({ length: 8 }).map((_, i) => (
              <div
                key={i}
                className="aspect-square animate-pulse rounded-xl bg-surface-hover"
              />
            ))}
          </div>
        </div>
      )}

      {(photos?.length ?? 0) > 0 && (
        <>
          <PhotoGallery
            photos={photos!}
            editableCategories={editableCategories ?? {}}
            onCategoryChange={onCategoryChange}
            onConfirm={onConfirmCategories}
            isConfirming={isConfirming ?? false}
            onPhotoClick={onPhotoClick}
            skippedPhotos={skippedPhotos}
            onSkipPhoto={onSkipPhoto}
            onAddToOriginalPhotos={onAddToOriginalPhotos}
            onOpenEditor={onEditorToggle}
            onDeletePhotos={onDeleteOriginalPhotos}
            onRemoveBackgrounds={onRemoveBackgroundOriginal}
            showClassification={classifyImagesEnabled}
            hideConfirmButton={autoBackgroundRemovalEnabled}
            testUserEnabled={testUserEnabled}
            onUsePlaceholderImages={onUsePlaceholderImages}
          />
          {pendingImagePromptModifier && !(generatedImages?.length) && (
            <div className="mt-3 flex items-center gap-2 rounded-xl border border-border-default bg-surface-panel px-4 py-2.5">
              <span className="flex-1 text-sm text-text-muted">
                Will generate with:{" "}
                <span className="font-medium text-text-primary">
                  &quot;{pendingImagePromptModifier}&quot;
                </span>
              </span>
              <button
                type="button"
                className="rounded-md px-2 py-1 text-xs text-text-muted hover:bg-surface-muted hover:text-text-primary"
                onClick={onClearImagePromptModifier}
              >
                &times;
              </button>
            </div>
          )}
        </>
      )}

      {/* Step 4 — background removal (optional; disabled when off in
          settings). Wraps the bg-removed photos and the confirm button. */}
      {createWorkflowActive && (
        <StepCard
          title={CREATE_STEP_TITLES.bgRemoval}
          status={steps.bgRemoval.status}
          statusText={
            bgRemovalSkipped ? "Skipped in settings" : steps.bgRemoval.statusText
          }
          progress={steps.bgRemoval.progress}
          error={steps.bgRemoval.error}
          onRetry={retryCreateStep("bgRemoval")}
          disabled={bgRemovalSkipped}
        >
          {autoBackgroundRemovalEnabled && (photos?.length ?? 0) > 0 && (
            <>
            <div className="rounded-lg border border-border-default bg-surface-muted p-4">
              <h3 className="mb-2.5 text-lg text-text-primary">
                Background Removed Photos
              </h3>
              {Object.keys(bgRemovedPhotos || {}).length > 0 && (
                <div className="mt-4 grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-4 sm:grid-cols-[repeat(auto-fill,minmax(180px,1fr))]">
                  {Object.values(bgRemovedPhotos!).map((url, idx) => (
                    <div
                      key={url}
                      className="aspect-square overflow-hidden rounded-xl border border-border-default bg-surface-panel"
                    >
                      <img
                        src={url}
                        alt={`Background removed ${idx + 1}`}
                        className="h-full w-full object-contain"
                        loading="lazy"
                      />
                    </div>
                  ))}
                </div>
              )}
              {Object.keys(bgRemovedPhotos || {}).length === 0 && (
                <p className="mt-2 text-sm text-text-muted">
                  Waiting for photos to load...
                </p>
              )}
            </div>
            <div className="mt-4 flex justify-center">
              <button
                type="button"
                className={btnPillLg}
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onConfirmCategories?.();
                }}
                disabled={isConfirming}
              >
                {isConfirming ? "Generating Images..." : "Confirm Categories"}
              </button>
            </div>
            </>
          )}
        </StepCard>
      )}

      {/* Step 5 — image generation. Determinate "N of M" progress shows in
          the card header; the generated grid lives inside the card. */}
      {createWorkflowActive && (
        <StepCard
          title={CREATE_STEP_TITLES.imageGen}
          status={steps.imageGen.status}
          statusText={steps.imageGen.statusText}
          progress={steps.imageGen.progress}
          error={steps.imageGen.error}
          onRetry={retryCreateStep("imageGen")}
        >
      {(generatedImages?.length ?? 0) > 0 && (
        <div>
          <div className="mb-5 flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-semibold text-text-primary">New Listing Photos</h2>
            <div className="flex flex-wrap items-center gap-2">
              {onEditorToggle && (
                <button type="button" className={btnPill} onClick={onEditorToggle}>
                  Image Editor
                </button>
              )}
              {onAddToGeneratedImages && (
                <button type="button" className={btnPill} onClick={() => setShowGenUploadModal(true)}>
                  Upload Images
                </button>
              )}
              <button
                type="button"
                className={`${btnPill} ${genSelectMode ? "ring-2 ring-inset ring-blue-500" : ""}`}
                onClick={toggleGenSelectMode}
              >
                {genSelectMode ? "Done" : "Select"}
              </button>
              <div className="relative">
                <button
                  type="button"
                  className={btnPill}
                  disabled={!genSelectMode || genSelectedPhotos.size === 0}
                  onClick={(e) => { e.stopPropagation(); setGenBulkDropdownOpen((prev) => !prev); }}
                >
                  Bulk Actions ▾
                </button>
                {genBulkDropdownOpen && (
                  <div className="absolute right-0 top-full z-20 mt-1 min-w-36 rounded-lg border border-border-default bg-surface-panel py-1 shadow-lg">
                    {onRemoveBackgroundGenerated && (
                      <button
                        type="button"
                        className="w-full px-4 py-2 text-left text-sm text-text-primary hover:bg-surface-app"
                        onClick={() => {
                          const urls = Array.from(genSelectedPhotos).map((idx) => generatedImages![idx]);
                          onRemoveBackgroundGenerated(urls);
                          setGenSelectedPhotos(new Set());
                          setGenSelectMode(false);
                          setGenBulkDropdownOpen(false);
                        }}
                      >
                        Remove Background
                      </button>
                    )}
                    {onDeleteGeneratedImages && (
                      <button
                        type="button"
                        className="w-full px-4 py-2 text-left text-sm text-text-primary hover:bg-surface-app"
                        onClick={() => {
                          onDeleteGeneratedImages(Array.from(genSelectedPhotos));
                          setGenSelectedPhotos(new Set());
                          setGenSelectMode(false);
                          setGenBulkDropdownOpen(false);
                        }}
                      >
                        Delete
                      </button>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId="new-listing-photos" direction="horizontal">
              {(provided) => (
                <div
                  className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-4 sm:grid-cols-[repeat(auto-fill,minmax(180px,1fr))] sm:gap-5"
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                >
                  {generatedImages!.map((imageUrl, index) => {
                    const isSelected = selectedImagesForRegen.includes(index);
                    return (
                    <Draggable
                      key={`img-${imageUrl}-${index}`}
                      draggableId={`img-${imageUrl}-${index}`}
                      index={index}
                    >
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          {...provided.dragHandleProps}
                          className="flex flex-col"
                        >
                          <div
                            className={`group relative aspect-square overflow-hidden rounded-xl transition-all ${
                              genSelectMode ? "cursor-pointer" : "cursor-grab active:cursor-grabbing"
                            } ${
                              snapshot.isDragging ? "opacity-80 shadow-lg" : ""
                            } ${imageSelectionActive ? "animate-jiggle" : ""} ${
                              imageSelectionActive && isSelected
                                ? "ring-3 ring-blue-500 ring-offset-2"
                                : ""
                            } ${
                              imageSelectionActive && !isSelected
                                ? "opacity-40"
                                : ""
                            }`}
                            onClick={() => {
                              if (genSelectMode) {
                                toggleGenPhotoSelection(index);
                              } else if (imageSelectionActive && onImageSelection) {
                                onImageSelection(index);
                              }
                            }}
                          >
                            {genSelectMode && genSelectedPhotos.has(index) && (
                              <div className="pointer-events-none absolute inset-0 z-10 rounded-xl ring-4 ring-inset ring-blue-500">
                                <div className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-white">
                                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                                    <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                                  </svg>
                                </div>
                              </div>
                            )}
                            {imageSelectionActive && isSelected && (
                              <div className="pointer-events-none absolute left-1.5 top-1.5 z-20 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white shadow">
                                &#10003;
                              </div>
                            )}
                            <img
                              src={imageUrl}
                              alt={`New listing photo ${index + 1}`}
                              className="pointer-events-none h-full w-full object-cover"
                              loading="lazy"
                              draggable={false}
                            />
                            {!imageSelectionActive && (
                              <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 transition-opacity group-hover:opacity-100">
                                <span className="text-2xl font-bold text-white">
                                  {index + 1}
                                </span>
                              </div>
                            )}
                          </div>
                          {imageSelectionActive && isSelected && pendingPhotoPrompt && (
                            <div className="mt-1">
                              <button
                                type="button"
                                className="flex items-center gap-1 rounded-md px-1.5 py-0.5 text-xs text-text-muted hover:bg-surface-muted"
                                onMouseDown={(e) => e.stopPropagation()}
                                onClick={(e) => {
                                  e.stopPropagation();
                                  setExpandedPromptIndex(expandedPromptIndex === index ? null : index);
                                }}
                              >
                                <span>💬</span>
                                {expandedPromptIndex === index ? (
                                  <span className="max-w-[150px] truncate text-text-primary">{pendingPhotoPrompt}</span>
                                ) : (
                                  <span>...</span>
                                )}
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </Draggable>
                    );
                  })}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>
          {imageSelectionActive && pendingPhotoPrompt && selectedImagesForRegen.length > 0 && (
            <div className="mt-3 flex items-center gap-3 rounded-xl border border-border-default bg-surface-panel px-4 py-3">
              <span className="flex-1 text-sm text-text-muted">
                Regenerate {selectedImagesForRegen.length} selected with:{" "}
                <span className="font-medium text-text-primary">
                  &quot;{pendingPhotoPrompt}&quot;
                </span>
              </span>
              <button
                type="button"
                className={btnPillSm}
                onClick={onCancelPhotoRegeneration}
              >
                Cancel
              </button>
              <button
                type="button"
                className={btnPillLg}
                onClick={onConfirmPhotoRegeneration}
              >
                Regenerate Selected
              </button>
            </div>
          )}
          {listingData && (
            <div className="mt-8 flex justify-center border-t-2 border-border-default pt-8">
              <button
                type="button"
                className={btnPillLg}
                onClick={() => onUploadToEbay?.(listingData.sku!, listingData)}
                disabled={
                  uploadingSkus?.has(listingData?.sku ?? "") || !listingData?.sku
                }
              >
                {uploadingSkus?.has(listingData?.sku ?? "")
                  ? "Uploading to eBay..."
                  : "Upload to eBay"}
              </button>
            </div>
          )}
          {onAddToGeneratedImages && (
            <ImageUploadModal
              isOpen={showGenUploadModal}
              onClose={() => setShowGenUploadModal(false)}
              onAddImages={(images) => {
                const items = Array.isArray(images) ? images : [images];
                items.forEach((item) => {
                  const url = typeof item === "string" ? item : (item as PendingImage).dataUrl;
                  onAddToGeneratedImages(url);
                });
              }}
              canAddToOriginal={false}
            />
          )}
        </div>
      )}
        </StepCard>
      )}

      {/* Upload to eBay — kicked off by the button in the images card above;
          both steps run inside one /api/upload-listing request and report
          the stream's step messages in their own cards (ADR 0003). */}
      {uploadSteps && (
        <div className="mt-4 flex flex-col gap-3">
          <StepCard
            title={UPLOAD_STEP_TITLES.prepare}
            status={uploadSteps.prepare.status}
            statusText={uploadSteps.prepare.statusText}
            error={uploadSteps.prepare.error}
            onRetry={onRetryUpload}
          />
          <StepCard
            title={UPLOAD_STEP_TITLES.upload}
            status={uploadSteps.upload.status}
            statusText={uploadSteps.upload.statusText}
            error={uploadSteps.upload.error}
            onRetry={onRetryUpload}
          />
        </div>
      )}

      {/* Step 7 — create listing. Runs automatically once images and text
          are ready; its Retry re-runs only this phase. */}
      {createWorkflowActive && (
        <StepCard
          title={CREATE_STEP_TITLES.createListing}
          status={steps.createListing.status}
          statusText={steps.createListing.statusText}
          error={steps.createListing.error}
          onRetry={retryCreateStep("createListing")}
        />
      )}

      {lightboxOpen && (photos?.length ?? 0) > 0 && (
        <Lightbox
          photos={photos!}
          currentIndex={lightboxIndex ?? 0}
          onClose={onCloseLightbox!}
          onNavigate={onNavigateLightbox!}
        />
      )}

      {isEditorOpen && (photos?.length ?? 0) > 0 && (
        <div
          className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60 p-4"
          onClick={onEditorToggle}
        >
          <div
            className="flex max-h-[95vh] w-full max-w-[1400px] flex-col overflow-hidden rounded-xl bg-surface-panel shadow-2xl animate-slide-up"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-border-default p-4">
              <h2 className="m-0 text-xl font-semibold text-text-primary">
                Image Editor
              </h2>
              <button
                type="button"
                aria-label="Close image editor"
                className="flex h-10 w-10 items-center justify-center rounded-full border-none bg-surface-muted text-2xl text-text-muted transition-all hover:rotate-90 hover:bg-surface-hover hover:text-text-primary"
                onClick={onEditorToggle}
              >
                &times;
              </button>
            </div>
            <div className="flex-1 overflow-auto p-4 text-text-primary">
              {onUseRealEbayUploadChange != null && (
                <label className="mb-3 flex cursor-pointer items-center gap-2">
                  <input
                    type="checkbox"
                    checked={useRealEbayUpload ?? false}
                    onChange={(e) =>
                      onUseRealEbayUploadChange(e.target.checked)
                    }
                    className="rounded"
                  />
                  <span>Upload to eBay when adding from canvas</span>
                </label>
              )}
              <ImageCanvas
                onAddToListing={onAddToListing}
                onAddToOriginalPhotos={onAddToOriginalPhotos}
                originalPhotos={photos}
                generatedImages={generatedImages}
                useRealUpload={
                  onUseRealEbayUploadChange != null
                    ? (useRealEbayUpload ?? false)
                    : true
                }
                onRequestClose={onEditorToggle}
                onError={onError}
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default CreateWorkflow;
