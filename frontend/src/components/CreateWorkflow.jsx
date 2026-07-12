import { useEffect, useState } from "react";
import { motion } from "motion/react";
import PhotoGallery from "./PhotoGallery";
import MessageBarInput from "./MessageBarInput";
import Lightbox from "./Lightbox";
import ListingDetails from "./ListingDetails";
import ProgressIndicator from "./ProgressIndicator";
import ImageCanvas from "./ImageCanvas";
import { DragDropContext, Droppable, Draggable } from "@hello-pangea/dnd";
import { btnPillLg, btnPillSm } from "../styles/buttonPill";
import {
  DEFAULT_CHAT_CONTEXT,
  getChatContextInputPlaceholder,
} from "../constants/chatContextModes";

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
  error,
  isConfirming,
  isCreatingListing,
  listingData,
  editableTitle,
  editableDescription,
  uploadResult,
  isEditorOpen,
  fetchProgress,
  imageGenProgress,
  createListingProgress,
  uploadProgress,
  uploadingSkus,
  isTrimmingTitle,
  isSavingTitle,
  isSavingDescription,
  isGeneratingText = false,
  onCancelTextGen = () => {},
  onListingIdChange,
  onSubmit,
  onCategoryChange,
  onSkipPhoto,
  onConfirmCategories,
  onDragEnd,
  onRemoveFromListing,
  onAddToListing,
  onAddToOriginalPhotos,
  onEditableTitleChange,
  onTrimTitle,
  onSaveTitle,
  onEditableDescriptionChange,
  onSaveDescription,
  onUploadToEbay,
  onEditorToggle,
  useRealEbayUpload,
  onUseRealEbayUploadChange,
  onPhotoClick,
  onCloseLightbox,
  onNavigateLightbox,
  lightboxOpen,
  lightboxIndex,
  classifyImagesEnabled = true,
}) {
  const [descriptionEditMode, setDescriptionEditMode] = useState(false);
  const [chatContext, setChatContext] = useState(DEFAULT_CHAT_CONTEXT);

  useEffect(() => {
    if (!listingLinkSubmitted) {
      setChatContext(DEFAULT_CHAT_CONTEXT);
    }
  }, [listingLinkSubmitted]);

  useEffect(() => {
    if (!isEditorOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === "Escape" && onEditorToggle) {
        onEditorToggle();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isEditorOpen, onEditorToggle]);

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
          onSubmit={onSubmit}
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

      {error && (
        <div className="mb-8 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center gap-4 py-12">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-border-default border-t-primary" />
          <p className="text-text-muted">Fetching listing data...</p>
          {fetchProgress?.isActive && fetchProgress?.totalSteps?.length > 0 && (
            <ProgressIndicator
              steps={fetchProgress.totalSteps}
              currentStep={fetchProgress.currentStep}
              completedSteps={fetchProgress.completedSteps}
            />
          )}
        </div>
      )}

      {listingLinkSubmitted && listing && (
        <div className="mt-4">
          <ListingDetails listing={listing} photos={photos} sku={currentSku} />
        </div>
      )}

      {photos?.length > 0 && (
        <>
          <PhotoGallery
            photos={photos}
            editableCategories={editableCategories}
            onCategoryChange={onCategoryChange}
            onConfirm={onConfirmCategories}
            isConfirming={isConfirming}
            onPhotoClick={onPhotoClick}
            skippedPhotos={skippedPhotos}
            onSkipPhoto={onSkipPhoto}
            onAddToOriginalPhotos={onAddToOriginalPhotos}
            onOpenEditor={onEditorToggle}
            showClassification={classifyImagesEnabled}
          />
          {isConfirming && imageGenProgress?.isActive && (
            <div className="my-5 rounded-lg border border-border-default bg-surface-muted p-4">
              <h3 className="mb-2.5 text-lg text-text-primary">
                Generating Images
              </h3>
              <div className="mt-2.5">
                <p className="text-text-muted">
                  Progress: {imageGenProgress.completed} of{" "}
                  {imageGenProgress.total} images complete
                </p>
                {imageGenProgress.total > 0 && (
                  <div className="relative mt-2.5 h-5 w-full overflow-hidden rounded bg-surface-hover">
                    <div
                      className="h-full rounded bg-green-500 transition-[width] duration-300"
                      style={{
                        width: `${(imageGenProgress.completed / imageGenProgress.total) * 100}%`,
                      }}
                    />
                  </div>
                )}
              </div>
            </div>
          )}

        </>
      )}

      {generatedImages?.length > 0 && (
        <div className="mt-8 rounded-2xl border border-border-default bg-surface-panel p-6">
          <h2 className="mb-5 text-xl font-semibold text-text-primary">
            New Listing Photos
          </h2>
          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId="new-listing-photos" direction="horizontal">
              {(provided) => (
                <div
                  className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-4 sm:grid-cols-[repeat(auto-fill,minmax(180px,1fr))] sm:gap-5"
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                >
                  {generatedImages.map((imageUrl, index) => (
                    <Draggable
                      key={`img-${imageUrl}-${index}`}
                      draggableId={`img-${imageUrl}-${index}`}
                      index={index}
                    >
                      {(provided, snapshot) => {
                        return (
                          <div
                            ref={provided.innerRef}
                            {...provided.draggableProps}
                            {...provided.dragHandleProps}
                            className={`group relative aspect-square cursor-grab overflow-hidden rounded-xl transition-all active:cursor-grabbing ${
                              snapshot.isDragging ? "opacity-80 shadow-lg" : ""
                            }`}
                          >
                            <button
                              type="button"
                              className="absolute right-1.5 top-1.5 z-20 flex h-8 w-8 items-center justify-center rounded-full bg-red-500 text-lg font-bold text-white opacity-0 shadow-md transition-opacity hover:bg-red-600 hover:opacity-90 focus-visible:opacity-100 group-hover:opacity-100"
                              onMouseDown={(e) => e.stopPropagation()}
                              onClick={(e) => {
                                e.stopPropagation();
                                onRemoveFromListing(index);
                              }}
                              title="Remove from listing"
                            >
                              &times;
                            </button>
                            <img
                              src={imageUrl}
                              alt={`New listing photo ${index + 1}`}
                              className="pointer-events-none h-full w-full object-cover"
                              loading="lazy"
                              draggable={false}
                            />
                            <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 transition-opacity group-hover:opacity-100">
                              <span className="text-2xl font-bold text-white">
                                {index + 1}
                              </span>
                            </div>
                          </div>
                        );
                      }}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>
        </div>
      )}

      {listing && (isGeneratingText || editableTitle !== "") && (
        <div className="mt-8">
          <h2 className="mb-4 text-xl font-semibold text-text-primary">
            {isGeneratingText ? "Writing Listing..." : "Generated Listing"}
          </h2>
          <div className="space-y-4">
            <div className="flex flex-col gap-2 border-b border-border-default pb-4">
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <strong className="text-primary">Title:</strong>
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
                    editableTitle?.length > 80
                      ? "bg-red-100 text-red-700"
                      : editableTitle?.length >= 73 &&
                          editableTitle?.length <= 80
                        ? "bg-green-100 text-green-700"
                        : "bg-primary/10 text-primary"
                  }`}
                >
                  {editableTitle?.length ?? 0} / 80
                  {editableTitle?.length > 80 &&
                    ` (${editableTitle.length - 80} over)`}
                </span>
              </div>
              <input
                type="text"
                className={`w-full rounded-lg border-2 px-3 py-2.5 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20 ${
                  editableTitle?.length > 80
                    ? "border-red-500 bg-red-50 focus:border-red-500 focus:ring-red-500/20"
                    : "border-border-default bg-surface-panel text-text-primary focus:border-primary"
                }`}
                value={editableTitle}
                onChange={(e) => onEditableTitleChange(e.target.value)}
                placeholder="Listing title..."
              />
              {isGeneratingText && (
                <p className="animate-pulse text-xs text-text-muted">
                  AI is writing...
                </p>
              )}
              {editableTitle?.length > 80 && (
                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  Title exceeds 80 characters. Edit manually or use AI to trim
                  it.
                </div>
              )}
              <div className="flex gap-2">
                {editableTitle?.length > 80 && (
                  <button
                    type="button"
                    className={btnPillSm}
                    onClick={onTrimTitle}
                    disabled={isTrimmingTitle}
                  >
                    {isTrimmingTitle ? "Trimming..." : "AI Trim Title"}
                  </button>
                )}
                {listingData &&
                  editableTitle !==
                    (listingData.inventoryItem?.product?.title || "") && (
                    <button
                      type="button"
                      className={btnPillSm}
                      onClick={onSaveTitle}
                      disabled={isSavingTitle}
                    >
                      {isSavingTitle ? "Saving..." : "Save Title"}
                    </button>
                  )}
              </div>
            </div>
            <div className="border-b border-border-default pb-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-primary">Description:</strong>
                <button
                  type="button"
                  className="rounded-lg border-2 border-border-default bg-surface-panel px-3 py-1.5 text-sm font-semibold text-text-primary transition-colors hover:border-primary hover:text-primary"
                  onClick={() => setDescriptionEditMode((v) => !v)}
                >
                  {descriptionEditMode ? "Preview HTML" : "Edit HTML"}
                </button>
              </div>
              {descriptionEditMode ? (
                <textarea
                  className="mt-2 min-h-[200px] w-full resize-y rounded-lg border-2 border-border-default bg-surface-panel p-3 font-mono text-sm text-text-primary transition-colors focus:border-primary focus:outline-none"
                  value={editableDescription}
                  onChange={(e) => onEditableDescriptionChange(e.target.value)}
                  placeholder="HTML description..."
                  rows={12}
                  spellCheck={false}
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
              <div className="mt-2 flex gap-2">
                {listingData &&
                  editableDescription !==
                    (listingData.inventoryItem?.product?.description || "") && (
                    <button
                      type="button"
                      className={btnPillSm}
                      onClick={onSaveDescription}
                      disabled={isSavingDescription}
                    >
                      {isSavingDescription ? "Saving..." : "Save Description"}
                    </button>
                  )}
              </div>
            </div>
          </div>

          {isCreatingListing &&
            createListingProgress?.isActive &&
            createListingProgress?.totalSteps?.length > 0 && (
              <div className="mt-4">
                <ProgressIndicator
                  steps={createListingProgress.totalSteps}
                  currentStep={createListingProgress.currentStep}
                  completedSteps={createListingProgress.completedSteps}
                />
              </div>
            )}

          {listingData && (
            <>
              <div className="mt-4 space-y-4">
                <div className="border-b border-border-default pb-4">
                  <strong className="text-primary">SKU:</strong> {listingData.sku}
                </div>
                <div className="border-b border-border-default pb-4">
                  <strong className="text-primary">Price:</strong> $
                  {listingData.offer?.pricingSummary?.price?.value || "N/A"}
                </div>
                <div className="border-b border-border-default pb-4">
                  <strong className="text-primary">Category ID:</strong>{" "}
                  {listingData.offer?.categoryId || "N/A"}
                </div>
                <div className="border-b border-border-default pb-4">
                  <strong className="text-primary">
                    Images (
                    {listingData.inventoryItem?.product?.imageUrls?.length || 0}):
                  </strong>
                  <div className="mt-2 space-y-2">
                    {listingData.inventoryItem?.product?.imageUrls?.map(
                      (url, idx) => (
                        <div
                          key={idx}
                          className="rounded-md bg-surface-muted p-2 text-sm text-text-muted break-all"
                        >
                          {idx + 1}. {url}
                        </div>
                      ),
                    ) || "No images"}
                  </div>
                </div>
                <div className="border-b border-border-default pb-4">
                  <strong className="text-primary">Created:</strong>{" "}
                  {listingData.createdDateTime || "N/A"}
                </div>
              </div>

              <div className="mt-8 flex justify-center border-t-2 border-border-default pt-8">
                <button
                  type="button"
                  className={btnPillLg}
                  onClick={() => onUploadToEbay(listingData.sku, listingData)}
                  disabled={
                    uploadingSkus?.has(listingData?.sku) || !listingData?.sku
                  }
                >
                  {uploadingSkus?.has(listingData?.sku)
                    ? "Uploading to eBay..."
                    : "Upload to eBay"}
                </button>
              </div>
              {uploadingSkus?.has(listingData?.sku) &&
                uploadProgress?.isActive &&
                uploadProgress?.totalSteps?.length > 0 && (
                  <div className="mt-4">
                    <ProgressIndicator
                      steps={uploadProgress.totalSteps}
                      currentStep={uploadProgress.currentStep}
                      completedSteps={uploadProgress.completedSteps}
                    />
                  </div>
                )}

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

      {lightboxOpen && photos?.length > 0 && (
        <Lightbox
          photos={photos}
          currentIndex={lightboxIndex}
          onClose={onCloseLightbox}
          onNavigate={onNavigateLightbox}
        />
      )}

      {isEditorOpen && photos?.length > 0 && (
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
              />
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default CreateWorkflow;
