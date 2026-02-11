import { useState, useRef, useEffect, useCallback } from 'react'
import { Canvas, FabricImage } from 'fabric'

const DISPLAY_MAX = 540 // max pixel width for the on-screen canvas
let imageIdCounter = 0

export default function ImageCanvas({ onAddToListing, originalPhotos = [] }) {
  // Canvas settings
  const [canvasWidth, setCanvasWidth] = useState(1080)
  const [canvasHeight, setCanvasHeight] = useState(1080)
  const [bgColor, setBgColor] = useState('#FFFFFF')
  const [showSettings, setShowSettings] = useState(false)

  // Temp settings (only applied on confirm)
  const [tempWidth, setTempWidth] = useState(1080)
  const [tempHeight, setTempHeight] = useState(1080)
  const [tempBgColor, setTempBgColor] = useState('#FFFFFF')

  // Uploaded image pool
  const [uploadedImages, setUploadedImages] = useState([]) // { id, dataUrl, name }
  const [selectedIds, setSelectedIds] = useState(new Set())
  const [processingIds, setProcessingIds] = useState(new Set()) // IDs currently having bg removed

  // Original photo selection
  const [selectedOriginalPhotos, setSelectedOriginalPhotos] = useState(new Set())
  const [isAddingOriginals, setIsAddingOriginals] = useState(false)

  // Loading states
  const [isProcessing, setIsProcessing] = useState(false)
  const [isCompiling, setIsCompiling] = useState(false)
  const [processingCount, setProcessingCount] = useState(0)
  const [processingTotal, setProcessingTotal] = useState(0)

  // Refs
  const canvasRef = useRef(null)
  const fabricRef = useRef(null)
  const uploadInputRef = useRef(null)
  const settingsRef = useRef(null)

  // Compute display scale
  const displayScale = Math.min(DISPLAY_MAX / canvasWidth, DISPLAY_MAX / canvasHeight, 1)
  const displayWidth = Math.round(canvasWidth * displayScale)
  const displayHeight = Math.round(canvasHeight * displayScale)

  // Initialize fabric canvas at full logical resolution
  useEffect(() => {
    if (!canvasRef.current) return

    const fc = new Canvas(canvasRef.current, {
      width: canvasWidth,
      height: canvasHeight,
      backgroundColor: bgColor,
      selection: true,
    })

    // Apply CSS transform to scale down for display (keeps logical coords at full res)
    const wrapper = fc.wrapperEl
    if (wrapper) {
      wrapper.style.transformOrigin = 'top left'
      wrapper.style.transform = `scale(${displayScale})`
    }

    fabricRef.current = fc

    return () => {
      fc.dispose()
      fabricRef.current = null
    }
    // Only re-init when dimensions or bg changes
  }, [canvasWidth, canvasHeight, bgColor, displayScale])

  // Delete key handler
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Delete' && fabricRef.current) {
        const active = fabricRef.current.getActiveObjects()
        if (active && active.length > 0) {
          active.forEach((obj) => fabricRef.current.remove(obj))
          fabricRef.current.discardActiveObject()
          fabricRef.current.requestRenderAll()
        }
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  // Close settings popover on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (showSettings && settingsRef.current && !settingsRef.current.contains(e.target)) {
        setShowSettings(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [showSettings])

  // Helper: add an image (as data URL) to the fabric canvas
  const addImageToCanvas = useCallback((dataUrl) => {
    const fc = fabricRef.current
    if (!fc) return

    const imgEl = new Image()
    imgEl.onload = () => {
      // Scale to fit 90% of the canvas, preserving aspect ratio
      const scaleX = (canvasWidth * 0.9) / imgEl.width
      const scaleY = (canvasHeight * 0.9) / imgEl.height
      const scale = Math.min(scaleX, scaleY)

      const scaledW = imgEl.width * scale
      const scaledH = imgEl.height * scale

      const fabricImg = new FabricImage(imgEl, {
        scaleX: scale,
        scaleY: scale,
        left: (canvasWidth - scaledW) / 2,
        top: (canvasHeight - scaledH) / 2,
      })

      fc.add(fabricImg)
      fc.setActiveObject(fabricImg)
      fc.requestRenderAll()
    }
    imgEl.src = dataUrl
  }, [canvasWidth, canvasHeight])

  // "Upload Images" handler: add files to the image pool
  const handleUploadImages = useCallback((e) => {
    const files = Array.from(e.target.files || [])
    if (files.length === 0) return

    files.forEach((file) => {
      const reader = new FileReader()
      reader.onload = (ev) => {
        const id = ++imageIdCounter
        setUploadedImages((prev) => [
          ...prev,
          { id, dataUrl: ev.target.result, name: file.name },
        ])
      }
      reader.readAsDataURL(file)
    })

    // Reset so the same files can be re-selected
    e.target.value = ''
  }, [])

  // Toggle original photo selection
  const toggleOriginalPhotoSelection = useCallback((url) => {
    setSelectedOriginalPhotos((prev) => {
      const next = new Set(prev)
      if (next.has(url)) {
        next.delete(url)
      } else {
        next.add(url)
      }
      return next
    })
  }, [])

  // Add selected original photos to the image pool
  const handleAddOriginalsToPool = useCallback(async () => {
    if (selectedOriginalPhotos.size === 0) return
    setIsAddingOriginals(true)

    const urls = Array.from(selectedOriginalPhotos)
    for (const url of urls) {
      try {
        const response = await fetch(url)
        const blob = await response.blob()
        const dataUrl = await new Promise((resolve) => {
          const reader = new FileReader()
          reader.onload = (ev) => resolve(ev.target.result)
          reader.readAsDataURL(blob)
        })
        const id = ++imageIdCounter
        const name = url.split('/').pop() || `original-${id}.jpg`
        setUploadedImages((prev) => [...prev, { id, dataUrl, name }])
      } catch (err) {
        console.error('Error fetching original photo:', url, err)
      }
    }

    setSelectedOriginalPhotos(new Set())
    setIsAddingOriginals(false)
  }, [selectedOriginalPhotos])

  // Toggle image selection in the pool
  const toggleImageSelection = useCallback((id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }, [])

  // Select / deselect all
  const selectAll = useCallback(() => {
    setSelectedIds(new Set(uploadedImages.map((img) => img.id)))
  }, [uploadedImages])

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set())
  }, [])

  // Remove selected images from the pool
  const removeFromPool = useCallback(() => {
    setUploadedImages((prev) => prev.filter((img) => !selectedIds.has(img.id)))
    setSelectedIds(new Set())
  }, [selectedIds])

  // "Add" handler: add selected images directly to canvas
  const handleAddSelected = useCallback(() => {
    const selected = uploadedImages.filter((img) => selectedIds.has(img.id))
    if (selected.length === 0) return

    selected.forEach((img) => {
      addImageToCanvas(img.dataUrl)
    })
  }, [uploadedImages, selectedIds, addImageToCanvas])

  // "Remove + Add" handler: remove bg from selected images, then add to canvas
  const handleRemoveAddSelected = useCallback(async () => {
    const selected = uploadedImages.filter((img) => selectedIds.has(img.id))
    if (selected.length === 0) return

    setIsProcessing(true)
    setProcessingCount(0)
    setProcessingTotal(selected.length)

    // Mark all selected images as processing
    setProcessingIds(new Set(selected.map((img) => img.id)))

    for (let i = 0; i < selected.length; i++) {
      try {
        // Convert data URL to blob for upload
        const resp = await fetch(selected[i].dataUrl)
        const blob = await resp.blob()

        const formData = new FormData()
        formData.append('image', blob, selected[i].name)

        const response = await fetch('/api/remove-background', {
          method: 'POST',
          body: formData,
        })

        if (!response.ok) {
          const err = await response.json()
          console.error('Background removal failed:', err.error)
          // Remove this image from processing set even on failure
          setProcessingIds((prev) => {
            const next = new Set(prev)
            next.delete(selected[i].id)
            return next
          })
          continue
        }

        const resultBlob = await response.blob()
        const dataUrl = await new Promise((resolve) => {
          const reader = new FileReader()
          reader.onload = (ev) => resolve(ev.target.result)
          reader.readAsDataURL(resultBlob)
        })

        addImageToCanvas(dataUrl)
        setProcessingCount(i + 1)

        // Remove this image from processing set
        setProcessingIds((prev) => {
          const next = new Set(prev)
          next.delete(selected[i].id)
          return next
        })
      } catch (err) {
        console.error('Error processing image:', selected[i].name, err)
        setProcessingIds((prev) => {
          const next = new Set(prev)
          next.delete(selected[i].id)
          return next
        })
      }
    }

    setIsProcessing(false)
    setProcessingIds(new Set())
  }, [uploadedImages, selectedIds, addImageToCanvas])

  // Download: client-side canvas export at full resolution
  const handleDownload = useCallback(() => {
    const fc = fabricRef.current
    if (!fc) return

    // Canvas is at full logical resolution, no multiplier needed
    const dataUrl = fc.toDataURL({ format: 'png' })

    const link = document.createElement('a')
    link.href = dataUrl
    link.download = 'canvas-export.png'
    link.click()
  }, [])

  // Add to New Listing: export canvas directly, upload to eBay, add to listing
  const handleAddToListing = useCallback(async () => {
    const fc = fabricRef.current
    if (!fc) return

    if (fc.getObjects().length === 0) {
      alert('No images on the canvas to add.')
      return
    }

    setIsCompiling(true)

    try {
      // Export the fabric canvas at full logical resolution (WYSIWYG)
      const dataUrl = fc.toDataURL({ format: 'png', multiplier: 1 })

      // Convert data URL to blob
      const resp = await fetch(dataUrl)
      const blob = await resp.blob()

      // Upload to eBay Picture Services
      const formData = new FormData()
      formData.append('image', blob, 'canvas-compiled.png')

      const uploadResponse = await fetch('/api/upload-image', {
        method: 'POST',
        body: formData,
      })

      if (!uploadResponse.ok) {
        const err = await uploadResponse.json()
        throw new Error(err.error || 'Upload to eBay failed')
      }

      const uploadData = await uploadResponse.json()
      const ebayUrl = uploadData.url

      if (!ebayUrl) {
        throw new Error('No URL returned from eBay upload')
      }

      // Add to the listing via callback
      if (onAddToListing) {
        onAddToListing(ebayUrl)
      }

    } catch (err) {
      console.error('Error adding to listing:', err)
      alert('Failed to add image to listing: ' + err.message)
    } finally {
      setIsCompiling(false)
    }
  }, [onAddToListing])

  // Delete selected object(s)
  const handleDelete = useCallback(() => {
    const fc = fabricRef.current
    if (!fc) return
    const active = fc.getActiveObjects()
    if (active && active.length > 0) {
      active.forEach((obj) => fc.remove(obj))
      fc.discardActiveObject()
      fc.requestRenderAll()
    }
  }, [])

  // Layer order controls
  const handleBringForward = useCallback(() => {
    const fc = fabricRef.current
    if (!fc) return
    const active = fc.getActiveObject()
    if (active) {
      fc.bringObjectForward(active)
      fc.requestRenderAll()
    }
  }, [])

  const handleSendBackward = useCallback(() => {
    const fc = fabricRef.current
    if (!fc) return
    const active = fc.getActiveObject()
    if (active) {
      fc.sendObjectBackwards(active)
      fc.requestRenderAll()
    }
  }, [])

  const handleBringToFront = useCallback(() => {
    const fc = fabricRef.current
    if (!fc) return
    const active = fc.getActiveObject()
    if (active) {
      fc.bringObjectToFront(active)
      fc.requestRenderAll()
    }
  }, [])

  const handleSendToBack = useCallback(() => {
    const fc = fabricRef.current
    if (!fc) return
    const active = fc.getActiveObject()
    if (active) {
      fc.sendObjectToBack(active)
      fc.requestRenderAll()
    }
  }, [])

  // Apply settings
  const applySettings = () => {
    const w = Math.max(1, parseInt(tempWidth, 10) || 1080)
    const h = Math.max(1, parseInt(tempHeight, 10) || 1080)
    setCanvasWidth(w)
    setCanvasHeight(h)
    setBgColor(tempBgColor)
    setShowSettings(false)
  }

  // Open settings
  const openSettings = () => {
    setTempWidth(canvasWidth)
    setTempHeight(canvasHeight)
    setTempBgColor(bgColor)
    setShowSettings(true)
  }

  const selectedCount = selectedIds.size

  return (
    <div className="canvas-compositor">
      <h3 className="canvas-compositor-title">Image Canvas</h3>
      <p className="testing-description">
        Upload images, select which ones to add to the canvas, arrange them with drag / resize / rotate, then download or compile.
      </p>

      {/* Original listing photos */}
      {originalPhotos.length > 0 && (
        <div className="canvas-pool-section canvas-originals-section">
          <div className="canvas-pool-header">
            <h4 className="canvas-pool-title">Original Listing Photos</h4>
            <div className="canvas-pool-actions">
              <button
                type="button"
                className="canvas-pool-link-btn"
                onClick={() => {
                  if (selectedOriginalPhotos.size === originalPhotos.length) {
                    setSelectedOriginalPhotos(new Set())
                  } else {
                    setSelectedOriginalPhotos(new Set(originalPhotos))
                  }
                }}
              >
                {selectedOriginalPhotos.size === originalPhotos.length ? 'Deselect All' : 'Select All'}
              </button>
              <button
                type="button"
                className="testing-button canvas-btn-add-originals"
                onClick={handleAddOriginalsToPool}
                disabled={selectedOriginalPhotos.size === 0 || isAddingOriginals}
              >
                {isAddingOriginals
                  ? 'Adding...'
                  : `Add to Pool${selectedOriginalPhotos.size > 0 ? ` (${selectedOriginalPhotos.size})` : ''}`}
              </button>
            </div>
          </div>
          <div className="canvas-pool-grid">
            {originalPhotos.map((url, index) => (
              <div
                key={`orig-${index}`}
                className={`canvas-pool-thumb ${selectedOriginalPhotos.has(url) ? 'selected' : ''}`}
                onClick={() => toggleOriginalPhotoSelection(url)}
                title={`Original photo ${index + 1}`}
              >
                <img src={url} alt={`Original ${index + 1}`} />
                <div className="canvas-pool-check">
                  {selectedOriginalPhotos.has(url) ? '\u2713' : ''}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Upload & image pool */}
      <div className="canvas-pool-section">
        <div className="canvas-pool-header">
          <h4 className="canvas-pool-title">Image Pool</h4>
          <div className="canvas-pool-actions">
            <input
              ref={uploadInputRef}
              type="file"
              accept="image/*"
              multiple
              style={{ display: 'none' }}
              onChange={handleUploadImages}
            />
            <button
              type="button"
              className="testing-button canvas-btn-upload"
              onClick={() => uploadInputRef.current?.click()}
            >
              Upload Images
            </button>
            {uploadedImages.length > 0 && (
              <>
                <button
                  type="button"
                  className="canvas-pool-link-btn"
                  onClick={selectedIds.size === uploadedImages.length ? deselectAll : selectAll}
                >
                  {selectedIds.size === uploadedImages.length ? 'Deselect All' : 'Select All'}
                </button>
                <button
                  type="button"
                  className="canvas-pool-link-btn canvas-pool-link-btn-danger"
                  onClick={removeFromPool}
                  disabled={selectedCount === 0}
                >
                  Remove from Pool
                </button>
              </>
            )}
          </div>
        </div>

        {uploadedImages.length > 0 ? (
          <div className="canvas-pool-grid">
            {uploadedImages.map((img) => {
              const isImgProcessing = processingIds.has(img.id)
              return (
                <div
                  key={img.id}
                  className={`canvas-pool-thumb ${selectedIds.has(img.id) ? 'selected' : ''} ${isImgProcessing ? 'processing' : ''}`}
                  onClick={() => !isImgProcessing && toggleImageSelection(img.id)}
                  title={img.name}
                >
                  <img src={img.dataUrl} alt={img.name} />
                  <div className="canvas-pool-check">
                    {selectedIds.has(img.id) ? '\u2713' : ''}
                  </div>
                  {isImgProcessing && (
                    <div className="canvas-pool-loading-overlay">
                      <div className="canvas-pool-loading-bar">
                        <div className="canvas-pool-loading-fill" />
                      </div>
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        ) : (
          <div className="canvas-pool-empty">
            No images uploaded yet. Click "Upload Images" to add some.
          </div>
        )}
      </div>

      {/* Toolbar */}
      <div className="canvas-toolbar">
        <div className="canvas-toolbar-left">
          <button
            type="button"
            className="testing-button canvas-btn-remove-add"
            onClick={handleRemoveAddSelected}
            disabled={isProcessing || selectedCount === 0}
            title={selectedCount === 0 ? 'Select images from the pool first' : ''}
          >
            {isProcessing
              ? `Removing... (${processingCount}/${processingTotal})`
              : `Remove + Add${selectedCount > 0 ? ` (${selectedCount})` : ''}`}
          </button>

          <button
            type="button"
            className="testing-button canvas-btn-add"
            onClick={handleAddSelected}
            disabled={isProcessing || selectedCount === 0}
            title={selectedCount === 0 ? 'Select images from the pool first' : ''}
          >
            {`Add${selectedCount > 0 ? ` (${selectedCount})` : ''}`}
          </button>

          <button
            type="button"
            className="canvas-btn-delete"
            onClick={handleDelete}
            title="Delete selected canvas object"
          >
            Delete
          </button>

          <span className="canvas-toolbar-separator" />

          <div className="canvas-layer-controls">
            <button
              type="button"
              className="canvas-layer-btn"
              onClick={handleBringToFront}
              title="Bring to front"
            >
              &#x21C8;
            </button>
            <button
              type="button"
              className="canvas-layer-btn"
              onClick={handleBringForward}
              title="Bring forward"
            >
              &#x2191;
            </button>
            <button
              type="button"
              className="canvas-layer-btn"
              onClick={handleSendBackward}
              title="Send backward"
            >
              &#x2193;
            </button>
            <button
              type="button"
              className="canvas-layer-btn"
              onClick={handleSendToBack}
              title="Send to back"
            >
              &#x21CA;
            </button>
          </div>
        </div>

        <div className="canvas-toolbar-right">
          <button
            type="button"
            className="testing-button canvas-btn-download"
            onClick={handleDownload}
          >
            Download
          </button>

          <button
            type="button"
            className="testing-button canvas-btn-compile"
            onClick={handleAddToListing}
            disabled={isCompiling}
          >
            {isCompiling ? 'Adding...' : 'Add to New Listing'}
          </button>

          {/* Settings gear */}
          <div className="canvas-settings-container" ref={settingsRef}>
            <button
              type="button"
              className="canvas-settings-btn"
              onClick={openSettings}
              title="Canvas settings"
            >
              &#9881;
            </button>

            {showSettings && (
              <div className="canvas-settings-popover">
                <div className="canvas-settings-row">
                  <label>Width:</label>
                  <input
                    type="number"
                    min="1"
                    value={tempWidth}
                    onChange={(e) => setTempWidth(e.target.value)}
                  />
                </div>
                <div className="canvas-settings-row">
                  <label>Height:</label>
                  <input
                    type="number"
                    min="1"
                    value={tempHeight}
                    onChange={(e) => setTempHeight(e.target.value)}
                  />
                </div>
                <div className="canvas-settings-row">
                  <label>BG Color:</label>
                  <input
                    type="color"
                    value={tempBgColor}
                    onChange={(e) => setTempBgColor(e.target.value)}
                  />
                </div>
                <button
                  type="button"
                  className="testing-button canvas-settings-apply"
                  onClick={applySettings}
                >
                  Apply
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Canvas area */}
      <div className="canvas-wrapper" style={{ width: displayWidth, height: displayHeight }}>
        <canvas ref={canvasRef} />
      </div>

      <p className="canvas-dimensions-label">
        {canvasWidth} &times; {canvasHeight}px
        {displayScale < 1 && ` (displayed at ${Math.round(displayScale * 100)}%)`}
      </p>
    </div>
  )
}
