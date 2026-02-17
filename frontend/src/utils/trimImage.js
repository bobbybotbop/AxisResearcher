/**
 * Takes an image data URL (PNG with transparency),
 * draws it to an offscreen canvas, scans pixels to find
 * the bounding box of non-transparent content, crops to
 * that box, and returns a new data URL.
 *
 * @param {string} dataUrl - Image data URL (e.g. from canvas.toDataURL or FileReader)
 * @returns {Promise<string>} Trimmed image as data URL, or original if no opaque pixels found
 */
export async function trimTransparentPadding(dataUrl) {
  return new Promise((resolve, reject) => {
    const img = new Image()

    img.onload = () => {
      try {
        const w = img.width
        const h = img.height

        const canvas = document.createElement('canvas')
        canvas.width = w
        canvas.height = h
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          resolve(dataUrl)
          return
        }

        ctx.drawImage(img, 0, 0)
        const imageData = ctx.getImageData(0, 0, w, h)
        const data = imageData.data

        let minX = w
        let minY = h
        let maxX = -1
        let maxY = -1

        for (let y = 0; y < h; y++) {
          for (let x = 0; x < w; x++) {
            const i = (y * w + x) * 4
            const alpha = data[i + 3]
            if (alpha > 0) {
              if (x < minX) minX = x
              if (x > maxX) maxX = x
              if (y < minY) minY = y
              if (y > maxY) maxY = y
            }
          }
        }

        if (maxX < minX || maxY < minY) {
          resolve(dataUrl)
          return
        }

        const cropW = maxX - minX + 1
        const cropH = maxY - minY + 1

        const cropCanvas = document.createElement('canvas')
        cropCanvas.width = cropW
        cropCanvas.height = cropH
        const cropCtx = cropCanvas.getContext('2d')
        if (!cropCtx) {
          resolve(dataUrl)
          return
        }

        cropCtx.drawImage(img, minX, minY, cropW, cropH, 0, 0, cropW, cropH)
        resolve(cropCanvas.toDataURL('image/png'))
      } catch (err) {
        console.error('trimTransparentPadding error:', err)
        resolve(dataUrl)
      }
    }

    img.onerror = () => {
      reject(new Error('Failed to load image for trimming'))
    }

    img.src = dataUrl
  })
}
