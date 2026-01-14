function PhotoGallery({
  photos,
  editableCategories,
  onCategoryChange,
  onConfirm,
  isConfirming,
  onPhotoClick,
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

  return (
    <div className="photo-gallery">
      <h2 className="gallery-title">Photos ({photos.length})</h2>
      <div className="gallery-grid">
        {photos.map((photoUrl, index) => {
          const category = editableCategories[photoUrl];
          return (
            <div
              key={index}
              className="gallery-item"
              onClick={() => onPhotoClick && onPhotoClick(index)}
            >
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
              <div className={`gallery-category ${getCategoryClass(category)}`}>
                <select
                  className="category-select"
                  value={category || ""}
                  onChange={(e) => handleCategorySelect(e, photoUrl)}
                  onClick={(e) => e.stopPropagation()}
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
