function PhotoGallery({ photos, onPhotoClick }) {
  if (!photos || photos.length === 0) {
    return null
  }

  return (
    <div className="photo-gallery">
      <h2 className="gallery-title">Photos ({photos.length})</h2>
      <div className="gallery-grid">
        {photos.map((photoUrl, index) => (
          <div
            key={index}
            className="gallery-item"
            onClick={() => onPhotoClick(index)}
          >
            <img
              src={photoUrl}
              alt={`Photo ${index + 1}`}
              className="gallery-image"
              loading="lazy"
              onError={(e) => {
                e.target.src = 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="200" height="200"%3E%3Crect fill="%23ddd" width="200" height="200"/%3E%3Ctext fill="%23999" font-family="sans-serif" font-size="14" x="50%25" y="50%25" text-anchor="middle" dy=".3em"%3EFailed to load%3C/text%3E%3C/svg%3E'
              }}
            />
            <div className="gallery-overlay">
              <span className="gallery-index">{index + 1}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default PhotoGallery
