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
    <div
      className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/95 animate-fade-in"
      onClick={handleBackdropClick}
    >
      <div className="relative flex h-full w-full items-center justify-center p-8">
        <button
          className="absolute right-2 top-2 z-[1001] flex h-10 w-10 items-center justify-center rounded-full border-2 border-white/30 bg-white/10 text-2xl text-white transition-all duration-300 hover:rotate-90 hover:border-white/50 hover:bg-white/20 md:right-4 md:top-4 md:h-[50px] md:w-[50px] md:text-3xl"
          onClick={onClose}
          aria-label="Close"
        >
          ×
        </button>

        {photos.length > 1 && (
          <>
            <button
              className="absolute left-4 top-1/2 z-[1001] flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full border-2 border-white/30 bg-white/10 text-2xl text-white transition-all duration-300 hover:scale-110 hover:border-white/50 hover:bg-white/20 md:left-8 md:h-[60px] md:w-[60px] md:text-[2.5rem]"
              onClick={() => onNavigate('prev')}
              aria-label="Previous photo"
            >
              ‹
            </button>
            <button
              className="absolute right-4 top-1/2 z-[1001] flex h-12 w-12 -translate-y-1/2 items-center justify-center rounded-full border-2 border-white/30 bg-white/10 text-2xl text-white transition-all duration-300 hover:scale-110 hover:border-white/50 hover:bg-white/20 md:right-8 md:h-[60px] md:w-[60px] md:text-[2.5rem]"
              onClick={() => onNavigate('next')}
              aria-label="Next photo"
            >
              ›
            </button>
          </>
        )}

        <div className="flex max-h-[90%] max-w-[90%] items-center justify-center md:max-w-[95%]">
          <img
            src={currentPhoto}
            alt={`Photo ${currentIndex + 1} of ${photos.length}`}
            className="max-h-[90vh] max-w-full rounded-lg object-contain shadow-2xl animate-zoom-in"
          />
        </div>

        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 rounded-full bg-black/60 px-6 py-3 text-base text-white">
          <span className="font-semibold">
            {currentIndex + 1} / {photos.length}
          </span>
        </div>
      </div>
    </div>
  )
}

export default Lightbox
