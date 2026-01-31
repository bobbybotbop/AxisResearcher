import { useState } from 'react'
import PhotoGallery from './components/PhotoGallery'
import Lightbox from './components/Lightbox'
import ListingDetails from './components/ListingDetails'
import './styles/App.css'

function App() {
  const [photos, setPhotos] = useState([])
  const [categories, setCategories] = useState({})
  const [editableCategories, setEditableCategories] = useState({})
  const [listing, setListing] = useState(null)
  const [loading, setLoading] = useState(false)
  const [isConfirming, setIsConfirming] = useState(false)
  const [error, setError] = useState(null)
  const [generatedImages, setGeneratedImages] = useState([])
  const [customPrompt, setCustomPrompt] = useState('')
  const [selectedImagesForRegen, setSelectedImagesForRegen] = useState([])
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [isCreatingListing, setIsCreatingListing] = useState(false)
  const [listingData, setListingData] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [activeTab, setActiveTab] = useState('create') // 'create', 'upload', or 'testing'
  const [testingResult, setTestingResult] = useState(null)
  const [isTesting, setIsTesting] = useState(false)
  const [testingId, setTestingId] = useState('')
  const [allListings, setAllListings] = useState([])
  const [loadingListings, setLoadingListings] = useState(false)
  const [uploadingSkus, setUploadingSkus] = useState(new Set())
  const [uploadResults, setUploadResults] = useState({})
  const [selectedListing, setSelectedListing] = useState(null)
  const [listingDetailData, setListingDetailData] = useState(null)
  const [loadingListingDetail, setLoadingListingDetail] = useState(false)
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
    setCategories({})
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
      const initialCategories = data.categories || {}
      setCategories(initialCategories)
      setEditableCategories({ ...initialCategories })
      setListing(data.listing || null)
      setGeneratedImages([])
    } catch (err) {
      setError(err.message || 'An error occurred while fetching the listing')
      setPhotos([])
      setCategories({})
      setEditableCategories({})
      setListing(null)
      setGeneratedImages([])
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

  const handleCategoryChange = (photoUrl, newCategory) => {
    setEditableCategories((prev) => ({
      ...prev,
      [photoUrl]: newCategory
    }))
  }

  const handleConfirmCategories = async () => {
    console.log('Confirm categories button clicked')
    console.log('Photos:', photos)
    console.log('Editable categories:', editableCategories)
    
    setIsConfirming(true)
    setError(null)

    try {
      const requestBody = {
        photos: photos,
        categories: editableCategories
      }
      console.log('Sending request to /api/generate-images:', requestBody)
      
      const response = await fetch('/api/generate-images', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody)
      })

      console.log('Response status:', response.status)
      const data = await response.json()
      console.log('Response data:', data)

      if (!response.ok) {
        throw new Error(data.error || 'Failed to generate images')
      }

      if (data.error) {
        throw new Error(data.error)
      }

      const generatedImagesList = data.generated_images || []
      console.log('Generated images:', generatedImagesList)
      console.log(`Successfully generated ${generatedImagesList.length} image(s)`)
      
      setGeneratedImages(generatedImagesList)
      setCategories(editableCategories) // Update confirmed categories
      setSelectedImagesForRegen([]) // Reset selection
      setCustomPrompt('') // Reset prompt
    } catch (err) {
      console.error('Error generating images:', err)
      setError(err.message || 'An error occurred while generating images')
    } finally {
      setIsConfirming(false)
    }
  }

  const handleImageSelection = (index) => {
    setSelectedImagesForRegen((prev) => {
      if (prev.includes(index)) {
        return prev.filter(i => i !== index)
      } else {
        return [...prev, index]
      }
    })
  }

  const handleRegenerateImages = async () => {
    if (!customPrompt.trim()) {
      setError('Please enter a custom prompt')
      return
    }
    if (selectedImagesForRegen.length === 0) {
      setError('Please select at least one image to regenerate')
      return
    }

    setIsRegenerating(true)
    setError(null)

    try {
      const imagesToRegen = selectedImagesForRegen.map(index => generatedImages[index])
      console.log('Regenerating images:', imagesToRegen)
      console.log('Custom prompt:', customPrompt)

      const response = await fetch('/api/regenerate-images', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_urls: imagesToRegen,
          prompt: customPrompt
        })
      })

      const data = await response.json()
      console.log('Regeneration response:', data)

      if (!response.ok) {
        throw new Error(data.error || 'Failed to regenerate images')
      }

      if (data.error) {
        throw new Error(data.error)
      }

      const regeneratedUrls = data.generated_images || []
      console.log('Regenerated images:', regeneratedUrls)

      // Replace selected images with regenerated ones
      const newImages = [...generatedImages]
      selectedImagesForRegen.forEach((originalIndex, regenIndex) => {
        if (regenIndex < regeneratedUrls.length) {
          newImages[originalIndex] = regeneratedUrls[regenIndex]
        }
      })

      setGeneratedImages(newImages)
      setSelectedImagesForRegen([])
      setCustomPrompt('')
    } catch (err) {
      console.error('Error regenerating images:', err)
      setError(err.message || 'An error occurred while regenerating images')
    } finally {
      setIsRegenerating(false)
    }
  }

  const handleConfirmAndEditText = async () => {
    if (generatedImages.length === 0) {
      setError('No generated images to add to listing')
      return
    }
    if (!listing) {
      setError('Original listing data is required')
      return
    }

    setIsCreatingListing(true)
    setError(null)

    try {
      console.log('Creating listing with images:', generatedImages)
      console.log('Listing data:', listing)

      const response = await fetch('/api/create-listing', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          generated_images: generatedImages,
          listing: listing
        })
      })

      const data = await response.json()
      console.log('Create listing response:', data)

      if (!response.ok) {
        throw new Error(data.error || 'Failed to create listing')
      }

      if (data.error) {
        throw new Error(data.error)
      }

      setListingData(data.listing_data)
      setUploadResult(null) // Reset upload result when new listing is created
    } catch (err) {
      console.error('Error creating listing:', err)
      setError(err.message || 'An error occurred while creating listing')
    } finally {
      setIsCreatingListing(false)
    }
  }

  const fetchAllListings = async () => {
    setLoadingListings(true)
    setError(null)

    try {
      const response = await fetch('/api/listings')
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch listings')
      }

      if (data.error) {
        throw new Error(data.error)
      }

      setAllListings(data.listings || [])
      console.log('Loaded listings:', data.listings)
    } catch (err) {
      console.error('Error fetching listings:', err)
      setError(err.message || 'An error occurred while fetching listings')
    } finally {
      setLoadingListings(false)
    }
  }

  const handleUploadToEbay = async (sku, listingData = null) => {
    if (!sku) {
      setError('No SKU provided')
      return
    }

    setUploadingSkus(prev => new Set(prev).add(sku))
    setError(null)

    try {
      console.log('Uploading listing to eBay with SKU:', sku)
      console.log('Listing data:', listingData)

      const response = await fetch('/api/upload-listing', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          sku: sku,
          filename: listingData?.filename || (listingData?.fileSku ? `${listingData.fileSku}.json` : null)
        })
      })

      const data = await response.json()
      console.log('Upload response:', data)
      console.log('Response status:', response.status)
      console.log('Response ok:', response.ok)

      if (!response.ok) {
        const errorMessage = data.error || `HTTP ${response.status}: Failed to upload listing`
        console.error('Upload failed:', errorMessage)
        throw new Error(errorMessage)
      }

      if (data.error) {
        console.error('Upload error in response:', data.error)
        throw new Error(data.error)
      }

      if (!data.upload_result) {
        console.error('No upload_result in response:', data)
        throw new Error('Upload completed but no result returned')
      }

      // Store result for this specific SKU
      setUploadResults(prev => ({
        ...prev,
        [sku]: data.upload_result
      }))

      // If uploading from the create tab, also update the main upload result
      if (sku === listingData?.sku) {
        setUploadResult(data.upload_result)
      }

      console.log('Upload successful:', data.upload_result)
    } catch (err) {
      console.error('Error uploading listing:', err)
      setError(err.message || 'An error occurred while uploading listing')
    } finally {
      setUploadingSkus(prev => {
        const newSet = new Set(prev)
        newSet.delete(sku)
        return newSet
      })
    }
  }

  // Fetch listings when upload tab is activated
  const handleTabChange = (tab) => {
    setActiveTab(tab)
    if (tab === 'upload') {
      fetchAllListings()
    }
  }

  const handleTestingFunction = async () => {
    setIsTesting(true)
    setError(null)
    setTestingResult(null)

    try {
      console.log('Running testing function with id:', testingId)

      const response = await fetch('/api/testing', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id: testingId || null
        })
      })

      const data = await response.json()
      console.log('Testing response:', data)

      if (!response.ok) {
        throw new Error(data.error || 'Failed to run testing function')
      }

      if (data.error) {
        throw new Error(data.error)
      }

      setTestingResult(data.result)
      console.log('Testing function completed:', data.result)
    } catch (err) {
      console.error('Error running testing function:', err)
      setError(err.message || 'An error occurred while running testing function')
    } finally {
      setIsTesting(false)
    }
  }

  const handleListingClick = async (listing) => {
    setSelectedListing(listing)
    setLoadingListingDetail(true)
    setError(null)

    try {
      const response = await fetch(`/api/listings/${listing.sku}`)
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.error || 'Failed to fetch listing details')
      }

      if (data.error) {
        throw new Error(data.error)
      }

      setListingDetailData(data.listing_data)
    } catch (err) {
      console.error('Error fetching listing details:', err)
      setError(err.message || 'An error occurred while fetching listing details')
    } finally {
      setLoadingListingDetail(false)
    }
  }

  const closeListingDetail = () => {
    setSelectedListing(null)
    setListingDetailData(null)
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>Axis Researcher</h1>
        <p>Automatically create listings with AI</p>
      </header>

      <main className="app-main">
        <div className="tabs">
          <button
            className={`tab-button ${activeTab === 'create' ? 'active' : ''}`}
            onClick={() => handleTabChange('create')}
          >
            Create Listing
          </button>
          <button
            className={`tab-button ${activeTab === 'upload' ? 'active' : ''}`}
            onClick={() => handleTabChange('upload')}
          >
            Upload Listings
          </button>
          <button
            className={`tab-button ${activeTab === 'testing' ? 'active' : ''}`}
            onClick={() => handleTabChange('testing')}
          >
            Testing
          </button>
        </div>

        {activeTab === 'upload' && (
          <div className="upload-listings-section">
            <h2 className="gallery-title">Generated Listings</h2>
            
            {loadingListings ? (
              <div className="loading">
                <div className="spinner"></div>
                <p>Loading listings...</p>
              </div>
            ) : allListings.length === 0 ? (
              <div className="no-listings">
                <p>No generated listings found. Create a listing first!</p>
              </div>
            ) : (
              <div className="listings-grid">
                {allListings.map((listing) => (
                  <div 
                    key={listing.sku} 
                    className="listing-card"
                    onClick={() => handleListingClick(listing)}
                  >
                    <div className="listing-card-header">
                      <h3 className="listing-card-title">{listing.title}</h3>
                      <span className="listing-card-sku">{listing.sku}</span>
                    </div>
                    <div className="listing-card-info">
                      <div className="listing-card-item">
                        <strong>Price:</strong> ${listing.price}
                      </div>
                      <div className="listing-card-item">
                        <strong>Category:</strong> {listing.categoryId}
                      </div>
                      <div className="listing-card-item">
                        <strong>Images:</strong> {listing.imageCount}
                      </div>
                      <div className="listing-card-item">
                        <strong>Created:</strong>{' '}
                        {listing.createdDateTime
                          ? new Date(listing.createdDateTime).toLocaleString()
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="listing-card-actions">
                      <button
                        type="button"
                        className="listing-upload-button"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleUploadToEbay(listing.sku, listing)
                        }}
                        disabled={uploadingSkus.has(listing.sku)}
                      >
                        {uploadingSkus.has(listing.sku)
                          ? 'Uploading...'
                          : 'Upload to eBay'}
                      </button>
                    </div>
                    {uploadResults[listing.sku] && (
                      <div className="listing-upload-result">
                        <div className="upload-success-icon">✓</div>
                        <div className="upload-success-info">
                          {uploadResults[listing.sku].listingId && (
                            <div>
                              <strong>Listing ID:</strong> {uploadResults[listing.sku].listingId}
                            </div>
                          )}
                          {uploadResults[listing.sku].href && (
                            <div>
                              <a
                                href={uploadResults[listing.sku].href}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="listing-link"
                              >
                                View on eBay →
                              </a>
                            </div>
                          )}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Listing Detail Modal */}
        {selectedListing && (
          <div className="listing-detail-modal" onClick={closeListingDetail}>
            <div className="listing-detail-content" onClick={(e) => e.stopPropagation()}>
              <div className="listing-detail-header">
                <h2 className="listing-detail-title">Listing Details: {selectedListing.sku}</h2>
                <button className="listing-detail-close" onClick={closeListingDetail}>×</button>
              </div>
              
              {loadingListingDetail ? (
                <div className="loading">
                  <div className="spinner"></div>
                  <p>Loading listing details...</p>
                </div>
              ) : listingDetailData ? (
                <div className="listing-detail-body">
                  <pre className="listing-json-display">
                    {JSON.stringify(listingDetailData, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="listing-detail-error">
                  <p>Failed to load listing details</p>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'testing' && (
          <div className="testing-section">
            <h2 className="gallery-title">Testing</h2>
            <div className="testing-content">
              <p className="testing-description">
                Use this section to test functions and debug code.
              </p>
              <div className="testing-input-group">
                <label htmlFor="testing-id" className="testing-label">
                  ID (optional):
                </label>
                <input
                  id="testing-id"
                  type="text"
                  className="testing-input"
                  value={testingId}
                  onChange={(e) => setTestingId(e.target.value)}
                  placeholder="Enter ID parameter..."
                  disabled={isTesting}
                />
              </div>
              <button
                type="button"
                className="testing-button"
                onClick={handleTestingFunction}
                disabled={isTesting}
              >
                {isTesting ? 'Running...' : 'Run Testing Function'}
              </button>
              {testingResult && (
                <div className="testing-result">
                  <h3>Result:</h3>
                  <pre className="testing-result-display">
                    {typeof testingResult === 'string' 
                      ? testingResult 
                      : JSON.stringify(testingResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'create' && (
          <>
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
          <PhotoGallery
            photos={photos}
            editableCategories={editableCategories}
            onCategoryChange={handleCategoryChange}
            onConfirm={handleConfirmCategories}
            isConfirming={isConfirming}
            onPhotoClick={openLightbox}
          />
        )}

        {generatedImages.length > 0 && (
          <div className="generated-images-section">
            <h2 className="gallery-title">Generated Images ({generatedImages.length})</h2>
            <div className="gallery-grid">
              {generatedImages.map((imageUrl, index) => (
                <div key={index} className="gallery-item image-selectable">
                  <label className="image-checkbox-label">
                    <input
                      type="checkbox"
                      checked={selectedImagesForRegen.includes(index)}
                      onChange={() => handleImageSelection(index)}
                      className="image-checkbox"
                    />
                    <span className="checkbox-overlay">Select to regenerate</span>
                  </label>
                  <img
                    src={imageUrl}
                    alt={`Generated image ${index + 1}`}
                    className="gallery-image"
                    loading="lazy"
                  />
                </div>
              ))}
            </div>

            <div className="prompt-section">
              <h3 className="prompt-title">Optional: Edit Images Further</h3>
              <p className="prompt-description">Enter a custom prompt to regenerate selected images</p>
              <textarea
                className="prompt-input"
                value={customPrompt}
                onChange={(e) => setCustomPrompt(e.target.value)}
                placeholder="Enter your custom prompt for image editing..."
                rows={4}
                disabled={isRegenerating || selectedImagesForRegen.length === 0}
              />
              <div className="prompt-actions">
                <button
                  type="button"
                  className="regenerate-button"
                  onClick={handleRegenerateImages}
                  disabled={isRegenerating || !customPrompt.trim() || selectedImagesForRegen.length === 0}
                >
                  {isRegenerating ? 'Regenerating...' : `Regenerate Selected (${selectedImagesForRegen.length})`}
                </button>
              </div>
            </div>

            <div className="listing-actions">
              <button
                type="button"
                className="confirm-edit-button"
                onClick={handleConfirmAndEditText}
                disabled={isCreatingListing}
              >
                {isCreatingListing ? 'Creating Listing...' : 'Confirm and Edit Text'}
              </button>
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
              <div className="listing-info-item">
                <strong>Title:</strong> {listingData.inventoryItem?.product?.title || 'N/A'}
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
                    <div key={idx} className="listing-image-url">{idx + 1}. {url}</div>
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
                onClick={() => handleUploadToEbay(listingData.sku, listingData)}
                disabled={uploadingSkus.has(listingData?.sku) || !listingData?.sku}
              >
                {uploadingSkus.has(listingData?.sku) ? 'Uploading to eBay...' : 'Upload to eBay'}
              </button>
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

        {lightboxOpen && photos.length > 0 && (
          <Lightbox
            photos={photos}
            currentIndex={lightboxIndex}
            onClose={closeLightbox}
            onNavigate={navigateLightbox}
          />
        )}
          </>
        )}
      </main>
    </div>
  )
}

export default App
