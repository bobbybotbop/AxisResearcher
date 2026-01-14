import { useEffect } from 'react'

function Lightbox({ photos, currentIndex, onClose, onNavigate }) {
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        onClose()
      } else if (e.key === 'ArrowLeft') {
        onNavigate('prev')
      } else if (e.key === 'ArrowRight') {
        onNavigate('next')
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = 'unset'
    }
  }, [onClose, onNavigate])

  const handleBackdropClick = (e) => {
    if (e.target === e.currentTarget) {
      onClose()
    }
  }

  const currentPhoto = photos[currentIndex]

  return (
    <div className="lightbox" onClick={handleBackdropClick}>
      <div className="lightbox-content">
        <button className="lightbox-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        
        {photos.length > 1 && (
          <>
            <button
              className="lightbox-nav lightbox-prev"
              onClick={() => onNavigate('prev')}
              aria-label="Previous photo"
            >
              ‹
            </button>
            <button
              className="lightbox-nav lightbox-next"
              onClick={() => onNavigate('next')}
              aria-label="Next photo"
            >
              ›
            </button>
          </>
        )}

        <div className="lightbox-image-container">
          <img
            src={currentPhoto}
            alt={`Photo ${currentIndex + 1} of ${photos.length}`}
            className="lightbox-image"
          />
        </div>

        <div className="lightbox-info">
          <span className="lightbox-counter">
            {currentIndex + 1} / {photos.length}
          </span>
        </div>
      </div>
    </div>
  )
}

export default Lightbox
