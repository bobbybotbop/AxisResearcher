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
  isCreatingListing,
  listingData,
  editableTitle,
  uploadResult,
  isEditorOpen,
  fetchProgress,
  imageGenProgress,
  createListingProgress,
  uploadProgress,
  uploadingSkus,
  isTrimmingTitle,
  isSavingTitle,
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
  onCustomPromptChange,
  onDragEnd,
  onRemoveFromListing,
  onAddToListing,
  onConfirmAndEditText,
  onEditableTitleChange,
  onTrimTitle,
  onSaveTitle,
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
  return (
    <>
      <form onSubmit={onSubmit} className="search-form">
        <input
          type="text"
          value={listingId}
          onChange={(e) => onListingIdChange(e.target.value)}
          placeholder="eBay listing ID or URL (e.g., 123456789 or https://www.ebay.com/itm/123456789)"
          className="search-input"
          disabled={loading}
        />
        <button type="submit" className="search-button" disabled={loading}>
          {loading ? 'Loading...' : 'Fetch Photos'}
        </button>
      </form>

      {error && (
        <div className="error-message">
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="loading">
          <div className="spinner"></div>
          <p>Fetching listing data...</p>
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
        <div className="sku-display" style={{ margin: '20px 0', padding: '10px', backgroundColor: '#f0f0f0', borderRadius: '5px' }}>
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
          />
          {isConfirming && imageGenProgress?.isActive && (
            <div className="image-generation-progress" style={{ margin: '20px 0', padding: '15px', backgroundColor: '#f9f9f9', borderRadius: '5px' }}>
              <h3>Generating Images</h3>
              <div className="progress-info">
                <p>Progress: {imageGenProgress.completed} of {imageGenProgress.total} images complete</p>
                {imageGenProgress.total > 0 && (
                  <div className="progress-bar-container" style={{ marginTop: '10px' }}>
                    <div
                      className="progress-bar"
                      style={{
                        width: `${(imageGenProgress.completed / imageGenProgress.total) * 100}%`,
                        height: '20px',
                        backgroundColor: '#4CAF50',
                        borderRadius: '4px',
                        transition: 'width 0.3s ease',
                      }}
                    ></div>
                  </div>
                )}
              </div>
            </div>
          )}

          <div className="editor-collapsible-panel">
            <button type="button" className="editor-toggle-button" onClick={onEditorToggle}>
              <span className={`editor-chevron ${isEditorOpen ? 'open' : ''}`}>&#9654;</span>
              Image Editor
            </button>
            {isEditorOpen && (
              <div className="editor-panel-body">
                {onUseRealEbayUploadChange != null && (
                  <label className="editor-upload-checkbox" style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={useRealEbayUpload ?? false}
                      onChange={(e) => onUseRealEbayUploadChange(e.target.checked)}
                    />
                    <span>Upload to eBay when adding from canvas</span>
                  </label>
                )}
                <ImageCanvas
                  onAddToListing={onAddToListing}
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
        <div className="generated-images-section section-container new-listing-container">
          <h2 className="gallery-title">New Listing Photos</h2>
          <DragDropContext onDragEnd={onDragEnd}>
            <Droppable droppableId="new-listing-photos" direction="horizontal">
              {(provided) => (
                <div className="gallery-grid" ref={provided.innerRef} {...provided.droppableProps}>
                  {generatedImages.map((imageUrl, index) => (
                    <Draggable key={`img-${imageUrl}-${index}`} draggableId={`img-${imageUrl}-${index}`} index={index}>
                      {(provided, snapshot) => (
                        <div
                          ref={provided.innerRef}
                          {...provided.draggableProps}
                          className={`gallery-item image-selectable ${snapshot.isDragging ? 'is-dragging' : ''}`}
                        >
                          <div className="drag-handle" {...provided.dragHandleProps} title="Drag to reorder">
                            <span className="drag-handle-dots">&#x2630;</span>
                          </div>
                          <label className="image-checkbox-label">
                            <input
                              type="checkbox"
                              checked={selectedImagesForRegen?.includes(index)}
                              onChange={() => onImageSelection(index)}
                              className="image-checkbox"
                            />
                            <span className="checkbox-overlay">Select to regenerate</span>
                          </label>
                          <div className="gallery-order-badge">{index + 1}</div>
                          <button
                            type="button"
                            className="listing-photo-delete-btn"
                            onClick={() => onRemoveFromListing(index)}
                            title="Remove from listing"
                          >
                            &times;
                          </button>
                          <img
                            src={imageUrl}
                            alt={`New listing photo ${index + 1}`}
                            className="gallery-image"
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

          <div className="prompt-section">
            <h3 className="prompt-title">Optional: Edit Images Further</h3>
            <p className="prompt-description">Enter a custom prompt to regenerate selected images</p>
            <textarea
              className="prompt-input"
              value={customPrompt}
              onChange={(e) => onCustomPromptChange(e.target.value)}
              placeholder="Enter your custom prompt for image editing..."
              rows={4}
              disabled={isRegenerating || (selectedImagesForRegen?.length ?? 0) === 0}
            />
            <div className="prompt-actions">
              <button
                type="button"
                className="regenerate-button"
                onClick={onRegenerateImages}
                disabled={isRegenerating || !customPrompt?.trim() || (selectedImagesForRegen?.length ?? 0) === 0}
              >
                {isRegenerating ? 'Regenerating...' : `Regenerate Selected (${selectedImagesForRegen?.length ?? 0})`}
              </button>
              <button
                type="button"
                className="regenerate-button"
                onClick={onTrimSelected}
                disabled={isTrimming || (selectedImagesForRegen?.length ?? 0) === 0}
              >
                {isTrimming ? 'Trimming...' : `Trim Selected (${selectedImagesForRegen?.length ?? 0})`}
              </button>
            </div>
          </div>

          <div className="listing-actions">
            <button
              type="button"
              className="confirm-edit-button"
              onClick={onConfirmAndEditText}
              disabled={isCreatingListing}
            >
              {isCreatingListing ? 'Updating Listing...' : 'Confirm and Edit Text'}
            </button>
            {isCreatingListing && createListingProgress?.isActive && createListingProgress?.totalSteps?.length > 0 && (
              <div style={{ marginTop: '15px' }}>
                <ProgressIndicator
                  steps={createListingProgress.totalSteps}
                  currentStep={createListingProgress.currentStep}
                  completedSteps={createListingProgress.completedSteps}
                />
              </div>
            )}
          </div>
        </div>
      )}

      {listingData && (
        <div className="listing-data-section">
          <h2 className="gallery-title">Generated Listing</h2>
          <div className="listing-data-display">
            <div className="listing-info-item">
              <strong>SKU:</strong> {listingData.sku}
            </div>
            <div className="listing-info-item title-edit-section">
              <div className="title-edit-header">
                <strong>Title:</strong>
                <span
                  className={`title-char-count ${
                    editableTitle?.length > 80 ? 'over-limit' : editableTitle?.length >= 73 && editableTitle?.length <= 80 ? 'good' : 'under'
                  }`}
                >
                  {editableTitle?.length ?? 0} / 80
                  {editableTitle?.length > 80 && ` (${editableTitle.length - 80} over)`}
                </span>
              </div>
              <input
                type="text"
                className={`title-edit-input ${editableTitle?.length > 80 ? 'over-limit' : ''}`}
                value={editableTitle}
                onChange={(e) => onEditableTitleChange(e.target.value)}
                placeholder="Listing title..."
              />
              {editableTitle?.length > 80 && (
                <div className="title-warning">Title exceeds 80 characters. Edit manually or use AI to trim it.</div>
              )}
              <div className="title-edit-actions">
                {editableTitle?.length > 80 && (
                  <button type="button" className="title-trim-button" onClick={onTrimTitle} disabled={isTrimmingTitle}>
                    {isTrimmingTitle ? 'Trimming...' : 'AI Trim Title'}
                  </button>
                )}
                {editableTitle !== (listingData.inventoryItem?.product?.title || '') && (
                  <button type="button" className="title-save-button" onClick={onSaveTitle} disabled={isSavingTitle}>
                    {isSavingTitle ? 'Saving...' : 'Save Title'}
                  </button>
                )}
              </div>
            </div>
            <div className="listing-info-item">
              <strong>Description:</strong>
              <div className="listing-description-text">
                {listingData.inventoryItem?.product?.description || 'N/A'}
              </div>
            </div>
            <div className="listing-info-item">
              <strong>Price:</strong> ${listingData.offer?.pricingSummary?.price?.value || 'N/A'}
            </div>
            <div className="listing-info-item">
              <strong>Category ID:</strong> {listingData.offer?.categoryId || 'N/A'}
            </div>
            <div className="listing-info-item">
              <strong>Images ({listingData.inventoryItem?.product?.imageUrls?.length || 0}):</strong>
              <div className="listing-images-list">
                {listingData.inventoryItem?.product?.imageUrls?.map((url, idx) => (
                  <div key={idx} className="listing-image-url">
                    {idx + 1}. {url}
                  </div>
                )) || 'No images'}
              </div>
            </div>
            <div className="listing-info-item">
              <strong>Created:</strong> {listingData.createdDateTime || 'N/A'}
            </div>
          </div>

          <div className="upload-section">
            <button
              type="button"
              className="upload-button"
              onClick={() => onUploadToEbay(listingData.sku, listingData)}
              disabled={uploadingSkus?.has(listingData?.sku) || !listingData?.sku}
            >
              {uploadingSkus?.has(listingData?.sku) ? 'Uploading to eBay...' : 'Upload to eBay'}
            </button>
            {uploadingSkus?.has(listingData?.sku) && uploadProgress?.isActive && uploadProgress?.totalSteps?.length > 0 && (
              <div style={{ marginTop: '15px' }}>
                <ProgressIndicator
                  steps={uploadProgress.totalSteps}
                  currentStep={uploadProgress.currentStep}
                  completedSteps={uploadProgress.completedSteps}
                />
              </div>
            )}
          </div>

          {uploadResult && (
            <div className="upload-result-section">
              <h3 className="upload-result-title">Upload Successful!</h3>
              <div className="upload-result-info">
                {uploadResult.listingId && (
                  <div className="upload-result-item">
                    <strong>Listing ID:</strong> {uploadResult.listingId}
                  </div>
                )}
                {uploadResult.ebayId && (
                  <div className="upload-result-item">
                    <strong>eBay ID:</strong> {uploadResult.ebayId}
                  </div>
                )}
                {uploadResult.href && (
                  <div className="upload-result-item">
                    <strong>Listing URL:</strong>{' '}
                    <a href={uploadResult.href} target="_blank" rel="noopener noreferrer" className="listing-link">
                      View on eBay
                    </a>
                  </div>
                )}
                <div className="upload-result-item">
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
