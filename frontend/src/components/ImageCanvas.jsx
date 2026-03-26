import { useState, useRef, useEffect, useCallback } from "react";
import { Canvas, FabricImage, Textbox } from "fabric";
import {
  TypeText,
  Trash,
  TrashTwo,
  Cog,
  ArrowsUpFromLine,
  ArrowUp,
  ArrowDown,
  ArrowDownSquare,
  CloudUpload,
  CheckSquare,
  Scissors,
  PlusSquare,
} from "@mynaui/icons-react";
import { trimTransparentPadding } from "../utils/trimImage";
import ImageUploadModal from "./ImageUploadModal";
import { btnPill, btnPillSecondary, btnPillSm } from "../styles/buttonPill";

const DISPLAY_MAX = 324; // 30% of 1080 for on-screen canvas display
let imageIdCounter = 0;

export default function ImageCanvas({
  onAddToListing,
  onAddToOriginalPhotos,
  originalPhotos = [],
  generatedImages = [],
  useRealUpload = true,
}) {
  // Canvas settings
  const [canvasWidth, setCanvasWidth] = useState(1080);
  const [canvasHeight, setCanvasHeight] = useState(1080);
  const [bgColor, setBgColor] = useState("#FFFFFF");
  const [showSettings, setShowSettings] = useState(false);
  const [showTextOptions, setShowTextOptions] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);

  // Temp settings (only applied on confirm)
  const [tempWidth, setTempWidth] = useState(1080);
  const [tempHeight, setTempHeight] = useState(1080);
  const [tempBgColor, setTempBgColor] = useState("#FFFFFF");

  // Uploaded image pool
  const [uploadedImages, setUploadedImages] = useState([]); // { id, dataUrl, name }
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [processingIds, setProcessingIds] = useState(new Set()); // IDs currently having bg removed

  // Loading states
  const [isProcessing, setIsProcessing] = useState(false);
  const [isCompiling, setIsCompiling] = useState(false);
  const [processingCount, setProcessingCount] = useState(0);
  const [processingTotal, setProcessingTotal] = useState(0);

  // Default text settings (for Add Text)
  const [textFontSize, setTextFontSize] = useState(48);
  const [textFontWeight, setTextFontWeight] = useState("normal");

  // Refs
  const canvasRef = useRef(null);
  const fabricRef = useRef(null);
  const settingsRef = useRef(null);
  const textOptionsRef = useRef(null);

  // Compute display scale
  const displayScale = Math.min(
    DISPLAY_MAX / canvasWidth,
    DISPLAY_MAX / canvasHeight,
    1,
  );
  const displayWidth = Math.round(canvasWidth * displayScale);
  const displayHeight = Math.round(canvasHeight * displayScale);

  // Initialize fabric canvas at full logical resolution
  useEffect(() => {
    if (!canvasRef.current) return;

    const fc = new Canvas(canvasRef.current, {
      width: canvasWidth,
      height: canvasHeight,
      backgroundColor: bgColor,
      selection: true,
    });

    // Apply CSS transform to scale down for display (keeps logical coords at full res)
    const wrapper = fc.wrapperEl;
    if (wrapper) {
      wrapper.style.transformOrigin = "top left";
      wrapper.style.transform = `scale(${displayScale})`;
    }

    fabricRef.current = fc;

    return () => {
      fc.dispose();
      fabricRef.current = null;
    };
    // Only re-init when dimensions or bg changes
  }, [canvasWidth, canvasHeight, bgColor, displayScale]);

  // Delete key handler
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Delete" && fabricRef.current) {
        const active = fabricRef.current.getActiveObjects();
        if (active && active.length > 0) {
          active.forEach((obj) => fabricRef.current.remove(obj));
          fabricRef.current.discardActiveObject();
          fabricRef.current.requestRenderAll();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Close settings and text options popovers on outside click
  useEffect(() => {
    const handleClick = (e) => {
      if (
        showSettings &&
        settingsRef.current &&
        !settingsRef.current.contains(e.target)
      ) {
        setShowSettings(false);
      }
      if (
        showTextOptions &&
        textOptionsRef.current &&
        !textOptionsRef.current.contains(e.target)
      ) {
        setShowTextOptions(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [showSettings, showTextOptions]);

  // Pre-populate pool with original listing photos when they change
  useEffect(() => {
    if (!originalPhotos || originalPhotos.length === 0) return;

    let cancelled = false;
    const loadOriginals = async () => {
      const loaded = [];
      for (const url of originalPhotos) {
        if (cancelled) return;
        try {
          const response = await fetch(url);
          const blob = await response.blob();
          const dataUrl = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (ev) => resolve(ev.target.result);
            reader.readAsDataURL(blob);
          });
          const id = ++imageIdCounter;
          const name = url.split("/").pop() || `original-${id}.jpg`;
          loaded.push({ id, dataUrl, name, isOriginal: true });
        } catch (err) {
          console.error("Error loading original photo:", url, err);
        }
      }
      if (!cancelled && loaded.length > 0) {
        setUploadedImages((prev) => {
          const userUploaded = prev.filter((img) => !img.isOriginal);
          return [...loaded, ...userUploaded];
        });
      }
    };
    loadOriginals();
    return () => {
      cancelled = true;
    };
  }, [originalPhotos]);

  // Add generated images to pool when they become available (after Confirm Categories)
  useEffect(() => {
    if (!generatedImages || generatedImages.length === 0) return;

    let cancelled = false;
    const loadGenerated = async () => {
      const loaded = [];
      for (const url of generatedImages) {
        if (cancelled) return;
        try {
          const response = await fetch(url);
          const blob = await response.blob();
          const dataUrl = await new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = (ev) => resolve(ev.target.result);
            reader.readAsDataURL(blob);
          });
          const id = ++imageIdCounter;
          const name = url.split("/").pop() || `generated-${id}.jpg`;
          loaded.push({ id, dataUrl, name, isGenerated: true });
        } catch (err) {
          console.error("Error loading generated photo:", url, err);
        }
      }
      if (!cancelled && loaded.length > 0) {
        setUploadedImages((prev) => {
          const originals = prev.filter((img) => img.isOriginal);
          const userUploaded = prev.filter(
            (img) => !img.isOriginal && !img.isGenerated,
          );
          return [...originals, ...loaded, ...userUploaded];
        });
      }
    };
    loadGenerated();
    return () => {
      cancelled = true;
    };
  }, [generatedImages]);

  // Helper: add an image (as data URL) to the fabric canvas
  const addImageToCanvas = useCallback(
    (dataUrl) => {
      const fc = fabricRef.current;
      if (!fc) return;

      const imgEl = new Image();
      imgEl.onload = () => {
        // Scale to fit 90% of the canvas, preserving aspect ratio
        const scaleX = (canvasWidth * 0.9) / imgEl.width;
        const scaleY = (canvasHeight * 0.9) / imgEl.height;
        const scale = Math.min(scaleX, scaleY);

        const fabricImg = new FabricImage(imgEl, {
          scaleX: scale,
          scaleY: scale,
          originX: "center",
          originY: "center",
          left: canvasWidth / 2,
          top: canvasHeight / 2,
        });

        fc.add(fabricImg);
        fc.setActiveObject(fabricImg);
        fc.requestRenderAll();
      };
      imgEl.src = dataUrl;
    },
    [canvasWidth, canvasHeight],
  );

  // Handle images added from upload modal
  const handleModalAddImages = useCallback(
    (images, destination) => {
      if (destination === "original") {
        const urls = Array.isArray(images) ? images : [images];
        onAddToOriginalPhotos?.(urls);
      } else {
        const items = Array.isArray(images) ? images : [images];
        const newImages = items.map((img) => {
          const id = ++imageIdCounter;
          return {
            id,
            dataUrl: typeof img === "string" ? img : img.dataUrl,
            name: typeof img === "string" ? `image-${id}.png` : img.name,
          };
        });
        setUploadedImages((prev) => [...prev, ...newImages]);
      }
    },
    [onAddToOriginalPhotos],
  );

  // Toggle image selection in the pool
  const toggleImageSelection = useCallback((id) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  // Select / deselect all
  const selectAll = useCallback(() => {
    setSelectedIds(new Set(uploadedImages.map((img) => img.id)));
  }, [uploadedImages]);

  const deselectAll = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  // Remove selected images from the pool
  const removeFromPool = useCallback(() => {
    setUploadedImages((prev) => prev.filter((img) => !selectedIds.has(img.id)));
    setSelectedIds(new Set());
  }, [selectedIds]);

  // "Add" handler: add selected images directly to canvas
  const handleAddSelected = useCallback(() => {
    const selected = uploadedImages.filter((img) => selectedIds.has(img.id));
    if (selected.length === 0) return;

    selected.forEach((img) => {
      addImageToCanvas(img.dataUrl);
    });
    setSelectedIds(new Set());
  }, [uploadedImages, selectedIds, addImageToCanvas]);

  // "Remove + Add" handler: remove bg from selected images, then add to canvas
  const handleRemoveAddSelected = useCallback(async () => {
    const selected = uploadedImages.filter((img) => selectedIds.has(img.id));
    if (selected.length === 0) return;

    setIsProcessing(true);
    setProcessingCount(0);
    setProcessingTotal(selected.length);

    // Mark all selected images as processing
    setProcessingIds(new Set(selected.map((img) => img.id)));

    for (let i = 0; i < selected.length; i++) {
      try {
        // Convert data URL to blob for upload
        const resp = await fetch(selected[i].dataUrl);
        const blob = await resp.blob();

        const formData = new FormData();
        formData.append("image", blob, selected[i].name);

        const response = await fetch("/api/remove-background", {
          method: "POST",
          body: formData,
        });

        if (!response.ok) {
          const err = await response.json();
          console.error("Background removal failed:", err.error);
          // Remove this image from processing set even on failure
          setProcessingIds((prev) => {
            const next = new Set(prev);
            next.delete(selected[i].id);
            return next;
          });
          continue;
        }

        const resultBlob = await response.blob();
        const dataUrl = await new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = (ev) => resolve(ev.target.result);
          reader.readAsDataURL(resultBlob);
        });

        const trimmedUrl = await trimTransparentPadding(dataUrl);
        addImageToCanvas(trimmedUrl);
        setProcessingCount(i + 1);

        // Remove this image from processing set
        setProcessingIds((prev) => {
          const next = new Set(prev);
          next.delete(selected[i].id);
          return next;
        });
      } catch (err) {
        console.error("Error processing image:", selected[i].name, err);
        setProcessingIds((prev) => {
          const next = new Set(prev);
          next.delete(selected[i].id);
          return next;
        });
      }
    }

    setIsProcessing(false);
    setProcessingIds(new Set());
    setSelectedIds(new Set());
  }, [uploadedImages, selectedIds, addImageToCanvas]);

  // Download: client-side canvas export at full resolution
  const handleDownload = useCallback(() => {
    const fc = fabricRef.current;
    if (!fc) return;

    // Canvas is at full logical resolution, no multiplier needed
    const dataUrl = fc.toDataURL({ format: "png" });

    const link = document.createElement("a");
    link.href = dataUrl;
    link.download = "canvas-export.png";
    link.click();
  }, []);

  // Add to New Listing: export canvas, optionally upload to eBay, add to listing
  const handleAddToListing = useCallback(async () => {
    const fc = fabricRef.current;
    if (!fc) return;

    if (fc.getObjects().length === 0) {
      alert("No images on the canvas to add.");
      return;
    }

    setIsCompiling(true);

    try {
      // Export the fabric canvas at full logical resolution (WYSIWYG)
      const dataUrl = fc.toDataURL({ format: "png", multiplier: 1 });

      if (!useRealUpload) {
        // Mock mode: add data URL directly without uploading to eBay
        if (onAddToListing) onAddToListing(dataUrl);
        setIsCompiling(false);
        return;
      }

      // Convert data URL to blob
      const resp = await fetch(dataUrl);
      const blob = await resp.blob();

      // Upload to eBay Picture Services
      const formData = new FormData();
      formData.append("image", blob, "canvas-compiled.png");

      const uploadResponse = await fetch("/api/upload-image", {
        method: "POST",
        body: formData,
      });

      if (!uploadResponse.ok) {
        const err = await uploadResponse.json();
        throw new Error(err.error || "Upload to eBay failed");
      }

      const uploadData = await uploadResponse.json();
      const ebayUrl = uploadData.url;

      if (!ebayUrl) {
        throw new Error("No URL returned from eBay upload");
      }

      // Add to the listing via callback
      if (onAddToListing) {
        onAddToListing(ebayUrl);
      }
    } catch (err) {
      console.error("Error adding to listing:", err);
      alert("Failed to add image to listing: " + err.message);
    } finally {
      setIsCompiling(false);
    }
  }, [onAddToListing, useRealUpload]);

  // Add text to canvas
  const handleAddText = useCallback(() => {
    const fc = fabricRef.current;
    if (!fc) return;

    const fontSize = Math.max(
      8,
      Math.min(500, parseInt(textFontSize, 10) || 48),
    );
    const fontWeight =
      textFontWeight === "bold"
        ? "bold"
        : textFontWeight === "bolder"
          ? "bolder"
          : "normal";

    const textbox = new Textbox("Double-click to edit", {
      left: canvasWidth * 0.1,
      top: canvasHeight * 0.1,
      width: Math.min(canvasWidth * 0.8, 400),
      fontSize,
      fontWeight,
      fontFamily: "Arial",
      fill: "#000000",
      originX: "left",
      originY: "top",
    });
    fc.add(textbox);
    fc.setActiveObject(textbox);
    fc.requestRenderAll();
  }, [canvasWidth, canvasHeight, textFontSize, textFontWeight]);

  // Delete selected object(s)
  const handleDelete = useCallback(() => {
    const fc = fabricRef.current;
    if (!fc) return;
    const active = fc.getActiveObjects();
    if (active && active.length > 0) {
      active.forEach((obj) => fc.remove(obj));
      fc.discardActiveObject();
      fc.requestRenderAll();
    }
  }, []);

  // Layer order controls
  const handleBringForward = useCallback(() => {
    const fc = fabricRef.current;
    if (!fc) return;
    const active = fc.getActiveObject();
    if (active) {
      fc.bringObjectForward(active);
      fc.requestRenderAll();
    }
  }, []);

  const handleSendBackward = useCallback(() => {
    const fc = fabricRef.current;
    if (!fc) return;
    const active = fc.getActiveObject();
    if (active) {
      fc.sendObjectBackwards(active);
      fc.requestRenderAll();
    }
  }, []);

  const handleBringToFront = useCallback(() => {
    const fc = fabricRef.current;
    if (!fc) return;
    const active = fc.getActiveObject();
    if (active) {
      fc.bringObjectToFront(active);
      fc.requestRenderAll();
    }
  }, []);

  const handleSendToBack = useCallback(() => {
    const fc = fabricRef.current;
    if (!fc) return;
    const active = fc.getActiveObject();
    if (active) {
      fc.sendObjectToBack(active);
      fc.requestRenderAll();
    }
  }, []);

  // Apply settings
  const applySettings = () => {
    const w = Math.max(1, parseInt(tempWidth, 10) || 1080);
    const h = Math.max(1, parseInt(tempHeight, 10) || 1080);
    setCanvasWidth(w);
    setCanvasHeight(h);
    setBgColor(tempBgColor);
    setShowSettings(false);
  };

  // Open settings
  const openSettings = () => {
    setTempWidth(canvasWidth);
    setTempHeight(canvasHeight);
    setTempBgColor(bgColor);
    setShowSettings(true);
  };

  const selectedCount = selectedIds.size;

  const iconBtn =
    "flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-gray-300 bg-gray-100 text-gray-700 transition-colors hover:bg-gray-200";
  const iconBtnPool =
    "flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-gray-300 bg-gray-100 text-gray-700 transition-colors hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-60";

  return (
    <div>
      <div className="flex gap-4">
        {/* Vertical toolbar - left */}
        <div className="flex flex-col gap-1 rounded-xl border border-gray-200 bg-white p-2">
          <div className="relative" ref={textOptionsRef}>
            <button
              type="button"
              className={iconBtn}
              onClick={() => {
                setShowTextOptions((prev) => !prev);
                setShowSettings(false);
              }}
              title="Add text to canvas"
            >
              <TypeText size={20} />
            </button>
            {showTextOptions && (
              <div className="absolute left-full top-0 z-10 ml-2 flex w-40 flex-col gap-2 rounded-lg border border-gray-200 bg-white p-3 shadow-lg">
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm">Size:</label>
                  <input
                    type="number"
                    min="8"
                    max="500"
                    value={textFontSize}
                    onChange={(e) =>
                      setTextFontSize(
                        Math.max(
                          8,
                          Math.min(500, parseInt(e.target.value, 10) || 48),
                        ),
                      )
                    }
                    className="w-16 rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm">Weight:</label>
                  <select
                    value={textFontWeight}
                    onChange={(e) => setTextFontWeight(e.target.value)}
                    className="appearance-none rounded border border-gray-300 bg-white px-2 py-1 pr-7 text-sm accent-black"
                    style={{
                      backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%23000' d='M6 9L1 4h10z'/%3E%3C/svg%3E")`,
                      backgroundRepeat: "no-repeat",
                      backgroundPosition: "right 0.35rem center",
                    }}
                  >
                    <option value="normal">Normal</option>
                    <option value="bold">Bold</option>
                    <option value="bolder">Bolder</option>
                    <option value="lighter">Lighter</option>
                  </select>
                </div>
                <button
                  type="button"
                  className={`w-full ${btnPillSm}`}
                  onClick={() => {
                    handleAddText();
                    setShowTextOptions(false);
                  }}
                >
                  Add Text
                </button>
              </div>
            )}
          </div>

          <button
            type="button"
            className={iconBtn}
            onClick={handleDelete}
            title="Delete selected canvas object"
          >
            <Trash size={20} />
          </button>

          <span className="my-1 h-px bg-gray-200" />

          <button
            type="button"
            className={iconBtn}
            onClick={handleBringToFront}
            title="Bring to front"
          >
            <ArrowsUpFromLine size={20} />
          </button>
          <button
            type="button"
            className={iconBtn}
            onClick={handleBringForward}
            title="Bring forward"
          >
            <ArrowUp size={20} />
          </button>
          <button
            type="button"
            className={iconBtn}
            onClick={handleSendBackward}
            title="Send backward"
          >
            <ArrowDown size={20} />
          </button>
          <button
            type="button"
            className={iconBtn}
            onClick={handleSendToBack}
            title="Send to back"
          >
            <ArrowDownSquare size={20} />
          </button>

          <span className="my-1 h-px bg-gray-200" />

          <div className="relative" ref={settingsRef}>
            <button
              type="button"
              className={iconBtn}
              onClick={() => {
                openSettings();
                setShowTextOptions(false);
              }}
              title="Canvas settings"
            >
              <Cog size={20} />
            </button>
            {showSettings && (
              <div className="absolute left-full top-0 z-10 ml-2 flex w-48 flex-col gap-2 rounded-lg border border-gray-200 bg-white p-3 shadow-lg">
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm">Width:</label>
                  <input
                    type="number"
                    min="1"
                    value={tempWidth}
                    onChange={(e) => setTempWidth(e.target.value)}
                    className="w-20 rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm">Height:</label>
                  <input
                    type="number"
                    min="1"
                    value={tempHeight}
                    onChange={(e) => setTempHeight(e.target.value)}
                    className="w-20 rounded border border-gray-300 px-2 py-1 text-sm"
                  />
                </div>
                <div className="flex items-center justify-between gap-2">
                  <label className="text-sm">BG Color:</label>
                  <input
                    type="color"
                    value={tempBgColor}
                    onChange={(e) => setTempBgColor(e.target.value)}
                    className="h-8 w-14 cursor-pointer rounded border border-gray-300"
                  />
                </div>
                <button
                  type="button"
                  className={`w-full ${btnPillSm}`}
                  onClick={applySettings}
                >
                  Apply
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Canvas + Image pool */}
        <div className="flex min-w-0 flex-1 flex-col gap-4 lg:flex-row lg:gap-6">
          <div className="flex shrink-0 w-fit flex-col">
            {/* Canvas area */}
            <div
              className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm"
              style={{ width: displayWidth, height: displayHeight }}
            >
              <canvas ref={canvasRef} />
            </div>

            <p className="mt-2 text-sm text-gray-600">
              {canvasWidth} &times; {canvasHeight}px
              {displayScale < 1 &&
                ` (displayed at ${Math.round(displayScale * 100)}%)`}
            </p>

            <div className="mt-4 flex flex-wrap gap-3">
              <button
                type="button"
                className={btnPillSecondary}
                onClick={handleDownload}
              >
                Download
              </button>
              <button
                type="button"
                className={btnPill}
                onClick={handleAddToListing}
                disabled={isCompiling}
              >
                {isCompiling ? "Adding..." : "Add to New Listing"}
              </button>
            </div>
          </div>

          {/* Image pool */}
          <div className="flex flex-1 min-w-0 flex-col rounded-xl border border-gray-200 bg-white">
            <div className="flex flex-1 min-h-0">
              {/* Vertical toolbar - left */}
              <div className="flex shrink-0 flex-col gap-1 rounded-l-xl border-r border-gray-200 bg-white p-2">
                <button
                  type="button"
                  className={iconBtnPool}
                  onClick={() => setShowUploadModal(true)}
                  title="Upload Images"
                >
                  <CloudUpload size={22} />
                </button>
                {uploadedImages.length > 0 && (
                  <>
                    <button
                      type="button"
                      className={iconBtnPool}
                      onClick={
                        selectedIds.size === uploadedImages.length
                          ? deselectAll
                          : selectAll
                      }
                      title={
                        selectedIds.size === uploadedImages.length
                          ? "Deselect All"
                          : "Select All"
                      }
                    >
                      <CheckSquare size={22} />
                    </button>
                    <button
                      type="button"
                      className={iconBtnPool}
                      onClick={removeFromPool}
                      disabled={selectedCount === 0}
                      title="Remove from Pool"
                    >
                      <TrashTwo size={22} />
                    </button>
                    <button
                      type="button"
                      className={iconBtnPool}
                      onClick={handleRemoveAddSelected}
                      disabled={isProcessing || selectedCount === 0}
                      title={
                        isProcessing
                          ? `Removing... (${processingCount}/${processingTotal})`
                          : selectedCount === 0
                            ? "Select images from the pool first"
                            : `Remove + Add${selectedCount > 0 ? ` (${selectedCount})` : ""}`
                      }
                    >
                      <Scissors size={22} />
                    </button>
                    <button
                      type="button"
                      className={iconBtnPool}
                      onClick={handleAddSelected}
                      disabled={isProcessing || selectedCount === 0}
                      title={
                        selectedCount === 0
                          ? "Select images from the pool first"
                          : `Add${selectedCount > 0 ? ` (${selectedCount})` : ""}`
                      }
                    >
                      <PlusSquare size={22} />
                    </button>
                  </>
                )}
              </div>

              {/* Content - right (image pool) */}
              <div className="flex flex-1 min-w-0 flex-col">
                <div className="flex-1 overflow-auto p-4">
                  {uploadedImages.length > 0 ? (
                    <div
                      className={`grid ${
                        uploadedImages.length > 12
                          ? "grid-cols-4 gap-2 sm:grid-cols-5"
                          : uploadedImages.length > 6
                            ? "grid-cols-3 gap-2 sm:grid-cols-4"
                            : "grid-cols-2 gap-3 sm:grid-cols-3"
                      }`}
                    >
                      {uploadedImages.map((img) => {
                        const isImgProcessing = processingIds.has(img.id);
                        const isSelected = selectedIds.has(img.id);
                        return (
                          <div
                            key={img.id}
                            className={`relative aspect-square cursor-pointer overflow-hidden rounded-lg border-2 transition-all ${
                              isSelected
                                ? "border-primary ring-2 ring-primary/30"
                                : "border-transparent"
                            } ${isImgProcessing ? "pointer-events-none opacity-70" : ""}`}
                            onClick={() =>
                              !isImgProcessing && toggleImageSelection(img.id)
                            }
                            title={img.name}
                          >
                            <img
                              src={img.dataUrl}
                              alt={img.name}
                              className="h-full w-full object-cover"
                            />
                            <div
                              className={`absolute inset-0 flex items-center justify-center bg-primary/20 text-2xl font-bold text-primary ${
                                isSelected ? "opacity-100" : "opacity-0"
                              }`}
                            >
                              {isSelected ? "\u2713" : ""}
                            </div>
                            {isImgProcessing && (
                              <div className="absolute inset-0 flex items-center justify-center bg-black/40">
                                <div className="h-1 w-3/4 overflow-hidden rounded-full bg-gray-700">
                                  <div className="h-full w-2/5 animate-pool-loading rounded-full bg-violet-500" />
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  ) : (
                    <div className="py-8 text-center text-sm text-gray-500">
                      No images uploaded yet. Use the upload icon to add some.
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <ImageUploadModal
        isOpen={showUploadModal}
        onClose={() => setShowUploadModal(false)}
        onAddImages={handleModalAddImages}
        canAddToOriginal={!!onAddToOriginalPhotos}
      />
    </div>
  );
}
