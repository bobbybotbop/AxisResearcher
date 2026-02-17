import { useState, useRef, useEffect, useCallback } from 'react'
import { Canvas, FabricImage, Textbox } from 'fabric'
import { trimTransparentPadding } from '../utils/trimImage'

const DISPLAY_MAX = 540 // max pixel width for the on-screen canvas
let imageIdCounter = 0

export default function ImageCanvas({ onAddToListing, originalPhotos = [], generatedImages = [], useRealUpload = true }) {
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

  // Loading states
  const [isProcessing, setIsProcessing] = useState(false)
  const [isCompiling, setIsCompiling] = useState(false)
  const [processingCount, setProcessingCount] = useState(0)
  const [processingTotal, setProcessingTotal] = useState(0)

  // Default text settings (for Add Text)
  const [textFontSize, setTextFontSize] = useState(48)
  const [textFontWeight, setTextFontWeight] = useState('normal')

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

  // Pre-populate pool with original listing photos when they change
  useEffect(() => {
    if (!originalPhotos || originalPhotos.length === 0) return

    let cancelled = false
    const loadOriginals = async () => {
      const loaded = []
      for (const url of originalPhotos) {
        if (cancelled) return
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
          loaded.push({ id, dataUrl, name, isOriginal: true })
        } catch (err) {
          console.error('Error loading original photo:', url, err)
        }
      }
      if (!cancelled && loaded.length > 0) {
        setUploadedImages((prev) => {
          const userUploaded = prev.filter((img) => !img.isOriginal)
          return [...loaded, ...userUploaded]
        })
      }
    }
    loadOriginals()
    return () => { cancelled = true }
  }, [originalPhotos])

  // Add generated images to pool when they become available (after Confirm Categories)
  useEffect(() => {
    if (!generatedImages || generatedImages.length === 0) return

    let cancelled = false
    const loadGenerated = async () => {
      const loaded = []
      for (const url of generatedImages) {
        if (cancelled) return
        try {
          const response = await fetch(url)
          const blob = await response.blob()
          const dataUrl = await new Promise((resolve) => {
            const reader = new FileReader()
            reader.onload = (ev) => resolve(ev.target.result)
            reader.readAsDataURL(blob)
          })
          const id = ++imageIdCounter
          const name = url.split('/').pop() || `generated-${id}.jpg`
          loaded.push({ id, dataUrl, name, isGenerated: true })
        } catch (err) {
          console.error('Error loading generated photo:', url, err)
        }
      }
      if (!cancelled && loaded.length > 0) {
        setUploadedImages((prev) => {
          const originals = prev.filter((img) => img.isOriginal)
          const userUploaded = prev.filter((img) => !img.isOriginal && !img.isGenerated)
          return [...originals, ...loaded, ...userUploaded]
        })
      }
    }
    loadGenerated()
    return () => { cancelled = true }
  }, [generatedImages])

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

      const fabricImg = new FabricImage(imgEl, {
        scaleX: scale,
        scaleY: scale,
        originX: 'center',
        originY: 'center',
        left: canvasWidth / 2,
        top: canvasHeight / 2,
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
    setSelectedIds(new Set())
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

        const trimmedUrl = await trimTransparentPadding(dataUrl)
        addImageToCanvas(trimmedUrl)
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
    setSelectedIds(new Set())
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

  // Add to New Listing: export canvas, optionally upload to eBay, add to listing
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

      if (!useRealUpload) {
        // Mock mode: add data URL directly without uploading to eBay
        if (onAddToListing) onAddToListing(dataUrl)
        setIsCompiling(false)
        return
      }

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
  }, [onAddToListing, useRealUpload])

  // Add text to canvas
  const handleAddText = useCallback(() => {
    const fc = fabricRef.current
    if (!fc) return

    const fontSize = Math.max(8, Math.min(500, parseInt(textFontSize, 10) || 48))
    const fontWeight = textFontWeight === 'bold' ? 'bold' : textFontWeight === 'bolder' ? 'bolder' : 'normal'

    const textbox = new Textbox('Double-click to edit', {
      left: canvasWidth * 0.1,
      top: canvasHeight * 0.1,
      width: Math.min(canvasWidth * 0.8, 400),
      fontSize,
      fontWeight,
      fontFamily: 'Arial',
      fill: '#000000',
      originX: 'left',
      originY: 'top',
    })
    fc.add(textbox)
    fc.setActiveObject(textbox)
    fc.requestRenderAll()
  }, [canvasWidth, canvasHeight, textFontSize, textFontWeight])

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
          <div className="canvas-text-settings">
            <label className="canvas-text-label" title="Font size for new text">
              Size:
            </label>
            <input
              type="number"
              min="8"
              max="500"
              value={textFontSize}
              onChange={(e) => setTextFontSize(Math.max(8, Math.min(500, parseInt(e.target.value, 10) || 48)))}
              className="canvas-text-input"
            />
            <label className="canvas-text-label" title="Font weight for new text">
              Weight:
            </label>
            <select
              value={textFontWeight}
              onChange={(e) => setTextFontWeight(e.target.value)}
              className="canvas-text-select"
            >
              <option value="normal">Normal</option>
              <option value="bold">Bold</option>
              <option value="bolder">Bolder</option>
              <option value="lighter">Lighter</option>
            </select>
          </div>

          <button
            type="button"
            className="testing-button canvas-btn-add-text"
            onClick={handleAddText}
            title="Add text to canvas"
          >
            Add Text
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

      <div className="canvas-export-actions">
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
      </div>
    </div>
  )
}
