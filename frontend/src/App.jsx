import { useState, useEffect, useCallback } from 'react'
import PhotoGallery from './components/PhotoGallery'
import Lightbox from './components/Lightbox'
import ListingDetails from './components/ListingDetails'
import ProgressIndicator from './components/ProgressIndicator'
import ImageCanvas from './components/ImageCanvas'
import { DragDropContext, Droppable, Draggable } from '@hello-pangea/dnd'
import './styles/App.css'

/**
 * Fetch with streaming progress support.
 * Reads NDJSON stream from the backend and calls onProgress for each progress event.
 * Returns the final result data, or throws on error.
 */
async function fetchWithProgress(url, options, onProgress) {
  const response = await fetch(url, options)

  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let result = null
  let errorMsg = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // Keep incomplete line in buffer

    for (const line of lines) {
      if (!line.trim()) continue
      try {
        const event = JSON.parse(line)
        if (event.type === 'progress') {
          onProgress(event)
        } else if (event.type === 'result') {
          result = event.data
        } else if (event.type === 'error') {
          errorMsg = event.error
        }
      } catch (e) {
        console.warn('Failed to parse progress event:', line, e)
      }
    }
  }

  // Process any remaining data in the buffer
  if (buffer.trim()) {
    try {
      const event = JSON.parse(buffer)
      if (event.type === 'result') result = event.data
      else if (event.type === 'error') errorMsg = event.error
    } catch (e) {
      // ignore malformed trailing data
    }
  }

  if (errorMsg) {
    throw new Error(errorMsg)
  }

  return result
}

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
  const [currentSku, setCurrentSku] = useState(null)
  const [skippedPhotos, setSkippedPhotos] = useState(new Set())
  const [useOriginalPhotos, setUseOriginalPhotos] = useState(new Set())
  const [promptModifier, setPromptModifier] = useState('')
  const [isEditorOpen, setIsEditorOpen] = useState(false)
  const [editableTitle, setEditableTitle] = useState('')
  const [isTrimmingTitle, setIsTrimmingTitle] = useState(false)
  const [isSavingTitle, setIsSavingTitle] = useState(false)
  
  // Progress tracking states
  const [fetchProgress, setFetchProgress] = useState({
    isActive: false,
    currentStep: null,
    completedSteps: [],
    totalSteps: []
  })
  const [imageGenProgress, setImageGenProgress] = useState({
    isActive: false,
    taskId: null,
    total: 0,
    completed: 0,
    currentGenerating: []
  })
  const [createListingProgress, setCreateListingProgress] = useState({
    isActive: false,
    currentStep: null,
    completedSteps: [],
    totalSteps: []
  })
  const [uploadProgress, setUploadProgress] = useState({
    isActive: false,
    currentStep: null,
    completedSteps: [],
    totalSteps: []
  })

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
    setCurrentSku(null)
    setSkippedPhotos(new Set())
    setUseOriginalPhotos(new Set())
    
    // Initialize progress tracking
    const steps = ['Fetching listing from eBay', 'Creating initial JSON file', 'Categorizing images']
    setFetchProgress({
      isActive: true,
      currentStep: null,
      completedSteps: [],
      totalSteps: steps
    })

    try {
      // Stream progress from backend as each step actually completes
      const data = await fetchWithProgress(
        `/api/photos/${encodeURIComponent(listingId.trim())}`,
        {},
        (event) => {
          setFetchProgress(prev => {
            const completed = [...prev.completedSteps]
            if (event.status === 'completed' && !completed.includes(event.step)) {
              completed.push(event.step)
            }
            return {
              ...prev,
              completedSteps: completed,
              currentStep: event.status === 'in_progress' ? event.step : prev.currentStep
            }
          })
        }
      )

      setPhotos(data.photos || [])
      const initialCategories = data.categories || {}
      setCategories(initialCategories)
      setEditableCategories({ ...initialCategories })
      setListing(data.listing || null)
      setCurrentSku(data.sku || null)
      setGeneratedImages([])

      // Auto-skip images categorized as real_world_image or edited_image
      const autoSkip = new Set()
      for (const [url, cat] of Object.entries(initialCategories)) {
        if (cat === 'real_world_image' || cat === 'edited_image') {
          autoSkip.add(url)
        }
      }
      setSkippedPhotos(autoSkip)
      
      // All steps complete
      setFetchProgress({
        isActive: false,
        currentStep: null,
        completedSteps: steps,
        totalSteps: steps
      })
    } catch (err) {
      setError(err.message || 'An error occurred while fetching the listing')
      setPhotos([])
      setCategories({})
      setEditableCategories({})
      setListing(null)
      setCurrentSku(null)
      setSkippedPhotos(new Set())
      setUseOriginalPhotos(new Set())
      setGeneratedImages([])
      setFetchProgress({
        isActive: false,
        currentStep: null,
        completedSteps: [],
        totalSteps: []
      })
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

  const handleSkipPhoto = (photoUrl) => {
    setSkippedPhotos((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(photoUrl)) {
        newSet.delete(photoUrl)
      } else {
        newSet.add(photoUrl)
      }
      return newSet
    })
  }

  const handleUseOriginalPhoto = (photoUrl) => {
    setUseOriginalPhotos((prev) => {
      const newSet = new Set(prev)
      if (newSet.has(photoUrl)) {
        newSet.delete(photoUrl)
      } else {
        newSet.add(photoUrl)
      }
      return newSet
    })
  }

  const handleConfirmCategories = async () => {
    console.log('Confirm categories button clicked')
    console.log('Photos:', photos)
    console.log('Editable categories:', editableCategories)
    console.log('Skipped photos:', skippedPhotos)
    console.log('Use original photos:', useOriginalPhotos)
    
    setIsConfirming(true)
    setError(null)

    try {
      // Filter out skipped photos
      const photosToProcess = photos.filter(photoUrl => !skippedPhotos.has(photoUrl))
      const needsAIPhotos = photosToProcess.filter(photoUrl => !useOriginalPhotos.has(photoUrl))

      if (photosToProcess.length === 0) {
        throw new Error('All photos are skipped. Include at least one photo.')
      }

      // All use original: no API call, use original URLs directly
      if (needsAIPhotos.length === 0) {
        setGeneratedImages(photosToProcess)
        setCategories(editableCategories)
        setSelectedImagesForRegen([])
        setCustomPrompt('')
        setIsConfirming(false)
        return
      }

      const categoriesToProcess = {}
      needsAIPhotos.forEach(photoUrl => {
        if (editableCategories[photoUrl]) {
          categoriesToProcess[photoUrl] = editableCategories[photoUrl]
        }
      })

      const requestBody = {
        photos: needsAIPhotos,
        categories: categoriesToProcess,
        prompt_modifier: promptModifier.trim() || undefined
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
        throw new Error(data.error || 'Failed to start image generation')
      }

      if (data.error) {
        throw new Error(data.error)
      }

      // Get task ID for progress tracking
      const taskId = data.task_id
      const totalImages = data.total_images || 0
      
      if (!taskId) {
        throw new Error('No task ID returned from server')
      }

      // Initialize progress tracking
      setImageGenProgress({
        isActive: true,
        taskId: taskId,
        total: totalImages,
        completed: 0,
        currentGenerating: []
      })

      // Poll for progress updates
      const pollInterval = setInterval(async () => {
        try {
          const statusResponse = await fetch(`/api/generate-images-status/${taskId}`)
          const statusData = await statusResponse.json()

          if (statusData.status === 'completed' || statusData.status === 'failed') {
            clearInterval(pollInterval)
            
            if (statusData.status === 'completed') {
              const aiGeneratedList = statusData.generated_images || []
              console.log('AI generated images:', aiGeneratedList)
              console.log(`Successfully generated ${aiGeneratedList.length} image(s)`)
              
              // Merge: for each photo in photosToProcess, use original URL or next AI result
              const merged = []
              let aiIndex = 0
              for (const photoUrl of photosToProcess) {
                if (useOriginalPhotos.has(photoUrl)) {
                  merged.push(photoUrl)
                } else {
                  merged.push(aiGeneratedList[aiIndex++])
                }
              }
              setGeneratedImages(merged)
              setCategories(editableCategories)
              setSelectedImagesForRegen([])
              setCustomPrompt('')
              
              setImageGenProgress({
                isActive: false,
                taskId: null,
                total: totalImages,
                completed: totalImages,
                currentGenerating: []
              })
            } else {
              // Failed - show errors but return partial results if any
              const aiGeneratedList = statusData.generated_images || []
              const merged = []
              let aiIndex = 0
              for (const photoUrl of photosToProcess) {
                if (useOriginalPhotos.has(photoUrl)) {
                  merged.push(photoUrl)
                } else if (aiIndex < aiGeneratedList.length) {
                  merged.push(aiGeneratedList[aiIndex++])
                }
              }
              setGeneratedImages(merged)
              
              const errorMsg = statusData.errors && statusData.errors.length > 0
                ? `Image generation completed with errors: ${statusData.errors.join('; ')}`
                : 'Image generation failed'
              setError(errorMsg)
              
              setImageGenProgress({
                isActive: false,
                taskId: null,
                total: totalImages,
                completed: statusData.completed || 0,
                currentGenerating: []
              })
            }
            
            setIsConfirming(false)
          } else {
            // Update progress
            setImageGenProgress(prev => ({
              ...prev,
              completed: statusData.completed || 0
            }))
          }
        } catch (pollErr) {
          console.error('Error polling status:', pollErr)
          clearInterval(pollInterval)
          setError('Error checking generation status')
          setIsConfirming(false)
          setImageGenProgress({
            isActive: false,
            taskId: null,
            total: totalImages,
            completed: 0,
            currentGenerating: []
          })
        }
      }, 500) // Poll every 500ms
      
      // Store interval ID for cleanup if component unmounts
      // Note: In a real app, you'd use useEffect cleanup, but for now we rely on completion/error handling
    } catch (err) {
      console.error('Error generating images:', err)
      setError(err.message || 'An error occurred while generating images')
      setIsConfirming(false)
      setImageGenProgress({
        isActive: false,
        taskId: null,
        total: 0,
        completed: 0,
        currentGenerating: []
      })
    }
  }

  const handleAddToListing = useCallback((ebayUrl) => {
    setGeneratedImages(prev => [...prev, ebayUrl])
  }, [])

  const handleRemoveFromListing = useCallback((index) => {
    setGeneratedImages(prev => prev.filter((_, i) => i !== index))
    setSelectedImagesForRegen(prev => prev.filter(i => i !== index).map(i => i > index ? i - 1 : i))
  }, [])

  const handleDragEnd = useCallback((result) => {
    if (!result.destination) return
    const srcIdx = result.source.index
    const destIdx = result.destination.index
    if (srcIdx === destIdx) return
    setGeneratedImages(prev => {
      const updated = [...prev]
      const [moved] = updated.splice(srcIdx, 1)
      updated.splice(destIdx, 0, moved)
      return updated
    })
    // Clear selection since indices changed
    setSelectedImagesForRegen([])
  }, [])

  const handleImageSelection = (index) => {
    // #region agent log
    fetch('http://127.0.0.1:7243/ingest/02f918e9-918d-446f-84f2-b624a202fc2e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'App.jsx:handleImageSelection',message:'Checkbox clicked',data:{index,currentSelected:selectedImagesForRegen,generatedImagesLength:generatedImages.length},timestamp:Date.now(),hypothesisId:'checkbox'})}).catch(()=>{});
    // #endregion
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

      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/02f918e9-918d-446f-84f2-b624a202fc2e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'App.jsx:handleRegenerateImages:entry',message:'Regenerate request starting',data:{selectedIndices:selectedImagesForRegen,imageUrls:imagesToRegen,promptLength:customPrompt.length,totalGeneratedImages:generatedImages.length},timestamp:Date.now(),hypothesisId:'E'})}).catch(()=>{});
      // #endregion

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

      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/02f918e9-918d-446f-84f2-b624a202fc2e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'App.jsx:handleRegenerateImages:response',message:'Regeneration API response received',data:{status:response.status,ok:response.ok,error:data.error,warnings:data.warnings,generatedImagesCount:(data.generated_images||[]).length,generatedImages:data.generated_images},timestamp:Date.now(),hypothesisId:'A'})}).catch(()=>{});
      // #endregion

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

      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/02f918e9-918d-446f-84f2-b624a202fc2e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'App.jsx:handleRegenerateImages:replacement',message:'Image replacement result',data:{regeneratedUrlsCount:regeneratedUrls.length,replacementsAttempted:selectedImagesForRegen.length,newImagesLength:newImages.length},timestamp:Date.now(),hypothesisId:'E'})}).catch(()=>{});
      // #endregion

      setGeneratedImages(newImages)
      setSelectedImagesForRegen([])
      setCustomPrompt('')
    } catch (err) {
      console.error('Error regenerating images:', err)
      // #region agent log
      fetch('http://127.0.0.1:7243/ingest/02f918e9-918d-446f-84f2-b624a202fc2e',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'App.jsx:handleRegenerateImages:error',message:'Regeneration error caught',data:{errorMessage:err.message,errorName:err.name},timestamp:Date.now(),hypothesisId:'A'})}).catch(()=>{});
      // #endregion
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
    if (!currentSku) {
      setError('SKU is required. Please fetch photos first.')
      return
    }

    setIsCreatingListing(true)
    setError(null)
    
    // Initialize progress tracking
    const steps = ['Updating images', 'Generating optimized text', 'Updating metadata', 'Updating aspects']
    setCreateListingProgress({
      isActive: true,
      currentStep: null,
      completedSteps: [],
      totalSteps: steps
    })

    try {
      console.log('Updating listing with images:', generatedImages)
      console.log('Listing data:', listing)
      console.log('SKU:', currentSku)

      // Stream progress from backend as each step actually completes
      const data = await fetchWithProgress(
        '/api/create-listing',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            sku: currentSku,
            generated_images: generatedImages,
            listing: listing
          })
        },
        (event) => {
          setCreateListingProgress(prev => {
            const completed = [...prev.completedSteps]
            if (event.status === 'completed' && !completed.includes(event.step)) {
              completed.push(event.step)
            }
            return {
              ...prev,
              completedSteps: completed,
              currentStep: event.status === 'in_progress' ? event.step : prev.currentStep
            }
          })
        }
      )

      console.log('Create listing response:', data)

      // All steps complete
      setCreateListingProgress({
        isActive: false,
        currentStep: null,
        completedSteps: steps,
        totalSteps: steps
      })

      setListingData(data.listing_data)
      setEditableTitle(data.listing_data?.inventoryItem?.product?.title || '')
      setUploadResult(null) // Reset upload result when new listing is created
      
      // Refresh listings if we're on the upload tab
      if (activeTab === 'upload') {
        fetchAllListings()
      }
    } catch (err) {
      console.error('Error creating listing:', err)
      setError(err.message || 'An error occurred while creating listing')
      setCreateListingProgress({
        isActive: false,
        currentStep: null,
        completedSteps: [],
        totalSteps: steps
      })
    } finally {
      setIsCreatingListing(false)
    }
  }

  const handleTrimTitle = async () => {
    if (!editableTitle || !currentSku) return
    setIsTrimmingTitle(true)
    setError(null)
    try {
      const response = await fetch('/api/trim-title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: editableTitle, sku: currentSku })
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Failed to trim title')
      if (data.trimmed_title) {
        setEditableTitle(data.trimmed_title)
        // Update listingData in-place so the display stays in sync
        setListingData(prev => {
          if (!prev) return prev
          const updated = JSON.parse(JSON.stringify(prev))
          if (updated.inventoryItem?.product) {
            updated.inventoryItem.product.title = data.trimmed_title
          }
          return updated
        })
      }
    } catch (err) {
      console.error('Error trimming title:', err)
      setError(err.message || 'Failed to trim title')
    } finally {
      setIsTrimmingTitle(false)
    }
  }

  const handleSaveTitle = async () => {
    if (!editableTitle || !currentSku) return
    setIsSavingTitle(true)
    setError(null)
    try {
      const response = await fetch('/api/update-title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku: currentSku, title: editableTitle })
      })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Failed to update title')
      if (data.listing_data) {
        setListingData(data.listing_data)
        setEditableTitle(data.listing_data?.inventoryItem?.product?.title || editableTitle)
      }
    } catch (err) {
      console.error('Error saving title:', err)
      setError(err.message || 'Failed to save title')
    } finally {
      setIsSavingTitle(false)
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
    
    // Initialize progress tracking - steps match what the backend actually reports
    const steps = ['Preparing listing data', 'Uploading to eBay']
    setUploadProgress({
      isActive: true,
      currentStep: null,
      completedSteps: [],
      totalSteps: steps
    })

    try {
      console.log('Uploading listing to eBay with SKU:', sku)
      console.log('Listing data:', listingData)

      // Stream progress from backend as each step actually completes
      const data = await fetchWithProgress(
        '/api/upload-listing',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            sku: sku,
            filename: listingData?.filename || (listingData?.fileSku ? `${listingData.fileSku}.json` : null)
          })
        },
        (event) => {
          setUploadProgress(prev => {
            const completed = [...prev.completedSteps]
            if (event.status === 'completed' && !completed.includes(event.step)) {
              completed.push(event.step)
            }
            return {
              ...prev,
              completedSteps: completed,
              currentStep: event.status === 'in_progress' ? event.step : prev.currentStep
            }
          })
        }
      )

      console.log('Upload response:', data)

      if (!data.upload_result) {
        console.error('No upload_result in response:', data)
        throw new Error('Upload completed but no result returned')
      }

      // All steps complete
      setUploadProgress({
        isActive: false,
        currentStep: null,
        completedSteps: steps,
        totalSteps: steps
      })

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
      setUploadProgress({
        isActive: false,
        currentStep: null,
        completedSteps: [],
        totalSteps: steps
      })
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
            {fetchProgress.isActive && fetchProgress.totalSteps.length > 0 && (
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

        {photos.length > 0 && (
          <>
            <PhotoGallery
              photos={photos}
              editableCategories={editableCategories}
              onCategoryChange={handleCategoryChange}
              onConfirm={handleConfirmCategories}
              isConfirming={isConfirming}
              onPhotoClick={openLightbox}
              skippedPhotos={skippedPhotos}
              onSkipPhoto={handleSkipPhoto}
              useOriginalPhotos={useOriginalPhotos}
              onUseOriginalPhoto={handleUseOriginalPhoto}
              promptModifier={promptModifier}
              onPromptModifierChange={setPromptModifier}
            />
            {isConfirming && imageGenProgress.isActive && (
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
                          transition: 'width 0.3s ease'
                        }}
                      ></div>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Collapsible Image Editor */}
            <div className="editor-collapsible-panel">
              <button
                type="button"
                className="editor-toggle-button"
                onClick={() => setIsEditorOpen(prev => !prev)}
              >
                <span className={`editor-chevron ${isEditorOpen ? 'open' : ''}`}>&#9654;</span>
                Image Editor
              </button>
              {isEditorOpen && (
                <div className="editor-panel-body">
                  <ImageCanvas onAddToListing={handleAddToListing} originalPhotos={photos} />
                </div>
              )}
            </div>
          </>
        )}

        {generatedImages.length > 0 && (
          <div className="generated-images-section section-container new-listing-container">
            <h2 className="gallery-title">New Listing Photos</h2>
            <DragDropContext onDragEnd={handleDragEnd}>
              <Droppable droppableId="new-listing-photos" direction="horizontal">
                {(provided) => (
                  <div
                    className="gallery-grid"
                    ref={provided.innerRef}
                    {...provided.droppableProps}
                  >
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
                                checked={selectedImagesForRegen.includes(index)}
                                onChange={() => handleImageSelection(index)}
                                className="image-checkbox"
                              />
                              <span className="checkbox-overlay">Select to regenerate</span>
                            </label>
                            <div className="gallery-order-badge">{index + 1}</div>
                            <button
                              type="button"
                              className="listing-photo-delete-btn"
                              onClick={() => handleRemoveFromListing(index)}
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
                {isCreatingListing ? 'Updating Listing...' : 'Confirm and Edit Text'}
              </button>
              {isCreatingListing && createListingProgress.isActive && createListingProgress.totalSteps.length > 0 && (
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
                  <span className={`title-char-count ${editableTitle.length > 80 ? 'over-limit' : editableTitle.length >= 73 && editableTitle.length <= 80 ? 'good' : 'under'}`}>
                    {editableTitle.length} / 80
                    {editableTitle.length > 80 && ` (${editableTitle.length - 80} over)`}
                  </span>
                </div>
                <input
                  type="text"
                  className={`title-edit-input ${editableTitle.length > 80 ? 'over-limit' : ''}`}
                  value={editableTitle}
                  onChange={(e) => setEditableTitle(e.target.value)}
                  placeholder="Listing title..."
                />
                {editableTitle.length > 80 && (
                  <div className="title-warning">
                    Title exceeds 80 characters. Edit manually or use AI to trim it.
                  </div>
                )}
                <div className="title-edit-actions">
                  {editableTitle.length > 80 && (
                    <button
                      type="button"
                      className="title-trim-button"
                      onClick={handleTrimTitle}
                      disabled={isTrimmingTitle}
                    >
                      {isTrimmingTitle ? 'Trimming...' : 'AI Trim Title'}
                    </button>
                  )}
                  {editableTitle !== (listingData.inventoryItem?.product?.title || '') && (
                    <button
                      type="button"
                      className="title-save-button"
                      onClick={handleSaveTitle}
                      disabled={isSavingTitle}
                    >
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
              {uploadingSkus.has(listingData?.sku) && uploadProgress.isActive && uploadProgress.totalSteps.length > 0 && (
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
