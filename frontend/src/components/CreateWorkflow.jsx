import { useState } from 'react'
import PhotoGallery from './PhotoGallery'
import Lightbox from './Lightbox'
import ListingDetails from './ListingDetails'
import ProgressIndicator from './ProgressIndicator'
import ImageCanvas from './ImageCanvas'
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd'

function CreateWorkflow({
  listingId,
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
}) {
  const [descriptionEditMode, setDescriptionEditMode] = useState(false)

  const btnPrimary =
    'rounded-lg bg-gradient-to-br from-primary to-primary-dark px-4 py-2 font-semibold text-white shadow transition-all hover:-translate-y-0.5 hover:shadow-md disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60'
  const btnSuccess =
    'rounded-lg bg-gradient-to-br from-success to-emerald-600 px-4 py-2 font-semibold text-white shadow transition-all hover:-translate-y-0.5 hover:shadow-md disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60'
  const btnDanger =
    'rounded-lg bg-gradient-to-br from-red-500 to-red-600 px-4 py-2 font-semibold text-white shadow transition-all hover:-translate-y-0.5 hover:shadow-md disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60'

  return (
    <>
      <form onSubmit={onSubmit} className="mb-8 flex flex-wrap gap-4">
        <input
          type="text"
          value={listingId}
          onChange={(e) => onListingIdChange(e.target.value)}
          placeholder="eBay listing ID or URL (e.g., 123456789 or https://www.ebay.com/itm/123456789)"
          className="min-w-[250px] flex-1 rounded-lg border-2 border-gray-300 px-4 py-3 text-base transition-colors focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-100"
          disabled={loading}
        />
        <button type="submit" className={btnPrimary} disabled={loading}>
          {loading ? 'Loading...' : 'Fetch Photos'}
        </button>
      </form>

      {error && (
        <div className="mb-8 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="flex flex-col items-center justify-center gap-4 py-12">
          <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-primary" />
          <p className="text-gray-600">Fetching listing data...</p>
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
        <div className="my-5 rounded-md bg-gray-100 p-2.5">
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
          />
          {isConfirming && imageGenProgress?.isActive && (
            <div className="my-5 rounded-lg border border-gray-200 bg-gray-50 p-4">
              <h3 className="mb-2.5 text-lg text-gray-800">Generating Images</h3>
              <div className="mt-2.5">
                <p className="text-gray-600">
                  Progress: {imageGenProgress.completed} of {imageGenProgress.total} images complete
                </p>
                {imageGenProgress.total > 0 && (
                  <div className="relative mt-2.5 h-5 w-full overflow-hidden rounded bg-gray-200">
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

          <div className="mt-6 overflow-hidden rounded-xl border border-gray-200 bg-white">
            <button
              type="button"
              className="flex w-full items-center gap-3 border-none bg-[#fafbfe] px-5 py-4 text-left text-lg font-semibold text-gray-800 transition-colors hover:bg-[#f0f2fa]"
              onClick={onEditorToggle}
            >
              <span
                className={`inline-block text-sm text-primary transition-transform ${isEditorOpen ? 'rotate-90' : ''}`}
              >
                &#9654;
              </span>
              Image Editor
            </button>
            {isEditorOpen && (
              <div className="border-t border-gray-200 p-4">
                {onUseRealEbayUploadChange != null && (
                  <label className="mb-3 flex cursor-pointer items-center gap-2">
                    <input
                      type="checkbox"
                      checked={useRealEbayUpload ?? false}
                      onChange={(e) => onUseRealEbayUploadChange(e.target.checked)}
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
                  useRealUpload={onUseRealEbayUploadChange != null ? (useRealEbayUpload ?? false) : true}
                />
              </div>
            )}
          </div>
        </>
      )}

      {generatedImages?.length > 0 && (
        <div className="mt-8 rounded-2xl border border-green-200 bg-green-50/50 p-6">
          <h2 className="mb-5 text-xl font-semibold text-gray-800">New Listing Photos</h2>
          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId="new-listing-photos" direction="horizontal">
              {(provided) => (
                <div
                  className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-4 sm:grid-cols-[repeat(auto-fill,minmax(180px,1fr))] sm:gap-5"
                  ref={provided.innerRef}
                  {...provided.droppableProps}
                >
                  {generatedImages.map((imageUrl, index) => (
                    <Draggable key={`img-${imageUrl}-${index}`} draggableId={`img-${imageUrl}-${index}`} index={index}>
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          className={`group relative aspect-square overflow-hidden rounded-xl transition-all ${
                            snapshot.isDragging ? 'opacity-80 shadow-lg' : ''
                          }`}
                        >
                          <div
                            className="absolute left-1.5 top-1.5 z-20 cursor-grab text-gray-600 hover:text-gray-800"
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

          <div className="mt-8 rounded-xl bg-white p-6 shadow-sm">
            <h3 className="mb-2 text-xl text-gray-800">Optional: Edit Images Further</h3>
            <p className="mb-4 text-gray-600">Enter a custom prompt to regenerate selected images</p>
            <textarea
              className="w-full resize-y rounded-lg border-2 border-gray-300 p-3 text-base transition-colors focus:border-primary focus:outline-none disabled:cursor-not-allowed disabled:bg-gray-100"
              value={customPrompt}
              onChange={(e) => onCustomPromptChange(e.target.value)}
              placeholder="Enter your custom prompt for image editing..."
              rows={4}
              disabled={isRegenerating || isAddingNewVersions}
            />
            <div className="mt-4 flex justify-end gap-3">
              {(() => {
                const selCount = selectedImagesForRegen?.length ?? 0
                const totalCount = generatedImages?.length ?? 0
                const displayCount = selCount > 0 ? selCount : totalCount
                return (
                  <>
              <button
                type="button"
                className={btnSuccess}
                onClick={onRegenerateImages}
                disabled={isRegenerating || !customPrompt?.trim()}
              >
                {isRegenerating
                  ? 'Regenerating...'
                  : `Regenerate Selected (${displayCount})`}
              </button>
              <button
                type="button"
                className={btnSuccess}
                onClick={onTrimSelected}
                disabled={isTrimming}
              >
                {isTrimming ? 'Trimming...' : `Trim Selected (${displayCount})`}
              </button>
              <button
                type="button"
                className={btnSuccess}
                onClick={onAddNewVersions}
                disabled={isAddingNewVersions || isRegenerating || !customPrompt?.trim()}
              >
                {isAddingNewVersions
                  ? 'Generating + syncing...'
                  : `New version + sync (${displayCount})`}
              </button>
                  </>
                )
              })()}
            </div>
          </div>

          <div className="mt-8 flex justify-center">
            <button
              type="button"
              className={btnPrimary}
              onClick={onConfirmAndEditText}
              disabled={isCreatingListing}
            >
              {isCreatingListing ? 'Updating Listing...' : 'Confirm and Edit Text'}
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
          <h2 className="mb-4 text-xl font-semibold text-gray-800">Generated Listing</h2>
          <div className="space-y-4">
            <div className="border-b border-gray-200 pb-4">
              <strong className="text-primary">SKU:</strong> {listingData.sku}
            </div>
            <div className="flex flex-col gap-2 border-b border-gray-200 pb-4">
              <div className="flex items-center justify-between">
                <strong className="text-primary">Title:</strong>
                <span
                  className={`rounded-full px-2.5 py-1 text-sm font-semibold ${
                    editableTitle?.length > 80
                      ? 'bg-red-100 text-red-700'
                      : editableTitle?.length >= 73 && editableTitle?.length <= 80
                        ? 'bg-green-100 text-green-700'
                        : 'bg-primary/10 text-primary'
                  }`}
                >
                  {editableTitle?.length ?? 0} / 80
                  {editableTitle?.length > 80 && ` (${editableTitle.length - 80} over)`}
                </span>
              </div>
              <input
                type="text"
                className={`w-full rounded-lg border-2 px-3 py-2.5 transition-colors focus:outline-none focus:ring-2 focus:ring-primary/20 ${
                  editableTitle?.length > 80
                    ? 'border-red-500 bg-red-50 focus:border-red-500 focus:ring-red-500/20'
                    : 'border-gray-300 focus:border-primary'
                }`}
                value={editableTitle}
                onChange={(e) => onEditableTitleChange(e.target.value)}
                placeholder="Listing title..."
              />
              {editableTitle?.length > 80 && (
                <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                  Title exceeds 80 characters. Edit manually or use AI to trim it.
                </div>
              )}
              <div className="flex gap-2">
                {editableTitle?.length > 80 && (
                  <button
                    type="button"
                    className="rounded-lg bg-gradient-to-br from-amber-500 to-amber-600 px-4 py-2 font-semibold text-white transition-all hover:-translate-y-0.5 disabled:opacity-60"
                    onClick={onTrimTitle}
                    disabled={isTrimmingTitle}
                  >
                    {isTrimmingTitle ? 'Trimming...' : 'AI Trim Title'}
                  </button>
                )}
                {editableTitle !== (listingData.inventoryItem?.product?.title || '') && (
                  <button
                    type="button"
                    className={btnSuccess}
                    onClick={onSaveTitle}
                    disabled={isSavingTitle}
                  >
                    {isSavingTitle ? 'Saving...' : 'Save Title'}
                  </button>
                )}
              </div>
            </div>
            <div className="border-b border-gray-200 pb-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <strong className="text-primary">Description:</strong>
                <button
                  type="button"
                  className="rounded-lg border-2 border-gray-300 px-3 py-1.5 text-sm font-semibold text-gray-700 transition-colors hover:border-primary hover:text-primary"
                  onClick={() => setDescriptionEditMode((v) => !v)}
                >
                  {descriptionEditMode ? 'Preview HTML' : 'Edit HTML'}
                </button>
              </div>
              {descriptionEditMode ? (
                <textarea
                  className="mt-2 min-h-[200px] w-full resize-y rounded-lg border-2 border-gray-300 p-3 font-mono text-sm text-gray-800 transition-colors focus:border-primary focus:outline-none"
                  value={editableDescription}
                  onChange={(e) => onEditableDescriptionChange(e.target.value)}
                  placeholder="HTML description..."
                  rows={12}
                  spellCheck={false}
                />
              ) : (
                <div
                  className="listing-description-html mt-2 rounded-md bg-gray-50 p-3 text-gray-600 [&_a]:text-primary [&_a]:underline [&_li]:my-0.5 [&_ol]:list-decimal [&_ol]:pl-6 [&_p]:my-2 [&_p:first-child]:mt-0 [&_ul]:list-disc [&_ul]:pl-6"
                  dangerouslySetInnerHTML={{
                    __html:
                      (editableDescription && editableDescription.trim()) ||
                      '<p class="text-gray-400 italic">N/A</p>',
                  }}
                />
              )}
              <div className="mt-2 flex gap-2">
                {editableDescription !== (listingData.inventoryItem?.product?.description || '') && (
                  <button
                    type="button"
                    className={btnSuccess}
                    onClick={onSaveDescription}
                    disabled={isSavingDescription}
                  >
                    {isSavingDescription ? 'Saving...' : 'Save Description'}
                  </button>
                )}
              </div>
            </div>
            <div className="border-b border-gray-200 pb-4">
              <strong className="text-primary">Price:</strong> $
              {listingData.offer?.pricingSummary?.price?.value || 'N/A'}
            </div>
            <div className="border-b border-gray-200 pb-4">
              <strong className="text-primary">Category ID:</strong>{' '}
              {listingData.offer?.categoryId || 'N/A'}
            </div>
            <div className="border-b border-gray-200 pb-4">
              <strong className="text-primary">
                Images ({listingData.inventoryItem?.product?.imageUrls?.length || 0}):
              </strong>
              <div className="mt-2 space-y-2">
                {listingData.inventoryItem?.product?.imageUrls?.map((url, idx) => (
                  <div key={idx} className="rounded-md bg-gray-50 p-2 text-sm text-gray-600 break-all">
                    {idx + 1}. {url}
                  </div>
                )) || 'No images'}
              </div>
            </div>
            <div className="border-b border-gray-200 pb-4">
              <strong className="text-primary">Created:</strong> {listingData.createdDateTime || 'N/A'}
            </div>
          </div>

          <div className="mt-8 flex justify-center border-t-2 border-gray-200 pt-8">
            <button
              type="button"
              className="rounded-lg bg-gradient-to-br from-red-500 to-red-600 px-10 py-4 text-lg font-bold text-white shadow-lg transition-all hover:-translate-y-0.5 hover:shadow-xl disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60"
              onClick={() => onUploadToEbay(listingData.sku, listingData)}
              disabled={uploadingSkus?.has(listingData?.sku) || !listingData?.sku}
            >
              {uploadingSkus?.has(listingData?.sku) ? 'Uploading to eBay...' : 'Upload to eBay'}
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
              <h3 className="mb-4 text-2xl font-semibold">Upload Successful!</h3>
              <div className="flex flex-col gap-3">
                {uploadResult.listingId && (
                  <div>
                    <strong>Listing ID:</strong>{' '}
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
                    <strong>Listing URL:</strong>{' '}
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
    </>
  )
}

export default CreateWorkflow
