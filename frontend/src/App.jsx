import { useState } from 'react'
import PhotoGallery from './components/PhotoGallery'
import Lightbox from './components/Lightbox'
import ListingDetails from './components/ListingDetails'
import './styles/App.css'

function App() {
  const [photos, setPhotos] = useState([])
  const [listing, setListing] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const [lightboxIndex, setLightboxIndex] = useState(0)
  const [listingId, setListingId] = useState('')

  const fetchListingPhotos = async () => {
    if (!listingId.trim()) {
      setError('Please enter an eBay listing ID or URL')
      return
    }

    setLoading(true)
    setError(null)
    setPhotos([])
    setListing(null)

    try {
      const response = await fetch(`/api/photos/${encodeURIComponent(listingId.trim())}`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch listing data')
      }

      if (data.error) {
        throw new Error(data.error)
      }

      setPhotos(data.photos || [])
      setListing(data.listing || null)
    } catch (err) {
      setError(err.message || 'An error occurred while fetching the listing')
      setPhotos([])
      setListing(null)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    fetchListingPhotos()
  }

  const openLightbox = (index) => {
    setLightboxIndex(index)
    setLightboxOpen(true)
  }

  const closeLightbox = () => {
    setLightboxOpen(false)
  }

  const navigateLightbox = (direction) => {
    if (direction === 'next') {
      setLightboxIndex((prev) => (prev + 1) % photos.length)
    } else {
      setLightboxIndex((prev) => (prev - 1 + photos.length) % photos.length)
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>eBay Photo Gallery</h1>
        <p>Enter an eBay listing ID or URL to view photos</p>
      </header>

      <main className="app-main">
        <form onSubmit={handleSubmit} className="search-form">
          <input
            type="text"
            value={listingId}
            onChange={(e) => setListingId(e.target.value)}
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
          </div>
        )}

        {photos.length > 0 && (
          <PhotoGallery photos={photos} onPhotoClick={openLightbox} />
        )}

        {listing && <ListingDetails listing={listing} />}

        {lightboxOpen && photos.length > 0 && (
          <Lightbox
            photos={photos}
            currentIndex={lightboxIndex}
            onClose={closeLightbox}
            onNavigate={navigateLightbox}
          />
        )}
      </main>
    </div>
  )
}

export default App
