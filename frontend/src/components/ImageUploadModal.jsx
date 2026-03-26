import { useState, useCallback, useEffect, useRef } from "react";
import { btnPillSm } from "../styles/buttonPill";

export default function ImageUploadModal({
  isOpen,
  onClose,
  onAddImages,
  canAddToOriginal = true,
  mode,
}) {
  const [pendingImages, setPendingImages] = useState([]);
  const [destination, setDestination] = useState("pool");
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef(null);

  const reset = useCallback(() => {
    setPendingImages([]);
    setDestination("pool");
  }, []);

  useEffect(() => {
    if (!isOpen) reset();
  }, [isOpen, reset]);

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === "Escape") onClose();
    };
    if (isOpen) {
      document.addEventListener("keydown", handleEscape);
      document.body.style.overflow = "hidden";
    }
    return () => {
      document.removeEventListener("keydown", handleEscape);
      document.body.style.overflow = "";
    };
  }, [isOpen, onClose]);

  const addFilesToPending = useCallback((files) => {
    const imageFiles = Array.from(files || []).filter((f) =>
      f.type?.startsWith("image/"),
    );
    if (imageFiles.length === 0) return;
    const promises = imageFiles.map(
      (file) =>
        new Promise((resolve) => {
          const reader = new FileReader();
          reader.onload = (ev) =>
            resolve({
              dataUrl: ev.target.result,
              name: file.name || `image-${Date.now()}.png`,
            });
          reader.readAsDataURL(file);
        }),
    );
    Promise.all(promises).then((results) => {
      setPendingImages((prev) => [...prev, ...results]);
    });
  }, []);

  useEffect(() => {
    if (!isOpen) return;
    const handlePasteGlobal = (e) => {
      const items = e.clipboardData?.items;
      if (!items) return;
      const files = [];
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) files.push(file);
        }
      }
      if (files.length > 0) {
        e.preventDefault();
        addFilesToPending(files);
      }
    };
    document.addEventListener("paste", handlePasteGlobal, true);
    return () => document.removeEventListener("paste", handlePasteGlobal, true);
  }, [isOpen, addFilesToPending]);

  const handleFileChange = useCallback(
    (e) => {
      const files = e.target.files;
      if (files?.length) addFilesToPending(files);
      e.target.value = "";
    },
    [addFilesToPending],
  );

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      setIsDragging(false);
      const files = e.dataTransfer?.files;
      if (files?.length) addFilesToPending(files);
    },
    [addFilesToPending],
  );

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleConfirm = useCallback(() => {
    if (pendingImages.length === 0) return;
    const urls = pendingImages.map((img) => img.dataUrl);
    const dest = mode === "original" ? "original" : destination;
    if (dest === "original") {
      onAddImages?.(urls, "original");
    } else {
      onAddImages?.(pendingImages, "pool");
    }
    onClose();
  }, [pendingImages, destination, mode, onAddImages, onClose]);

  const removePending = useCallback((index) => {
    setPendingImages((prev) => prev.filter((_, i) => i !== index));
  }, []);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-modal-title"
    >
      <div
        className="flex max-h-[90vh] w-full max-w-lg flex-col rounded-xl border border-gray-200 bg-white shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-gray-200 p-4">
          <h2
            id="upload-modal-title"
            className="text-lg font-semibold text-gray-800"
          >
            Add Images
          </h2>
        </div>

        <div className="flex-1 overflow-auto p-4">
          <div
            className={`mb-4 rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
              isDragging
                ? "border-primary bg-primary/5"
                : "border-gray-300 bg-gray-50"
            }`}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            tabIndex={0}
          >
            <p className="mb-2 text-sm text-gray-600">
              Paste an image (Ctrl+V) or drag and drop files here
            </p>
            <button
              type="button"
              className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
              onClick={() => fileInputRef.current?.click()}
            >
              Choose files
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              multiple
              className="hidden"
              onChange={handleFileChange}
            />
          </div>

          {canAddToOriginal && mode !== "original" && (
            <div className="mb-4">
              <label className="mb-2 block text-sm font-medium text-gray-700">
                Add to
              </label>
              <div className="flex flex-col gap-2">
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="destination"
                    value="pool"
                    checked={destination === "pool"}
                    onChange={() => setDestination("pool")}
                    className="rounded"
                  />
                  <span className="text-sm">
                    Image Pool (for canvas editing)
                  </span>
                </label>
                <label className="flex cursor-pointer items-center gap-2">
                  <input
                    type="radio"
                    name="destination"
                    value="original"
                    checked={destination === "original"}
                    onChange={() => setDestination("original")}
                    className="rounded"
                  />
                  <span className="text-sm">
                    Original Photos (for AI processing)
                  </span>
                </label>
              </div>
            </div>
          )}

          {pendingImages.length > 0 && (
            <div>
              <p className="mb-2 text-sm font-medium text-gray-700">
                Preview ({pendingImages.length} image
                {pendingImages.length !== 1 ? "s" : ""})
              </p>
              <div className="flex flex-wrap gap-2">
                {pendingImages.map((img, i) => (
                  <div
                    key={i}
                    className="group relative aspect-square w-20 overflow-hidden rounded-lg border border-gray-200"
                  >
                    <img
                      src={img.dataUrl}
                      alt={img.name}
                      className="h-full w-full object-cover"
                    />
                    <button
                      type="button"
                      className="absolute right-1 top-1 flex h-6 w-6 items-center justify-center rounded-full bg-red-500 text-sm font-bold text-white shadow-md transition-colors hover:bg-red-600"
                      onClick={(e) => {
                        e.stopPropagation();
                        removePending(i);
                      }}
                      title="Remove image"
                    >
                      &times;
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="flex justify-end gap-2 border-t border-gray-200 p-4">
          <button
            type="button"
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 transition-colors hover:bg-gray-50"
            onClick={onClose}
          >
            Cancel
          </button>
          <button
            type="button"
            className={btnPillSm}
            onClick={handleConfirm}
            disabled={pendingImages.length === 0}
          >
            Add {pendingImages.length > 0 ? `(${pendingImages.length})` : ""}
          </button>
        </div>
      </div>
    </div>
  );
}
