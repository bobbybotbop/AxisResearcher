import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import { btnPillSm } from "../styles/buttonPill";

const DEFAULT_TEXT_PROMPT = "Reply with exactly: OK";
const DEFAULT_IMAGE_PROMPT =
  "Generate a simple 64x64 solid blue square on a white background.";

const PROVIDER_LABELS = {
  openrouter: "OpenRouter",
  bedrock: "Bedrock",
};

function groupByProvider(options) {
  return Object.entries(
    options.reduce((acc, option) => {
      const key = option.provider || "openrouter";
      (acc[key] = acc[key] || []).push(option);
      return acc;
    }, {}),
  );
}

export default function TestAiModelSection({
  textModel,
  imageModel,
  textModelOptions,
  imageModelOptions,
}) {
  const [expanded, setExpanded] = useState(false);
  const [kind, setKind] = useState("text");
  const [model, setModel] = useState(textModel);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    setModel(kind === "text" ? textModel : imageModel);
  }, [kind, textModel, imageModel]);

  useEffect(() => {
    if (kind !== "text" || textModelOptions.length === 0) return;
    const isValid = textModelOptions.some((o) => o.value === model);
    if (!isValid) setModel(textModelOptions[0].value);
  }, [kind, textModelOptions, model]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleKindChange = (nextKind) => {
    setKind(nextKind);
    setModel(nextKind === "text" ? textModel : imageModel);
  };

  const handleSend = async (e) => {
    e.preventDefault();
    const prompt = input.trim();
    if (!prompt || isLoading) return;

    const userMessage = { role: "user", content: prompt };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch("/api/test-ai-model", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kind, model, prompt }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: data.error || "Model test failed",
            serverLog: data.server_log || null,
            ok: false,
          },
        ]);
        return;
      }
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.content || "(empty response)",
          imageUrl: data.image_url || null,
          ok: true,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err.message || "Model test failed",
          serverLog: null,
          ok: false,
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClear = () => {
    setMessages([]);
    setInput("");
  };

  const placeholder =
    kind === "text"
      ? DEFAULT_TEXT_PROMPT
      : DEFAULT_IMAGE_PROMPT;

  return (
    <div className="mt-4 border-t border-border-default pt-4">
      <button
        type="button"
        className={btnPillSm}
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
      >
        {expanded ? "Hide Test AI Model" : "Test AI Model"}
      </button>

      {expanded && (
        <div className="mt-4 rounded-lg border border-border-default bg-surface-panel p-4">
          <div className="mb-3 flex flex-wrap items-end gap-3">
            <fieldset className="m-0 flex gap-1 rounded-lg border border-border-default bg-surface-muted p-1">
              <legend className="sr-only">Model type</legend>
              {[
                { value: "text", label: "Text" },
                { value: "image", label: "Image" },
              ].map(({ value, label }) => (
                <button
                  key={value}
                  type="button"
                  className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                    kind === value
                      ? "bg-surface-panel text-text-primary shadow-sm"
                      : "text-text-muted hover:text-text-primary"
                  }`}
                  onClick={() => handleKindChange(value)}
                  aria-pressed={kind === value}
                >
                  {label}
                </button>
              ))}
            </fieldset>
            <label className="flex min-w-[12rem] flex-1 flex-col gap-1 text-sm font-semibold text-text-primary">
              Model
              <select
                className="rounded-lg border border-border-default bg-surface-panel px-3 py-2 text-sm font-medium text-text-primary focus:border-primary focus:outline-none"
                value={model}
                onChange={(e) => setModel(e.target.value)}
                disabled={isLoading}
              >
                {kind === "text"
                  ? groupByProvider(textModelOptions).map(
                      ([provider, options]) => (
                        <optgroup
                          key={provider}
                          label={PROVIDER_LABELS[provider] || provider}
                        >
                          {options.map((option) => (
                            <option key={option.value} value={option.value}>
                              {option.label}
                            </option>
                          ))}
                        </optgroup>
                      ),
                    )
                  : imageModelOptions.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
              </select>
            </label>
            <button
              type="button"
              className="rounded-lg border border-border-default bg-surface-panel px-3 py-2 text-sm font-medium text-text-muted transition-colors hover:bg-surface-hover hover:text-text-primary disabled:opacity-50"
              onClick={handleClear}
              disabled={isLoading || messages.length === 0}
            >
              Clear
            </button>
          </div>

          <div
            className="mb-3 max-h-48 overflow-y-auto rounded-lg border border-border-default bg-surface-muted p-3"
            role="log"
            aria-live="polite"
            aria-label="Test chat messages"
          >
            {messages.length === 0 && !isLoading && (
              <p className="text-sm text-text-muted">
                Send a short prompt to verify the selected{" "}
                {kind === "text" ? "text" : "image"} model responds.
              </p>
            )}
            <ul className="flex flex-col gap-2">
              {messages.map((msg, i) => (
                <li
                  key={i}
                  className={`text-sm ${
                    msg.role === "user"
                      ? "text-text-primary"
                      : msg.ok === false
                        ? "text-red-700"
                        : "text-text-muted"
                  }`}
                >
                  <span className="font-semibold text-text-primary">
                    {msg.role === "user" ? "You" : "Model"}:
                  </span>{" "}
                  {msg.content}
                  {msg.serverLog && (
                    <pre className="mt-2 max-h-40 overflow-auto whitespace-pre-wrap rounded border border-red-200 bg-red-50/80 p-2 font-mono text-xs text-red-900">
                      {msg.serverLog}
                    </pre>
                  )}
                  {msg.imageUrl && (
                    <img
                      src={msg.imageUrl}
                      alt="Generated test"
                      className="mt-2 max-h-32 rounded border border-border-default object-contain"
                    />
                  )}
                </li>
              ))}
              {isLoading && (
                <li className="flex items-center gap-2 text-sm text-text-muted">
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden />
                  Testing model…
                </li>
              )}
            </ul>
            <div ref={chatEndRef} />
          </div>

          <form onSubmit={handleSend} className="flex gap-2">
            <input
              type="text"
              className="min-w-0 flex-1 rounded-full border border-border-default bg-surface-panel px-4 py-2 text-sm text-text-primary transition-colors focus:border-primary focus:outline-none disabled:opacity-60"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={placeholder}
              disabled={isLoading}
              aria-label="Test prompt"
            />
            <button
              type="submit"
              className={`shrink-0 ${btnPillSm}`}
              disabled={isLoading || !input.trim()}
            >
              {isLoading ? "Sending…" : "Send"}
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
