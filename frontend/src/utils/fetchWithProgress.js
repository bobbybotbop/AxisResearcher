export async function fetchWithProgress(url, options, onProgress) {
  const response = await fetch(url, options);

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result = null;
  let errorMsg = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop(); // Keep incomplete line in buffer

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const event = JSON.parse(line);
        if (event.type === "progress") {
          onProgress(event);
        } else if (event.type === "result") {
          result = event.data;
        } else if (event.type === "error") {
          errorMsg = event.error;
        }
      } catch (e) {
        console.warn("Failed to parse progress event:", line, e);
      }
    }
  }

  // Process any remaining data in the buffer
  if (buffer.trim()) {
    try {
      const event = JSON.parse(buffer);
      if (event.type === "result") result = event.data;
      else if (event.type === "error") errorMsg = event.error;
    } catch (e) {
      // ignore malformed trailing data
    }
  }

  if (errorMsg) {
    throw new Error(errorMsg);
  }

  return result;
}
