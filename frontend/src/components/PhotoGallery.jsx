function PhotoGallery({
  photos,
  editableCategories,
  onCategoryChange,
  onConfirm,
  isConfirming,
  onPhotoClick,
  skippedPhotos = new Set(),
  onSkipPhoto,
}) {
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

  const getCategoryClass = (category) => {
    if (!category) return "category-unknown";
    return `category-${category.replace("_", "-")}`;
  };

  const categoryOptions = [
    { value: "bad_image", label: "Bad Image" },
    { value: "professional_image", label: "Professional Image" },
    { value: "real_world_image", label: "Real World Image" },
    { value: "edited_image", label: "Edited Image" },
  ];

  const handleCategorySelect = (e, photoUrl) => {
    e.stopPropagation(); // Prevent triggering photo click
    const newCategory = e.target.value;
    if (onCategoryChange) {
      onCategoryChange(photoUrl, newCategory);
    }
  };

  const handleSkipClick = (e, photoUrl) => {
    e.stopPropagation(); // Prevent triggering photo click
    if (onSkipPhoto) {
      onSkipPhoto(photoUrl);
    }
  };

  return (
    <div className="photo-gallery">
      <h2 className="gallery-title">Photos ({photos.length})</h2>
      <div className="gallery-grid">
        {photos.map((photoUrl, index) => {
          const category = editableCategories[photoUrl];
          const isSkipped = skippedPhotos.has(photoUrl);
          return (
            <div
              key={index}
              className={`gallery-item ${isSkipped ? 'skipped' : ''}`}
              onClick={() => onPhotoClick && onPhotoClick(index)}
              style={{
                opacity: isSkipped ? 0.5 : 1,
                position: 'relative'
              }}
            >
              {onSkipPhoto && (
                <button
                  className="skip-photo-button"
                  onClick={(e) => handleSkipClick(e, photoUrl)}
                  style={{
                    position: 'absolute',
                    top: '5px',
                    right: '5px',
                    background: isSkipped ? '#4CAF50' : '#f44336',
                    color: 'white',
                    border: 'none',
                    borderRadius: '50%',
                    width: '30px',
                    height: '30px',
                    cursor: 'pointer',
                    fontSize: '18px',
                    fontWeight: 'bold',
                    zIndex: 10,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                  }}
                  title={isSkipped ? 'Include this photo' : 'Skip this photo'}
                >
                  {isSkipped ? '✓' : '×'}
                </button>
              )}
              <img
                src={photoUrl}
                alt={`Photo ${index + 1}`}
                className="gallery-image"
                loading="lazy"
                onError={(e) => {
                  e.target.src =
                    'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext fill="%23999" font-family="sans-serif" font-size="14" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3EFailed to load%3C/text%3E%3C/svg%3E';
                }}
              />
              <div className="gallery-overlay">
                <span className="gallery-index">{index + 1}</span>
              </div>
              {isSkipped && (
                <div style={{
                  position: 'absolute',
                  top: '50%',
                  left: '50%',
                  transform: 'translate(-50%, -50%)',
                  background: 'rgba(0, 0, 0, 0.7)',
                  color: 'white',
                  padding: '5px 10px',
                  borderRadius: '5px',
                  fontWeight: 'bold',
                  zIndex: 5
                }}>
                  SKIPPED
                </div>
              )}
              <div className={`gallery-category ${getCategoryClass(category)}`}>
                <select
                  className="category-select"
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
            </div>
          );
        })}
      </div>
      <div className="gallery-actions">
        <button
          type="button"
          className="confirm-button"
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            console.log("Button clicked, calling onConfirm");
            if (onConfirm) {
              onConfirm();
            } else {
              console.error("onConfirm handler is not provided");
            }
          }}
          disabled={isConfirming}
        >
          {isConfirming ? "Generating Images..." : "Confirm Categories"}
        </button>
      </div>
    </div>
  );
}

export default PhotoGallery;
