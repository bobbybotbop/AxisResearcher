import { useState, useCallback, useEffect } from "react";
import ImageUploadModal from "./ImageUploadModal";
import { btnPill, btnPillLg } from "../styles/buttonPill";

function PhotoGallery({
  photos,
  editableCategories,
  onCategoryChange,
  onConfirm,
  isConfirming,
  onPhotoClick,
  skippedPhotos = new Set(),
  onSkipPhoto,
  onAddToOriginalPhotos,
  onOpenEditor,
  showClassification = true,
}) {
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [selectMode, setSelectMode] = useState(false);
  const [selectedPhotos, setSelectedPhotos] = useState(new Set());
  const [bulkDropdownOpen, setBulkDropdownOpen] = useState(false);

  useEffect(() => {
    if (!bulkDropdownOpen) return;
    const close = () => setBulkDropdownOpen(false);
    document.addEventListener("click", close);
    return () => document.removeEventListener("click", close);
  }, [bulkDropdownOpen]);

  const handleModalAddImages = useCallback(
    (images, destination) => {
      if (destination === "original" && onAddToOriginalPhotos) {
        const urls = Array.isArray(images) ? images : [images];
        onAddToOriginalPhotos(urls);
      }
    },
    [onAddToOriginalPhotos],
  );

  if (!photos || photos.length === 0) {
    return null;
  }

  const formatCategoryName = (category) => {
    if (!category) return "Unknown";
    return category
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ");
  };

  const getCategoryGradient = (category) => {
    const gradients = {
      professional_image: "from-green-500/90 via-green-500/70 to-transparent",
      edited_image: "from-red-500/90 via-red-500/70 to-transparent",
      bad_image: "from-amber-500/90 via-amber-500/70 to-transparent",
      real_world_image: "from-blue-500/90 via-blue-500/70 to-transparent",
    };
    return (
      gradients[category] || "from-gray-500/90 via-gray-500/70 to-transparent"
    );
  };

  const categoryOptions = [
    { value: "bad_image", label: "Bad Image" },
    { value: "professional_image", label: "Professional Image" },
    { value: "real_world_image", label: "Real World Image" },
    { value: "edited_image", label: "Edited Image" },
  ];

  const handleCategorySelect = (e, photoUrl) => {
    e.stopPropagation();
    const newCategory = e.target.value;
    if (onCategoryChange) {
      onCategoryChange(photoUrl, newCategory);
    }
  };

  const handleSkipClick = (e, photoUrl) => {
    e.stopPropagation();
    if (onSkipPhoto) {
      onSkipPhoto(photoUrl);
    }
  };

  const toggleSelectMode = () => {
    setSelectMode((prev) => {
      if (prev) {
        setSelectedPhotos(new Set());
        setBulkDropdownOpen(false);
      }
      return !prev;
    });
  };

  const togglePhotoSelection = (index) => {
    setSelectedPhotos((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  return (
    <div className="mt-8 rounded-2xl border border-border-default bg-surface-panel p-6">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <h2 className="text-xl font-semibold text-text-primary">Original Photos</h2>
        <div className="flex flex-wrap items-center gap-2">
          {onOpenEditor && (
            <button type="button" className={btnPill} onClick={onOpenEditor}>
              Image Editor
            </button>
          )}
          {onAddToOriginalPhotos && (
            <button
              type="button"
              className={btnPill}
              onClick={() => setShowUploadModal(true)}
            >
              Upload Images
            </button>
          )}
          <button
            type="button"
            className={`${btnPill} ${selectMode ? "ring-2 ring-inset ring-blue-500" : ""}`}
            onClick={toggleSelectMode}
          >
            {selectMode ? "Done" : "Select"}
          </button>
          <div className="relative">
            <button
              type="button"
              className={btnPill}
              disabled={!selectMode || selectedPhotos.size === 0}
              onClick={() => setBulkDropdownOpen((prev) => !prev)}
            >
              Bulk Actions ▾
            </button>
            {bulkDropdownOpen && (
              <div className="absolute right-0 top-full z-20 mt-1 min-w-30 rounded-lg border border-border-default bg-surface-panel py-1 shadow-lg">
                <button
                  type="button"
                  className="w-full px-4 py-2 text-left text-sm text-text-primary hover:bg-surface-app"
                  onClick={() => {
                    selectedPhotos.forEach((idx) => {
                      const photoUrl = photos[idx];
                      if (onSkipPhoto) onSkipPhoto(photoUrl);
                    });
                    setSelectedPhotos(new Set());
                    setSelectMode(false);
                    setBulkDropdownOpen(false);
                  }}
                >
                  Skip
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
      <div className="grid grid-cols-[repeat(auto-fill,minmax(150px,1fr))] gap-4 sm:grid-cols-[repeat(auto-fill,minmax(180px,1fr))] sm:gap-5">
        {photos.map((photoUrl, index) => {
          const category = editableCategories[photoUrl];
          const isSkipped = skippedPhotos.has(photoUrl);
          return (
            <div
              key={index}
              className={`group relative aspect-square cursor-pointer overflow-hidden rounded-xl transition-all ${
                isSkipped ? "opacity-50" : ""
              }`}
              onClick={() => {
                if (selectMode) {
                  togglePhotoSelection(index);
                } else {
                  onPhotoClick && onPhotoClick(index);
                }
              }}
            >
              {onSkipPhoto && !selectMode && (
                <button
                  className="absolute right-1.5 top-1.5 z-10 flex h-8 w-8 items-center justify-center rounded-full text-lg font-bold text-white opacity-0 shadow-md transition-opacity hover:opacity-90 focus-visible:opacity-100 group-hover:opacity-100"
                  style={{
                    background: isSkipped ? "#4CAF50" : "#f44336",
                  }}
                  onClick={(e) => handleSkipClick(e, photoUrl)}
                  title={isSkipped ? "Include this photo" : "Skip this photo"}
                >
                  {isSkipped ? "✓" : "×"}
                </button>
              )}
              <img
                src={photoUrl}
                alt={`Photo ${index + 1}`}
                className="h-full w-full object-cover"
                loading="lazy"
                onError={(e) => {
                  e.target.src =
                    'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext fill="%23999" font-family="sans-serif" font-size="14" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3EFailed to load%3C/text%3E%3C/svg%3E';
                }}
              />
              <div className="absolute inset-0 flex items-center justify-center bg-black/50 opacity-0 transition-opacity group-hover:opacity-100">
                <span className="text-2xl font-bold text-white">
                  {index + 1}
                </span>
              </div>
              {isSkipped && (
                <div className="absolute left-1/2 top-1/2 z-[5] -translate-x-1/2 -translate-y-1/2 rounded-md bg-black/70 px-2.5 py-1 font-bold text-white">
                  SKIPPED
                </div>
              )}
              {selectMode && selectedPhotos.has(index) && (
                <div className="pointer-events-none absolute inset-0 z-10 rounded-xl ring-4 ring-inset ring-blue-500">
                  <div className="absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full bg-blue-500 text-white">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" className="h-4 w-4">
                      <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 01.143 1.052l-8 10.5a.75.75 0 01-1.127.075l-4.5-4.5a.75.75 0 011.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 011.05-.143z" clipRule="evenodd" />
                    </svg>
                  </div>
                </div>
              )}
              {showClassification && (
                <div
                  className={`absolute bottom-0 left-0 right-0 bg-gradient-to-t ${getCategoryGradient(
                    category,
                  )} p-2`}
                >
                  <select
                    className="w-full cursor-pointer appearance-none rounded border border-border-default bg-surface-panel/95 px-2 py-1 pr-8 text-xs font-semibold uppercase tracking-wide text-text-primary accent-text-primary focus:border-border-default focus:outline-none focus:ring-2 focus:ring-border-default/40"
                    style={{
                      backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23c7c7c7' d='M6 9L1 4h10z'/%3E%3C/svg%3E")`,
                      backgroundRepeat: "no-repeat",
                      backgroundPosition: "right 0.5rem center",
                    }}
                    value={category || ""}
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
              )}
            </div>
          );
        })}
      </div>
      <div className="mt-8 flex justify-center">
        <button
          type="button"
          className={btnPillLg}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            if (onConfirm) {
              onConfirm();
            }
          }}
          disabled={isConfirming}
        >
          {isConfirming ? "Generating Images..." : "Confirm Categories"}
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
  );
}

export default PhotoGallery;
