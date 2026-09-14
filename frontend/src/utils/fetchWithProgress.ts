interface ProgressEvent {
  type: "progress";
  [key: string]: unknown;
}

interface ResultEvent {
  type: "result";
  data: unknown;
}

interface ErrorEvent {
  type: "error";
  error: string;
}

type StreamEvent = ProgressEvent | ResultEvent | ErrorEvent;

export async function fetchWithProgress(
  url: string,
  options: RequestInit,
  onProgress: (event: ProgressEvent) => void,
): Promise<unknown> {
  const response = await fetch(url, options);

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let result: unknown = null;
  let errorMsg: string | null = null;

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop()!;

    for (const line of lines) {
      if (!line.trim()) continue;
      try {
        const event = JSON.parse(line) as StreamEvent;
        if (event.type === "progress") {
          onProgress(event as ProgressEvent);
        } else if (event.type === "result") {
          result = (event as ResultEvent).data;
        } else if (event.type === "error") {
          errorMsg = (event as ErrorEvent).error;
        }
      } catch (e) {
        console.warn("Failed to parse progress event:", line, e);
      }
    }
  }

  if (buffer.trim()) {
    try {
      const event = JSON.parse(buffer) as StreamEvent;
      if (event.type === "result") result = (event as ResultEvent).data;
      else if (event.type === "error") errorMsg = (event as ErrorEvent).error;
    } catch {
      // ignore malformed trailing data
    }
  }

  if (errorMsg) {
    throw new Error(errorMsg);
  }

  return result;
}
