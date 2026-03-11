import { useState, useCallback } from 'react'
import ImageUploadModal from './ImageUploadModal'

function PhotoGallery({
  photos,
  editableCategories,
  onCategoryChange,
  onConfirm,
  isConfirming,
  onPhotoClick,
  skippedPhotos = new Set(),
  onSkipPhoto,
  useOriginalPhotos = new Set(),
  onUseOriginalPhoto,
  promptModifier = '',
  onPromptModifierChange,
  onAddToOriginalPhotos,
}) {
  const [showUploadModal, setShowUploadModal] = useState(false)

  const handleModalAddImages = useCallback(
    (images, destination) => {
      if (destination === 'original' && onAddToOriginalPhotos) {
        const urls = Array.isArray(images) ? images : [images]
        onAddToOriginalPhotos(urls)
      }
    },
    [onAddToOriginalPhotos],
  )
  if (!photos || photos.length === 0) {
    return null
  }

  const formatCategoryName = (category) => {
    if (!category) return 'Unknown'
    return category
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ')
  }

  const getCategoryGradient = (category) => {
    const gradients = {
      professional_image: 'from-green-500/90 via-green-500/70 to-transparent',
      edited_image: 'from-red-500/90 via-red-500/70 to-transparent',
      bad_image: 'from-amber-500/90 via-amber-500/70 to-transparent',
      real_world_image: 'from-blue-500/90 via-blue-500/70 to-transparent',
    }
    return gradients[category] || 'from-gray-500/90 via-gray-500/70 to-transparent'
  }

  const categoryOptions = [
    { value: 'bad_image', label: 'Bad Image' },
    { value: 'professional_image', label: 'Professional Image' },
    { value: 'real_world_image', label: 'Real World Image' },
    { value: 'edited_image', label: 'Edited Image' },
  ]

  const handleCategorySelect = (e, photoUrl) => {
    e.stopPropagation()
    const newCategory = e.target.value
    if (onCategoryChange) {
      onCategoryChange(photoUrl, newCategory)
    }
  }

  const handleSkipClick = (e, photoUrl) => {
    e.stopPropagation()
    if (onSkipPhoto) {
      onSkipPhoto(photoUrl)
    }
  }

  const handleUseOriginalClick = (e, photoUrl) => {
    e.stopPropagation()
    if (onUseOriginalPhoto) {
      onUseOriginalPhoto(photoUrl)
    }
  }

  return (
    <div className="mt-8 rounded-2xl border border-gray-200 bg-gray-50 p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold text-gray-800">Original Photos</h2>
        {onAddToOriginalPhotos && (
          <button
            type="button"
            className="rounded-lg bg-gradient-to-br from-primary to-primary-dark px-4 py-2 font-semibold text-white shadow transition-all hover:-translate-y-0.5 hover:shadow-md"
            onClick={() => setShowUploadModal(true)}
          >
            Upload Images
          </button>
        )}
      </div>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-4 sm:grid-cols-[repeat(auto-fill,minmax(180px,1fr))] sm:gap-5">
        {photos.map((photoUrl, index) => {
          const category = editableCategories[photoUrl]
          const isSkipped = skippedPhotos.has(photoUrl)
          const isUseOriginal = useOriginalPhotos.has(photoUrl)
          return (
            <div
              key={index}
              className={`group relative aspect-square cursor-pointer overflow-hidden rounded-xl transition-all ${
                isSkipped ? 'opacity-50' : ''
              }`}
              onClick={() => onPhotoClick && onPhotoClick(index)}
            >
              {onSkipPhoto && (
                <button
                  className="absolute right-1.5 top-1.5 z-10 flex h-8 w-8 items-center justify-center rounded-full text-lg font-bold text-white shadow-md transition-colors hover:opacity-90"
                  style={{
                    background: isSkipped ? '#4CAF50' : '#f44336',
                  }}
                  onClick={(e) => handleSkipClick(e, photoUrl)}
                  title={isSkipped ? 'Include this photo' : 'Skip this photo'}
                >
                  {isSkipped ? '✓' : '×'}
                </button>
              )}
              {onUseOriginalPhoto && !isSkipped && (
                <button
                  className="absolute left-1.5 top-1.5 z-10 flex h-8 w-8 items-center justify-center rounded-full text-sm font-bold text-white shadow-md transition-colors hover:opacity-90"
                  style={{
                    background: isUseOriginal ? '#2196F3' : 'rgba(0,0,0,0.4)',
                  }}
                  onClick={(e) => handleUseOriginalClick(e, photoUrl)}
                  title={isUseOriginal ? 'Edit with AI' : 'Use original (no AI edit)'}
                >
                  {isUseOriginal ? '✓' : 'O'}
                </button>
              )}
              <img
                src={photoUrl}
                alt={`Photo ${index + 1}`}
                className="h-full w-full object-cover"
                loading="lazy"
                onError={(e) => {
                  e.target.src =
                    'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext fill="%23999" font-family="sans-serif" font-size="14" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3EFailed to load%3C/text%3E%3C/svg%3E'
                }}
              />
              <div className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 transition-opacity group-hover:opacity-100">
                <span className="text-2xl font-bold text-white">{index + 1}</span>
              </div>
              {isSkipped && (
                <div className="absolute left-1/2 top-1/2 z-[5] -translate-x-1/2 -translate-y-1/2 rounded-md bg-black/70 px-2.5 py-1 font-bold text-white">
                  SKIPPED
                </div>
              )}
              {isUseOriginal && !isSkipped && (
                <div className="absolute bottom-9 left-1/2 z-[5] -translate-x-1/2 rounded bg-blue-500/90 px-2 py-1 text-[11px] font-bold text-white">
                  USE ORIGINAL
                </div>
              )}
              <div
                className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t ${getCategoryGradient(
                  category
                )} p-2`}
              >
                <select
                  className="w-full cursor-pointer appearance-none rounded border border-white/30 bg-white/95 px-2 py-1 pr-8 text-xs font-semibold uppercase tracking-wide text-gray-800 focus:border-white/60 focus:outline-none focus:ring-2 focus:ring-white/30"
                  style={{
                    backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23333' d='M6 9L1 4h10z'/%3E%3C/svg%3E")`,
                    backgroundRepeat: 'no-repeat',
                    backgroundPosition: 'right 0.5rem center',
                  }}
                  value={category || ''}
                  onChange={(e) => handleCategorySelect(e, photoUrl)}
                  onClick={(e) => e.stopPropagation()}
                  disabled={isSkipped}
                >
                  <option value="">Select Category</option>
                  {categoryOptions.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )
        })}
      </div>
      {onPromptModifierChange && (
        <div className="my-4">
          <label htmlFor="prompt-modifier" className="mb-1.5 block text-sm font-semibold">
            Prompt Modifier (optional)
          </label>
          <p className="mb-2 text-[13px] text-gray-600">
            Add instructions that apply to every generated image (e.g., &quot;change the blue plastic
            to black&quot;)
          </p>
          <textarea
            id="prompt-modifier"
            className="w-full resize-y rounded-md border border-gray-300 p-2.5 text-sm transition-colors focus:border-primary focus:outline-none focus:ring-2 focus:ring-primary/20 disabled:cursor-not-allowed disabled:bg-gray-100"
            value={promptModifier}
            onChange={(e) => onPromptModifierChange(e.target.value)}
            placeholder="e.g., change the color of the blue plastic to black instead"
            rows={2}
            disabled={isConfirming}
          />
        </div>
      )}
      <div className="mt-8 flex justify-center">
        <button
          type="button"
          className="rounded-lg bg-gradient-to-br from-primary to-primary-dark px-8 py-3 font-semibold text-white shadow-md transition-all hover:-translate-y-0.5 hover:shadow-lg disabled:translate-y-0 disabled:cursor-not-allowed disabled:opacity-60 disabled:shadow-none"
          onClick={(e) => {
            e.preventDefault()
            e.stopPropagation()
            if (onConfirm) {
              onConfirm()
            }
          }}
          disabled={isConfirming}
        >
          {isConfirming ? 'Generating Images...' : 'Confirm Categories'}
        </button>
      </div>

      {onAddToOriginalPhotos && (
        <ImageUploadModal
          isOpen={showUploadModal}
          onClose={() => setShowUploadModal(false)}
          onAddImages={handleModalAddImages}
          canAddToOriginal={false}
          mode="original"
        />
      )}
    </div>
  )
}

export default PhotoGallery
