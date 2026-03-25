import { useState, useEffect, useCallback, useRef } from 'react'
import { FilePlus, Upload, Route, FlaskConical, Settings } from 'lucide-react'
import CreateWorkflow from './components/CreateWorkflow'
import { MOCK_DATA } from './mockData'
import { createTestWorkflowState } from './testWorkflowState'
import { trimTransparentPadding } from './utils/trimImage'

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

/** Merge AI-generated URLs with originals: originals keep their URL; others consume aiGeneratedList in order. */
function mergeGeneratedWithOriginals(photosToProcess, aiGeneratedList, useOriginalPhotos, { allowPartial } = {}) {
  const merged = []
  let aiIndex = 0
  for (const photoUrl of photosToProcess) {
    if (useOriginalPhotos.has(photoUrl)) {
      merged.push(photoUrl)
    } else if (allowPartial && aiIndex < aiGeneratedList.length) {
      merged.push(aiGeneratedList[aiIndex++])
    } else if (!allowPartial) {
      merged.push(aiGeneratedList[aiIndex++])
    }
  }
  return merged
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
  const [isTrimming, setIsTrimming] = useState(false)
  const [isRegenerating, setIsRegenerating] = useState(false)
  const [isAddingNewVersions, setIsAddingNewVersions] = useState(false)
  const [isCreatingListing, setIsCreatingListing] = useState(false)
  const [listingData, setListingData] = useState(null)
  const [isUploading, setIsUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const [activeTab, setActiveTab] = useState('create') // 'create' | 'upload' | 'test-workflow' | 'testing' | 'settings'
  const [testingResult, setTestingResult] = useState(null)
  const [isTesting, setIsTesting] = useState(false)
  const [testingId, setTestingId] = useState('')
  const [appTokenResult, setAppTokenResult] = useState(null)
  const [isTestingAppToken, setIsTestingAppToken] = useState(false)
  const [userTokenResult, setUserTokenResult] = useState(null)
  const [isTestingUserToken, setIsTestingUserToken] = useState(false)
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

  // Token refresh panel state
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [tokenMessage, setTokenMessage] = useState(null)
  const [tokenInfo, setTokenInfo] = useState({ user_token_set: false, application_token_set: false, user_token: '', application_token: '' })
  const [tokenLastUpdated, setTokenLastUpdated] = useState(() => {
    const saved = localStorage.getItem('tokenLastUpdated')
    return saved ? parseInt(saved, 10) : null
  })
  const [, setTickCounter] = useState(0)

  // Re-render every 60s so the "ago" label and stale status stay current
  useEffect(() => {
    const interval = setInterval(() => setTickCounter(c => c + 1), 60000)
    return () => clearInterval(interval)
  }, [])

  const TOKEN_STALE_MS = 2 * 60 * 60 * 1000 // 2 hours

  const isTokenStale = tokenLastUpdated ? (Date.now() - tokenLastUpdated) > TOKEN_STALE_MS : true

  const formatTimeAgo = (timestamp) => {
    if (!timestamp) return 'never'
    const diff = Date.now() - timestamp
    const minutes = Math.floor(diff / 60000)
    if (minutes < 1) return 'just now'
    if (minutes < 60) return `${minutes}m ago`
    const hours = Math.floor(minutes / 60)
    if (hours < 24) return `${hours}h ${minutes % 60}m ago`
    const days = Math.floor(hours / 24)
    return `${days}d ${hours % 24}h ago`
  }

  const fetchTokenInfo = async () => {
    try {
      const res = await fetch('/api/tokens')
      const data = await res.json()
      if (data && !data.error) {
        setTokenInfo(data)
        if (typeof data.token_last_updated_ms === 'number' && Number.isFinite(data.token_last_updated_ms)) {
          setTokenLastUpdated(data.token_last_updated_ms)
          localStorage.setItem('tokenLastUpdated', data.token_last_updated_ms.toString())
        }
      }
    } catch (e) {
      // ignore
    }
  }

  const handleRefreshTokens = async () => {
    setIsRefreshing(true)
    setTokenMessage(null)
    try {
      const res = await fetch('/api/refresh-tokens', { method: 'POST' })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to refresh tokens')
      const now = Date.now()
      setTokenLastUpdated(now)
      localStorage.setItem('tokenLastUpdated', now.toString())
      const successCount = (data.user_token_refreshed ? 1 : 0) + (data.application_token_refreshed ? 1 : 0)
      if (successCount > 0) {
        setTokenMessage({ type: 'success', text: `Tokens refreshed! User: ${data.user_token_refreshed ? 'yes' : 'no'}, App: ${data.application_token_refreshed ? 'yes' : 'no'}` })
      } else {
        setTokenMessage({ type: 'error', text: data.errors?.join('; ') || 'Refresh failed' })
      }
      fetchTokenInfo()
    } catch (err) {
      setTokenMessage({ type: 'error', text: err.message || 'Failed to refresh tokens' })
    } finally {
      setIsRefreshing(false)
    }
  }

  // Auto-refresh tokens on mount if stale (>2h), only once per session
  const hasAutoRefreshed = useRef(false)
  useEffect(() => {
    if (hasAutoRefreshed.current) return
    const saved = localStorage.getItem('tokenLastUpdated')
    const lastUpdated = saved ? parseInt(saved, 10) : null
    const stale = lastUpdated ? (Date.now() - lastUpdated) > TOKEN_STALE_MS : true
    fetchTokenInfo()
    if (stale) {
      hasAutoRefreshed.current = true
      handleRefreshTokens()
    }
  }, [])

  const handleOpenEbayAuth = () => {
    window.open('https://developer.ebay.com/my/auth/?env=production&index=0', '_blank')
  }

  // Test workflow state (mock data, no API calls) — single state object
  const [testWf, setTestWf] = useState(createTestWorkflowState)
  const setTestKey = (key) => (valOrFn) =>
    setTestWf((w) => ({ ...w, [key]: typeof valOrFn === 'function' ? valOrFn(w[key]) : valOrFn }))
  const setTestListingId = setTestKey('listingId')
  const setTestPhotos = setTestKey('photos')
  const setTestCategories = setTestKey('categories')
  const setTestEditableCategories = setTestKey('editableCategories')
  const setTestListing = setTestKey('listing')
  const setTestLoading = setTestKey('loading')
  const setTestIsConfirming = setTestKey('isConfirming')
  const setTestError = setTestKey('error')
  const setTestGeneratedImages = setTestKey('generatedImages')
  const setTestCustomPrompt = setTestKey('customPrompt')
  const setTestSelectedImagesForRegen = setTestKey('selectedImagesForRegen')
  const setTestIsRegenerating = setTestKey('isRegenerating')
  const setTestIsTrimming = setTestKey('isTrimming')
  const setTestIsAddingNewVersions = setTestKey('isAddingNewVersions')
  const setTestUseRealEbayUpload = setTestKey('useRealEbayUpload')
  const setTestIsCreatingListing = setTestKey('isCreatingListing')
  const setTestListingData = setTestKey('listingData')
  const setTestUploadResult = setTestKey('uploadResult')
  const setTestCurrentSku = setTestKey('currentSku')
  const setTestSkippedPhotos = setTestKey('skippedPhotos')
  const setTestUseOriginalPhotos = setTestKey('useOriginalPhotos')
  const setTestPromptModifier = setTestKey('promptModifier')
  const setTestIsEditorOpen = setTestKey('isEditorOpen')
  const setTestEditableTitle = setTestKey('editableTitle')
  const setTestIsTrimmingTitle = setTestKey('isTrimmingTitle')
  const setTestIsSavingTitle = setTestKey('isSavingTitle')
  const setTestLightboxOpen = setTestKey('lightboxOpen')
  const setTestLightboxIndex = setTestKey('lightboxIndex')
  const setTestFetchProgress = setTestKey('fetchProgress')
  const setTestImageGenProgress = setTestKey('imageGenProgress')
  const setTestCreateListingProgress = setTestKey('createListingProgress')
  const setTestUploadProgress = setTestKey('uploadProgress')
  const setTestUploadingSkus = setTestKey('uploadingSkus')

  const {
    listingId: testListingId,
    photos: testPhotos,
    categories: testCategories,
    editableCategories: testEditableCategories,
    listing: testListing,
    loading: testLoading,
    isConfirming: testIsConfirming,
    error: testError,
    generatedImages: testGeneratedImages,
    customPrompt: testCustomPrompt,
    selectedImagesForRegen: testSelectedImagesForRegen,
    isRegenerating: testIsRegenerating,
    isTrimming: testIsTrimming,
    isAddingNewVersions: testIsAddingNewVersions,
    useRealEbayUpload: testUseRealEbayUpload,
    isCreatingListing: testIsCreatingListing,
    listingData: testListingData,
    uploadResult: testUploadResult,
    currentSku: testCurrentSku,
    skippedPhotos: testSkippedPhotos,
    useOriginalPhotos: testUseOriginalPhotos,
    promptModifier: testPromptModifier,
    isEditorOpen: testIsEditorOpen,
    editableTitle: testEditableTitle,
    isTrimmingTitle: testIsTrimmingTitle,
    isSavingTitle: testIsSavingTitle,
    lightboxOpen: testLightboxOpen,
    lightboxIndex: testLightboxIndex,
    fetchProgress: testFetchProgress,
    imageGenProgress: testImageGenProgress,
    createListingProgress: testCreateListingProgress,
    uploadProgress: testUploadProgress,
    uploadingSkus: testUploadingSkus,
  } = testWf

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

  const handleAddToOriginalPhotos = (newUrls) => {
    if (!newUrls?.length) return
    setPhotos((prev) => [...prev, ...newUrls])
    setEditableCategories((prev) => {
      const next = { ...prev }
      newUrls.forEach((url) => {
        next[url] = 'professional_image'
      })
      return next
    })
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
              
              setGeneratedImages(
                mergeGeneratedWithOriginals(photosToProcess, aiGeneratedList, useOriginalPhotos, { allowPartial: false })
              )
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
              setGeneratedImages(
                mergeGeneratedWithOriginals(photosToProcess, aiGeneratedList, useOriginalPhotos, { allowPartial: true })
              )
              
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
    setSelectedImagesForRegen((prev) => {
      if (prev.includes(index)) {
        return prev.filter(i => i !== index)
      } else {
        return [...prev, index]
      }
    })
  }

  const handleRegenerateImages = async () => {
    if (!customPrompt?.trim()) {
      setError('Please enter a prompt to guide the regeneration')
      return
    }
    const indices = selectedImagesForRegen.length > 0
      ? selectedImagesForRegen
      : generatedImages.map((_, i) => i)
    if (indices.length === 0) return

    setIsRegenerating(true)
    setError(null)

    try {
      const imagesToRegen = selectedImagesForRegen.map(index => generatedImages[index])
      const promptToUse = customPrompt.trim()
      console.log('Regenerating images:', imagesToRegen)
      console.log('Custom prompt:', promptToUse)

      const response = await fetch('/api/regenerate-images', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          image_urls: imagesToRegen,
          prompt: promptToUse
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
      indices.forEach((originalIndex, regenIndex) => {
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

  const handleTrimSelected = async () => {
    const indices = selectedImagesForRegen.length > 0
      ? selectedImagesForRegen
      : generatedImages.map((_, i) => i)
    if (indices.length === 0) return

    setIsTrimming(true)
    setError(null)

    try {
      const newImages = [...generatedImages]
      for (const index of indices) {
        const url = generatedImages[index]
        const resp = await fetch(url)
        const blob = await resp.blob()
        const dataUrl = await new Promise((resolve) => {
          const reader = new FileReader()
          reader.onload = (ev) => resolve(ev.target.result)
          reader.readAsDataURL(blob)
        })
        const trimmedUrl = await trimTransparentPadding(dataUrl)
        const trimmedBlob = await (await fetch(trimmedUrl)).blob()
        const formData = new FormData()
        formData.append('image', trimmedBlob, 'trimmed.png')
        const uploadResp = await fetch('/api/upload-image', { method: 'POST', body: formData })
        const uploadData = await uploadResp.json()
        if (!uploadResp.ok) throw new Error(uploadData.error || 'Upload failed')
        if (uploadData.url) newImages[index] = uploadData.url
      }
      setGeneratedImages(newImages)
    } catch (err) {
      console.error('Error trimming images:', err)
      setError(err.message || 'An error occurred while trimming images')
    } finally {
      setIsTrimming(false)
    }
  }

  const handleAddNewVersions = async () => {
    if (!customPrompt?.trim()) {
      setError('Please enter a prompt to guide the new version')
      return
    }
    if (!currentSku) {
      setError('SKU is required. Please fetch photos first.')
      return
    }

    const indices = selectedImagesForRegen.length > 0
      ? selectedImagesForRegen
      : generatedImages.map((_, i) => i)
    const imagesToRegen = indices.map(i => generatedImages[i]).filter(Boolean)
    if (imagesToRegen.length === 0) {
      setError('No valid images to regenerate')
      return
    }

    setIsAddingNewVersions(true)
    setError(null)

    try {
      const response = await fetch('/api/regenerate-images', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          image_urls: imagesToRegen,
          prompt: customPrompt.trim()
        })
      })

      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Failed to regenerate images')

      const newUrls = data.generated_images || []
      const nextImages = [...generatedImages, ...newUrls]
      setGeneratedImages(nextImages)
      setSelectedImagesForRegen([])

      const syncResp = await fetch('/api/update-listing-images', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sku: currentSku, image_urls: nextImages })
      })

      const syncData = await syncResp.json()
      if (!syncResp.ok) throw new Error(syncData.error || 'Failed to update listing file')
      if (syncData.listing_data) {
        setListingData(syncData.listing_data)
        setEditableTitle(syncData.listing_data?.inventoryItem?.product?.title || '')
      }

      await handleUploadToEbay(currentSku, syncData.listing_data)
    } catch (err) {
      console.error('Error in add new version:', err)
      setError(err.message || 'An error occurred while adding new version')
    } finally {
      setIsAddingNewVersions(false)
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
    if (tab === 'settings') {
      fetchTokenInfo()
      setTokenMessage(null)
    }
  }

  const navItemClass = (tab) =>
    `flex w-full items-center gap-3 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
      activeTab === tab
        ? 'bg-primary/10 font-semibold text-primary'
        : 'font-medium text-gray-700 hover:bg-gray-100'
    }`

  const handleTestAppToken = async () => {
    setIsTestingAppToken(true)
    setAppTokenResult(null)
    try {
      const response = await fetch('/api/test-application-token', { method: 'POST' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Test failed')
      setAppTokenResult(data.result)
    } catch (err) {
      setAppTokenResult({ ok: false, message: err.message })
    } finally {
      setIsTestingAppToken(false)
    }
  }

  const handleTestUserToken = async () => {
    setIsTestingUserToken(true)
    setUserTokenResult(null)
    try {
      const response = await fetch('/api/test-user-token', { method: 'POST' })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Test failed')
      setUserTokenResult(data.result)
    } catch (err) {
      setUserTokenResult({ ok: false, message: err.message })
    } finally {
      setIsTestingUserToken(false)
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

  // Test workflow mock handlers (no API calls)
  const testHandleSubmit = (e) => {
    e.preventDefault()
    if (!testListingId.trim()) {
      setTestError('Please enter an eBay listing ID or URL (any value works for testing)')
      return
    }
    setTestLoading(true)
    setTestError(null)
    const steps = ['Fetching listing from eBay', 'Creating initial JSON file', 'Categorizing images']
    setTestFetchProgress({ isActive: true, currentStep: steps[0], completedSteps: [], totalSteps: steps })
    setTimeout(() => {
      setTestFetchProgress(prev => ({ ...prev, completedSteps: [steps[0]], currentStep: steps[1] }))
    }, 400)
    setTimeout(() => {
      setTestFetchProgress(prev => ({ ...prev, completedSteps: [steps[0], steps[1]], currentStep: steps[2] }))
    }, 800)
    setTimeout(() => {
      setTestPhotos(MOCK_DATA.photos)
      setTestCategories(MOCK_DATA.categories)
      setTestEditableCategories({ ...MOCK_DATA.categories })
      setTestListing(MOCK_DATA.listing)
      setTestCurrentSku(MOCK_DATA.sku)
      setTestGeneratedImages([])
      const autoSkip = new Set()
      for (const [url, cat] of Object.entries(MOCK_DATA.categories)) {
        if (cat === 'real_world_image' || cat === 'edited_image') autoSkip.add(url)
      }
      setTestSkippedPhotos(autoSkip)
      setTestFetchProgress({ isActive: false, currentStep: null, completedSteps: steps, totalSteps: steps })
      setTestLoading(false)
    }, 1500)
  }

  const testHandleConfirmCategories = () => {
    const photosToProcess = testPhotos.filter(url => !testSkippedPhotos.has(url))
    const needsAI = photosToProcess.filter(url => !testUseOriginalPhotos.has(url))
    if (photosToProcess.length === 0) {
      setTestError('All photos are skipped. Include at least one photo.')
      return
    }
    if (needsAI.length === 0) {
      setTestGeneratedImages(photosToProcess)
      setTestCategories(testEditableCategories)
      setTestIsConfirming(false)
      return
    }
    setTestIsConfirming(true)
    setTestError(null)
    const total = needsAI.length
    setTestImageGenProgress({ isActive: true, taskId: 'mock', total, completed: 0, currentGenerating: [] })
    let completed = 0
    const interval = setInterval(() => {
      completed += 1
      setTestImageGenProgress(prev => ({ ...prev, completed }))
      if (completed >= total) {
        clearInterval(interval)
        const merged = []
        let aiIdx = 0
        for (const url of photosToProcess) {
          merged.push(testUseOriginalPhotos.has(url) ? url : MOCK_DATA.generatedImages[aiIdx++] || url)
        }
        setTestGeneratedImages(merged)
        setTestCategories(testEditableCategories)
        setTestImageGenProgress({ isActive: false, taskId: null, total, completed, currentGenerating: [] })
        setTestIsConfirming(false)
      }
    }, 500)
  }

  const testHandleConfirmAndEditText = () => {
    if (testGeneratedImages.length === 0) {
      setTestError('No generated images to add to listing')
      return
    }
    setTestIsCreatingListing(true)
    setTestError(null)
    const steps = ['Updating images', 'Generating optimized text', 'Updating metadata', 'Updating aspects']
    setTestCreateListingProgress({ isActive: true, currentStep: steps[0], completedSteps: [], totalSteps: steps })
    let stepIdx = 0
    const interval = setInterval(() => {
      stepIdx += 1
      setTestCreateListingProgress(prev => ({
        ...prev,
        completedSteps: steps.slice(0, stepIdx),
        currentStep: steps[stepIdx] || null
      }))
      if (stepIdx >= steps.length) {
        clearInterval(interval)
        const listingData = { ...MOCK_DATA.listingData, inventoryItem: { ...MOCK_DATA.listingData.inventoryItem, product: { ...MOCK_DATA.listingData.inventoryItem.product, imageUrls: testGeneratedImages } } }
        setTestListingData(listingData)
        setTestEditableTitle(listingData.inventoryItem?.product?.title || '')
        setTestUploadResult(null)
        setTestCreateListingProgress({ isActive: false, currentStep: null, completedSteps: steps, totalSteps: steps })
        setTestIsCreatingListing(false)
      }
    }, 400)
  }

  const testHandleUploadToEbay = (sku, listingData) => {
    setTestUploadingSkus(prev => new Set(prev).add(sku))
    setTestError(null)
    const steps = ['Preparing listing data', 'Uploading to eBay']
    setTestUploadProgress({ isActive: true, currentStep: steps[0], completedSteps: [], totalSteps: steps })
    setTimeout(() => {
      setTestUploadProgress(prev => ({ ...prev, completedSteps: [steps[0]], currentStep: steps[1] }))
    }, 400)
    setTimeout(() => {
      setTestUploadResult(MOCK_DATA.uploadResult)
      setTestUploadProgress({ isActive: false, currentStep: null, completedSteps: steps, totalSteps: steps })
      setTestUploadingSkus(prev => { const s = new Set(prev); s.delete(sku); return s })
    }, 1000)
  }

  const testHandleRegenerateImages = () => {
    if (!testCustomPrompt.trim() || testSelectedImagesForRegen.length === 0) {
      setTestError('Please enter a prompt and select at least one image')
      return
    }
    setTestIsRegenerating(true)
    setTestError(null)
    setTimeout(() => {
      const newImages = [...testGeneratedImages]
      const placeholderUrls = ['https://picsum.photos/seed/regen1/400/400', 'https://picsum.photos/seed/regen2/400/400']
      testSelectedImagesForRegen.forEach((idx, i) => {
        if (i < placeholderUrls.length) newImages[idx] = placeholderUrls[i]
      })
      setTestGeneratedImages(newImages)
      setTestSelectedImagesForRegen([])
      setTestCustomPrompt('')
      setTestIsRegenerating(false)
    }, 800)
  }

  const testHandleAddNewVersions = () => {
    if (!testCustomPrompt?.trim()) {
      setTestError('Please enter a prompt')
      return
    }
    const indices = testSelectedImagesForRegen.length > 0
      ? testSelectedImagesForRegen
      : testGeneratedImages.map((_, i) => i)
    if (indices.length === 0) return
    setTestIsAddingNewVersions(true)
    setTestError(null)
    const placeholderUrls = ['https://picsum.photos/seed/newver1/400/400', 'https://picsum.photos/seed/newver2/400/400']
    const toAppend = indices.slice(0, placeholderUrls.length).map((_, i) => placeholderUrls[i])
    setTimeout(() => {
      setTestGeneratedImages(prev => {
        const updated = [...prev, ...toAppend]
        const listingData = { ...MOCK_DATA.listingData, inventoryItem: { ...MOCK_DATA.listingData.inventoryItem, product: { ...MOCK_DATA.listingData.inventoryItem.product, imageUrls: updated } } }
        setTestListingData(listingData)
        setTestEditableTitle(listingData.inventoryItem?.product?.title || '')
        testHandleUploadToEbay(testCurrentSku || MOCK_DATA.listingData?.sku, listingData)
        return updated
      })
      setTestIsAddingNewVersions(false)
    }, 600)
  }

  const testHandleTrimSelected = async () => {
    const indices = testSelectedImagesForRegen.length > 0
      ? testSelectedImagesForRegen
      : testGeneratedImages.map((_, i) => i)
    if (indices.length === 0) return
    setTestIsTrimming(true)
    setTestError(null)
    try {
      const newImages = [...testGeneratedImages]
      for (const index of indices) {
        const url = testGeneratedImages[index]
        const resp = await fetch(url)
        const blob = await resp.blob()
        const dataUrl = await new Promise((resolve) => {
          const reader = new FileReader()
          reader.onload = (ev) => resolve(ev.target.result)
          reader.readAsDataURL(blob)
        })
        const trimmedUrl = await trimTransparentPadding(dataUrl)
        newImages[index] = trimmedUrl
      }
      setTestGeneratedImages(newImages)
    } catch (err) {
      console.error('Error trimming test images:', err)
      setTestError(err.message || 'An error occurred while trimming images')
    } finally {
      setTestIsTrimming(false)
    }
  }

  return (
    <div className="flex min-h-screen">
      <aside
        className="sticky top-0 flex h-screen w-60 shrink-0 flex-col rounded-tr-xl border-r border-gray-200 bg-white shadow-sm"
        aria-label="Main navigation"
      >
        <div className="flex items-center px-4 py-5">
          <div
            className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-primary-dark text-sm font-bold tracking-tight text-white"
            aria-hidden
          >
            AR
          </div>
        </div>
        <nav className="flex flex-1 flex-col px-3 pb-4">
          <p className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider text-gray-400">Research</p>
          <div className="flex flex-col gap-0.5">
            <button
              type="button"
              className={navItemClass('create')}
              onClick={() => handleTabChange('create')}
            >
              <FilePlus size={20} strokeWidth={1.75} className="shrink-0" />
              <span>Create Listing</span>
            </button>
            <button
              type="button"
              className={navItemClass('upload')}
              onClick={() => handleTabChange('upload')}
            >
              <Upload size={20} strokeWidth={1.75} className="shrink-0" />
              <span>Upload Listings</span>
            </button>
            <button
              type="button"
              className={navItemClass('test-workflow')}
              onClick={() => handleTabChange('test-workflow')}
            >
              <Route size={20} strokeWidth={1.75} className="shrink-0" />
              <span>Test Workflow</span>
            </button>
            <button
              type="button"
              className={navItemClass('testing')}
              onClick={() => handleTabChange('testing')}
            >
              <FlaskConical size={20} strokeWidth={1.75} className="shrink-0" />
              <span>Testing</span>
            </button>
          </div>
          <div className="mt-auto border-t border-gray-200 pt-3">
            <button
              type="button"
              className={`${navItemClass('settings')} relative`}
              onClick={() => handleTabChange('settings')}
              title={`eBay tokens – last updated: ${formatTimeAgo(tokenLastUpdated)}`}
            >
              <Settings size={20} strokeWidth={1.75} className="shrink-0" />
              <span>Settings</span>
              {isTokenStale && (
                <span
                  className="absolute right-2.5 top-1/2 h-2 w-2 -translate-y-1/2 animate-stale-pulse rounded-full bg-danger ring-2 ring-white"
                  aria-label="Tokens may be stale"
                />
              )}
            </button>
          </div>
        </nav>
      </aside>

      <main className="min-h-screen flex-1 overflow-auto bg-gray-50">
        <div className="mx-auto flex w-full max-w-[1200px] flex-col px-6 py-6 md:px-8 md:py-8">
        {activeTab === 'test-workflow' && (
          <CreateWorkflow
            listingId={testListingId}
            photos={testPhotos}
            categories={testCategories}
            editableCategories={testEditableCategories}
            listing={testListing}
            currentSku={testCurrentSku}
            skippedPhotos={testSkippedPhotos}
            useOriginalPhotos={testUseOriginalPhotos}
            promptModifier={testPromptModifier}
            generatedImages={testGeneratedImages}
            selectedImagesForRegen={testSelectedImagesForRegen}
            customPrompt={testCustomPrompt}
            loading={testLoading}
            error={testError}
            isConfirming={testIsConfirming}
            isRegenerating={testIsRegenerating}
            isTrimming={testIsTrimming}
            isAddingNewVersions={testIsAddingNewVersions}
            isCreatingListing={testIsCreatingListing}
            listingData={testListingData}
            editableTitle={testEditableTitle}
            uploadResult={testUploadResult}
            isEditorOpen={testIsEditorOpen}
            fetchProgress={testFetchProgress}
            imageGenProgress={testImageGenProgress}
            createListingProgress={testCreateListingProgress}
            uploadProgress={testUploadProgress}
            uploadingSkus={testUploadingSkus}
            isTrimmingTitle={testIsTrimmingTitle}
            isSavingTitle={testIsSavingTitle}
            onListingIdChange={setTestListingId}
            onSubmit={testHandleSubmit}
            onCategoryChange={(url, cat) => setTestEditableCategories(prev => ({ ...prev, [url]: cat }))}
            onSkipPhoto={(url) => setTestSkippedPhotos(prev => { const s = new Set(prev); s.has(url) ? s.delete(url) : s.add(url); return s })}
            onUseOriginalPhoto={(url) => setTestUseOriginalPhotos(prev => { const s = new Set(prev); s.has(url) ? s.delete(url) : s.add(url); return s })}
            onPromptModifierChange={setTestPromptModifier}
            onConfirmCategories={testHandleConfirmCategories}
            onImageSelection={(idx) => setTestSelectedImagesForRegen(prev => prev.includes(idx) ? prev.filter(i => i !== idx) : [...prev, idx])}
            onRegenerateImages={testHandleRegenerateImages}
            onTrimSelected={testHandleTrimSelected}
            onAddNewVersions={testHandleAddNewVersions}
            onCustomPromptChange={setTestCustomPrompt}
            onDragEnd={(result) => { if (!result.destination) return; const src = result.source.index, dest = result.destination.index; if (src === dest) return; setTestGeneratedImages(prev => { const arr = [...prev]; const [moved] = arr.splice(src, 1); arr.splice(dest, 0, moved); return arr }) }}
            onRemoveFromListing={(idx) => { setTestGeneratedImages(prev => prev.filter((_, i) => i !== idx)); setTestSelectedImagesForRegen([]) }}
            onAddToListing={(url) => setTestGeneratedImages(prev => [...prev, url])}
            onAddToOriginalPhotos={(urls) => {
              if (!urls?.length) return
              setTestPhotos(prev => [...prev, ...urls])
              setTestEditableCategories(prev => {
                const next = { ...prev }
                urls.forEach(url => { next[url] = 'professional_image' })
                return next
              })
            }}
            onConfirmAndEditText={testHandleConfirmAndEditText}
            onEditableTitleChange={setTestEditableTitle}
            onTrimTitle={() => setTestEditableTitle(prev => prev.slice(0, 80))}
            onSaveTitle={() => setTestListingData(prev => prev ? { ...prev, inventoryItem: { ...prev.inventoryItem, product: { ...prev.inventoryItem?.product, title: testEditableTitle } } } : prev)}
            onUploadToEbay={testHandleUploadToEbay}
            onEditorToggle={() => setTestIsEditorOpen(prev => !prev)}
            useRealEbayUpload={testUseRealEbayUpload}
            onUseRealEbayUploadChange={setTestUseRealEbayUpload}
            onPhotoClick={(idx) => { setTestLightboxIndex(idx); setTestLightboxOpen(true) }}
            onCloseLightbox={() => setTestLightboxOpen(false)}
            onNavigateLightbox={(dir) => setTestLightboxIndex(prev => dir === 'next' ? (prev + 1) % testPhotos.length : (prev - 1 + testPhotos.length) % testPhotos.length)}
            lightboxOpen={testLightboxOpen}
            lightboxIndex={testLightboxIndex}
          />
        )}

        {activeTab === 'upload' && (
          <div>
            <h2 className="mb-5 text-xl font-semibold text-gray-800">Generated Listings</h2>

            {loadingListings ? (
              <div className="flex flex-col items-center justify-center gap-4 py-12">
                <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-primary" />
                <p className="text-gray-600">Loading listings...</p>
              </div>
            ) : allListings.length === 0 ? (
              <div className="rounded-xl border border-gray-200 bg-gray-50 p-8 text-center">
                <p className="text-gray-600">No generated listings found. Create a listing first!</p>
              </div>
            ) : (
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                {allListings.map((listing) => (
                  <div
                    key={listing.sku}
                    className="cursor-pointer rounded-xl border border-gray-200 bg-white p-5 shadow-sm transition-all hover:shadow-md"
                    onClick={() => handleListingClick(listing)}
                  >
                    <div className="mb-3 flex items-start justify-between gap-2">
                      <h3 className="flex-1 text-lg font-semibold text-gray-800">{listing.title}</h3>
                      <span className="rounded bg-gray-100 px-2 py-0.5 text-sm font-mono text-gray-600">
                        {listing.sku}
                      </span>
                    </div>
                    <div className="mb-4 space-y-1 text-sm text-gray-600">
                      <div>
                        <strong>Price:</strong> ${listing.price}
                      </div>
                      <div>
                        <strong>Category:</strong> {listing.categoryId}
                      </div>
                      <div>
                        <strong>Images:</strong> {listing.imageCount}
                      </div>
                      <div>
                        <strong>Created:</strong>{' '}
                        {listing.createdDateTime
                          ? new Date(listing.createdDateTime).toLocaleString()
                          : 'N/A'}
                      </div>
                    </div>
                    <div className="flex flex-col gap-2">
                      <button
                        type="button"
                        className="w-full rounded-lg bg-gradient-to-br from-primary to-primary-dark px-4 py-2 font-semibold text-white shadow transition-all hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60 disabled:transform-none"
                        onClick={(e) => {
                          e.stopPropagation()
                          handleUploadToEbay(listing.sku, listing)
                        }}
                        disabled={uploadingSkus.has(listing.sku)}
                      >
                        {uploadingSkus.has(listing.sku) ? 'Uploading...' : 'Upload to eBay'}
                      </button>
                      {uploadResults[listing.sku] && (
                        <div className="flex items-center gap-3 rounded-lg border border-green-200 bg-green-50 p-3">
                          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-green-500 text-lg font-bold text-white">
                            ✓
                          </div>
                          <div className="flex-1 text-sm">
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
                                  className="font-semibold text-primary underline hover:no-underline"
                                >
                                  View on eBay →
                                </a>
                              </div>
                            )}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Listing Detail Modal */}
        {selectedListing && (
          <div
            className="fixed inset-0 z-[1000] flex items-center justify-center bg-black/60 p-4"
            onClick={closeListingDetail}
          >
            <div
              className="flex max-h-[90vh] max-w-[90%] flex-col overflow-hidden rounded-xl bg-white shadow-2xl animate-slide-up md:max-w-[95%]"
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between border-b-2 border-gray-200 p-4">
                <h2 className="m-0 text-xl font-semibold text-gray-800 md:text-2xl">
                  Listing Details: {selectedListing.sku}
                </h2>
                <button
                  className="flex h-10 w-10 items-center justify-center rounded-full border-none bg-gray-100 text-2xl text-gray-600 transition-all hover:rotate-90 hover:bg-gray-200 hover:text-gray-800"
                  onClick={closeListingDetail}
                >
                  ×
                </button>
              </div>

              {loadingListingDetail ? (
                <div className="flex flex-col items-center justify-center gap-4 py-12">
                  <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-primary" />
                  <p className="text-gray-600">Loading listing details...</p>
                </div>
              ) : listingDetailData ? (
                <div className="flex-1 overflow-auto p-4">
                  <pre className="overflow-x-auto whitespace-pre-wrap break-words rounded-lg border border-gray-200 bg-gray-50 p-4 font-mono text-sm text-gray-800">
                    {JSON.stringify(listingDetailData, null, 2)}
                  </pre>
                </div>
              ) : (
                <div className="p-8 text-center text-danger">Failed to load listing details</div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'testing' && (
          <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
            <h2 className="mb-5 text-xl font-semibold text-gray-800">Testing</h2>
            <div className="flex flex-col gap-6">
              <p className="text-gray-600">Use this section to test functions and debug code.</p>

              <div className="flex flex-col gap-2">
                <label htmlFor="testing-id" className="text-sm font-semibold text-gray-700">
                  ID (optional):
                </label>
                <input
                  id="testing-id"
                  type="text"
                  className="rounded-lg border-2 border-gray-300 px-4 py-2 transition-colors focus:border-primary focus:outline-none disabled:bg-gray-100"
                  value={testingId}
                  onChange={(e) => setTestingId(e.target.value)}
                  placeholder="Enter ID parameter..."
                  disabled={isTesting}
                />
              </div>
              <button
                type="button"
                className="w-fit rounded-lg bg-gradient-to-br from-primary to-primary-dark px-6 py-2 font-semibold text-white shadow transition-all hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
                onClick={handleTestingFunction}
                disabled={isTesting}
              >
                {isTesting ? 'Running...' : 'Run Testing Function'}
              </button>
              {testingResult && (
                <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                  <h3 className="mb-2 font-semibold text-gray-800">Result:</h3>
                  <pre className="overflow-x-auto whitespace-pre-wrap text-sm text-gray-700">
                    {typeof testingResult === 'string'
                      ? testingResult
                      : JSON.stringify(testingResult, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'settings' && (
          <div className="animate-token-slide-down rounded-xl border border-gray-200 bg-white p-6 shadow-sm md:p-8">
            <div className="mb-6 flex flex-wrap items-center justify-between gap-2">
              <h2 className="text-xl font-semibold text-gray-800">Settings</h2>
            </div>
            <div className="rounded-xl border border-gray-200 bg-gray-50/80 p-5">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
                <h3 className="m-0 text-lg font-semibold text-gray-800">eBay Token Management</h3>
                <button
                  type="button"
                  className="cursor-pointer rounded-md border border-gray-200 bg-white px-4 py-2 text-sm font-semibold text-primary shadow-sm transition-all hover:-translate-y-0.5 hover:bg-gray-50 hover:shadow-md"
                  onClick={handleOpenEbayAuth}
                >
                  Open eBay Auth Page
                </button>
              </div>

              <div className="mb-4 flex flex-col gap-1.5 font-mono text-sm">
                <span
                  className={`rounded px-2 py-1 break-all ${
                    tokenInfo.user_token_set ? 'bg-emerald-100 text-emerald-900' : 'bg-red-100 text-red-900'
                  }`}
                >
                  user_token: {tokenInfo.user_token_set ? tokenInfo.user_token : 'not set'}
                </span>
                <span
                  className={`rounded px-2 py-1 break-all ${
                    tokenInfo.application_token_set ? 'bg-emerald-100 text-emerald-900' : 'bg-red-100 text-red-900'
                  }`}
                >
                  application_token: {tokenInfo.application_token_set ? tokenInfo.application_token : 'not set'}
                </span>
              </div>

              <div
                className={`mb-4 rounded-md px-2.5 py-1.5 text-sm font-semibold ${
                  isTokenStale
                    ? 'border border-red-200 bg-red-50 text-red-800'
                    : 'border border-emerald-200 bg-emerald-50 text-emerald-800'
                }`}
              >
                Last updated:{' '}
                {tokenLastUpdated
                  ? `${formatTimeAgo(tokenLastUpdated)}${isTokenStale ? ' — tokens may be expired!' : ''}`
                  : 'never'}
              </div>

              <div className="mt-3 flex flex-col gap-3">
                <button
                  type="button"
                  className="cursor-pointer rounded-lg border border-gray-200 bg-white px-6 py-2.5 text-sm font-semibold text-primary shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:transform-none"
                  onClick={handleRefreshTokens}
                  disabled={isRefreshing}
                >
                  {isRefreshing ? 'Refreshing...' : 'Refresh Tokens'}
                </button>
                <div className="flex flex-wrap gap-3">
                  <button
                    type="button"
                    className="rounded-lg bg-gradient-to-br from-primary to-primary-dark px-4 py-2 text-sm font-semibold text-white shadow transition-all hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={handleTestAppToken}
                    disabled={isTestingAppToken}
                  >
                    {isTestingAppToken ? 'Testing...' : 'Test Application Token'}
                  </button>
                  <button
                    type="button"
                    className="rounded-lg bg-gradient-to-br from-primary to-primary-dark px-4 py-2 text-sm font-semibold text-white shadow transition-all hover:-translate-y-0.5 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
                    onClick={handleTestUserToken}
                    disabled={isTestingUserToken}
                  >
                    {isTestingUserToken ? 'Testing...' : 'Test User Token'}
                  </button>
                </div>
                <div className="flex flex-wrap gap-4 pt-1">
                  {appTokenResult && (
                    <div
                      className={`rounded-lg border px-3 py-2 text-sm ${appTokenResult.ok ? 'border-emerald-300 bg-emerald-50 text-emerald-800' : 'border-red-300 bg-red-50 text-red-800'}`}
                    >
                      <span className="font-medium">Application token:</span> {appTokenResult.message}
                    </div>
                  )}
                  {userTokenResult && (
                    <div
                      className={`rounded-lg border px-3 py-2 text-sm ${userTokenResult.ok ? 'border-emerald-300 bg-emerald-50 text-emerald-800' : 'border-red-300 bg-red-50 text-red-800'}`}
                    >
                      <span className="font-medium">User token:</span> {userTokenResult.message}
                    </div>
                  )}
                </div>
              </div>

              {tokenMessage && (
                <div
                  className={`mt-3 rounded-md px-3 py-2 text-sm font-medium ${
                    tokenMessage.type === 'success'
                      ? 'border border-emerald-200 bg-emerald-50 text-emerald-800'
                      : 'border border-red-200 bg-red-50 text-red-800'
                  }`}
                >
                  {tokenMessage.text}
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'create' && (
          <CreateWorkflow
            listingId={listingId}
            photos={photos}
            categories={categories}
            editableCategories={editableCategories}
            listing={listing}
            currentSku={currentSku}
            skippedPhotos={skippedPhotos}
            useOriginalPhotos={useOriginalPhotos}
            promptModifier={promptModifier}
            generatedImages={generatedImages}
            selectedImagesForRegen={selectedImagesForRegen}
            customPrompt={customPrompt}
            loading={loading}
            error={error}
            isConfirming={isConfirming}
            isRegenerating={isRegenerating}
            isTrimming={isTrimming}
            isAddingNewVersions={isAddingNewVersions}
            isCreatingListing={isCreatingListing}
            listingData={listingData}
            editableTitle={editableTitle}
            uploadResult={uploadResult}
            isEditorOpen={isEditorOpen}
            fetchProgress={fetchProgress}
            imageGenProgress={imageGenProgress}
            createListingProgress={createListingProgress}
            uploadProgress={uploadProgress}
            uploadingSkus={uploadingSkus}
            isTrimmingTitle={isTrimmingTitle}
            isSavingTitle={isSavingTitle}
            onListingIdChange={setListingId}
            onSubmit={handleSubmit}
            onCategoryChange={handleCategoryChange}
            onSkipPhoto={handleSkipPhoto}
            onUseOriginalPhoto={handleUseOriginalPhoto}
            onPromptModifierChange={setPromptModifier}
            onConfirmCategories={handleConfirmCategories}
            onImageSelection={handleImageSelection}
            onRegenerateImages={handleRegenerateImages}
            onTrimSelected={handleTrimSelected}
            onAddNewVersions={handleAddNewVersions}
            onCustomPromptChange={setCustomPrompt}
            onDragEnd={handleDragEnd}
            onRemoveFromListing={handleRemoveFromListing}
            onAddToListing={handleAddToListing}
            onAddToOriginalPhotos={handleAddToOriginalPhotos}
            onConfirmAndEditText={handleConfirmAndEditText}
            onEditableTitleChange={setEditableTitle}
            onTrimTitle={handleTrimTitle}
            onSaveTitle={handleSaveTitle}
            onUploadToEbay={handleUploadToEbay}
            onEditorToggle={() => setIsEditorOpen((prev) => !prev)}
            onPhotoClick={openLightbox}
            onCloseLightbox={closeLightbox}
            onNavigateLightbox={navigateLightbox}
            lightboxOpen={lightboxOpen}
            lightboxIndex={lightboxIndex}
          />
        )}
        </div>
      </main>
    </div>
  )
}

export default App
