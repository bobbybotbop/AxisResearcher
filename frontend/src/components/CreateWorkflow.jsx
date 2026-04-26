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

function CreateWorkflow({
  listingId,
  listingLinkSubmitted = false,
  shouldAutoHideMessageBar = false,
  sidebarCollapsed = false,
  photos,
  categories,
  editableCategories,
  listing,
  currentSku,
  skippedPhotos,
  useOriginalPhotos,
  promptModifier,
  generatedImages,
  selectedImagesForRegen,
  customPrompt,
  loading,
  error,
  isConfirming,
  isRegenerating,
  isTrimming,
  isAddingNewVersions,
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
  onListingIdChange,
  onSubmit,
  onCategoryChange,
  onSkipPhoto,
  onUseOriginalPhoto,
  onPromptModifierChange,
  onConfirmCategories,
  onImageSelection,
  onRegenerateImages,
  onTrimSelected,
  onAddNewVersions,
  onCustomPromptChange,
  onDragEnd,
  onRemoveFromListing,
  onAddToListing,
  onAddToOriginalPhotos,
  onConfirmAndEditText,
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
  const [isHoveringBarZone, setIsHoveringBarZone] = useState(false);

  // Bar is revealed while loading (always visible) or while user is hovering the
  // top reveal zone / the bar itself after auto-hide kicks in.
  const isBarRevealed = !shouldAutoHideMessageBar || isHoveringBarZone;

  // Reset hover state when leaving auto-hide mode so reveal logic doesn't get stuck.
  useEffect(() => {
    if (!shouldAutoHideMessageBar) {
      setIsHoveringBarZone(false);
    }
  }, [shouldAutoHideMessageBar]);

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
    ? "fixed right-0 top-0 z-40 flex w-auto flex-col items-center justify-center min-h-0 bg-surface-app/90 px-6 py-3 shadow-sm backdrop-blur md:px-8 transition-[left,margin,padding,min-height,background-color,box-shadow,border-color,backdrop-filter] duration-500 ease-in-out"
    : "flex w-full flex-col items-center mb-[15%] min-h-[min(42vh,320px)] max-w-4xl self-center justify-center border-b border-transparent bg-transparent shadow-none backdrop-blur-none transition-[margin,padding,min-height,background-color,box-shadow,border-color,backdrop-filter] duration-500 ease-in-out";

  return (
    <>
      {shouldAutoHideMessageBar && (
        <motion.div
          aria-hidden="true"
          className="fixed right-0 top-0 z-30"
          style={{ left: sidebarLeft, height: 96 }}
          onHoverStart={() => setIsHoveringBarZone(true)}
          onHoverEnd={() => setIsHoveringBarZone(false)}
        />
      )}
      <motion.div
        style={
          listingLinkSubmitted
            ? { left: sidebarLeft, right: 0 }
            : undefined
        }
        animate={
          listingLinkSubmitted
            ? { y: isBarRevealed ? 0 : "-120%" }
            : { y: 0 }
        }
        transition={{ type: "spring", stiffness: 260, damping: 30 }}
        onHoverStart={
          shouldAutoHideMessageBar
            ? () => setIsHoveringBarZone(true)
            : undefined
        }
        onHoverEnd={
          shouldAutoHideMessageBar
            ? () => setIsHoveringBarZone(false)
            : undefined
        }
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
            listingLinkSubmitted ? "mt-0" : "mt-12 md:mt-16"
          }`}
        >
          <MessageBarInput
            fullWidth
            value={listingId}
            onChange={onListingIdChange}
            placeholder="Paste any eBay link"
            disabled={loading}
            loading={loading}
            aria-label="eBay listing URL or ID"
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

      {currentSku && (
        <div className="my-5 rounded-md bg-surface-muted p-2.5 text-text-primary">
          <strong>Current SKU:</strong> {currentSku}
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
            useOriginalPhotos={useOriginalPhotos}
            onUseOriginalPhoto={onUseOriginalPhoto}
            promptModifier={promptModifier}
            onPromptModifierChange={onPromptModifierChange}
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
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          className={`group relative aspect-square overflow-hidden rounded-xl transition-all ${
                            snapshot.isDragging ? "opacity-80 shadow-lg" : ""
                          }`}
                        >
                          <div
                            className="absolute left-1.5 top-1.5 z-20 cursor-grab text-text-muted hover:text-text-primary"
                            {...provided.dragHandleProps}
                            title="Drag to reorder"
                          >
                            &#x2630;
                          </div>
                          <label className="absolute inset-0 z-10 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={selectedImagesForRegen?.includes(index)}
                              onChange={() => onImageSelection(index)}
                              className="peer sr-only"
                            />
                            <span className="pointer-events-none absolute inset-0 hidden rounded-xl border-2 border-primary bg-primary/10 peer-checked:block" />
                          </label>
                          <div className="absolute bottom-2 left-2 rounded bg-black/60 px-2 py-0.5 text-sm font-bold text-white">
                            {index + 1}
                          </div>
                          <button
                            type="button"
                            className="pointer-events-auto absolute right-1.5 top-1.5 z-20 flex h-8 w-8 items-center justify-center rounded-full bg-red-500 text-lg font-bold text-white shadow-md transition-colors hover:bg-red-600"
                            onClick={() => onRemoveFromListing(index)}
                            title="Remove from listing"
                          >
                            &times;
                          </button>
                          <img
                            src={imageUrl}
                            alt={`New listing photo ${index + 1}`}
                            className="h-full w-full object-cover"
                            loading="lazy"
                          />
                        </div>
                      )}
                    </Draggable>
                  ))}
                  {provided.placeholder}
                </div>
              )}
            </Droppable>
          </DragDropContext>

          <div className="mt-8 rounded-xl border border-border-default bg-surface-muted p-6 shadow-sm">
            <h3 className="mb-2 text-xl text-text-primary">
              Optional: Edit Images Further
            </h3>
            <p className="mb-4 text-text-muted">
              Enter a custom prompt to regenerate selected images
            </p>
            <textarea
              className="w-full resize-y rounded-lg border-2 border-border-default bg-surface-panel p-3 text-base text-text-primary transition-colors focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-surface-hover"
              value={customPrompt}
              onChange={(e) => onCustomPromptChange(e.target.value)}
              placeholder="Enter your custom prompt for image editing..."
              rows={4}
              disabled={isRegenerating || isAddingNewVersions}
            />
            <div className="mt-4 flex justify-end gap-3">
              {(() => {
                const selCount = selectedImagesForRegen?.length ?? 0;
                const totalCount = generatedImages?.length ?? 0;
                const displayCount = selCount > 0 ? selCount : totalCount;
                return (
                  <>
                    <button
                      type="button"
                      className={btnPillSm}
                      onClick={onRegenerateImages}
                      disabled={isRegenerating || !customPrompt?.trim()}
                    >
                      {isRegenerating
                        ? "Regenerating..."
                        : `Regenerate Selected (${displayCount})`}
                    </button>
                    <button
                      type="button"
                      className={btnPillSm}
                      onClick={onTrimSelected}
                      disabled={isTrimming}
                    >
                      {isTrimming
                        ? "Trimming..."
                        : `Trim Selected (${displayCount})`}
                    </button>
                    <button
                      type="button"
                      className={btnPillSm}
                      onClick={onAddNewVersions}
                      disabled={
                        isAddingNewVersions ||
                        isRegenerating ||
                        !customPrompt?.trim()
                      }
                    >
                      {isAddingNewVersions
                        ? "Generating + syncing..."
                        : `New version + sync (${displayCount})`}
                    </button>
                  </>
                );
              })()}
            </div>
          </div>

          <div className="mt-8 flex justify-center">
            <button
              type="button"
              className={btnPillLg}
              onClick={onConfirmAndEditText}
              disabled={isCreatingListing}
            >
              {isCreatingListing
                ? "Updating Listing..."
                : "Confirm and Edit Text"}
            </button>
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
        </div>
      )}

      {listingData && (
        <div className="mt-8">
          <h2 className="mb-4 text-xl font-semibold text-text-primary">
            Generated Listing
          </h2>
          <div className="space-y-4">
            <div className="border-b border-border-default pb-4">
              <strong className="text-primary">SKU:</strong> {listingData.sku}
            </div>
            <div className="flex flex-col gap-2 border-b border-border-default pb-4">
              <div className="flex items-center justify-between">
                <strong className="text-primary">Title:</strong>
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
                {editableTitle !==
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
                {editableDescription !==
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
            <div className="mt-8 rounded-xl bg-gradient-to-br from-success to-emerald-600 p-6 text-white">
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
        </div>
      )}

      {listing && <ListingDetails listing={listing} />}

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
