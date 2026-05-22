import { useEffect, useState } from "react";
import { Eye, EyeOff } from "lucide-react";
import { btnPillSm } from "../styles/buttonPill";

const API_KEY_FIELDS = [
  {
    name: "openrouter_api_key",
    label: "OpenRouter API Key",
    placeholder: "sk-or-v1-...",
  },
  {
    name: "bedrock_api_key",
    label: "Bedrock API Key",
    placeholder: "AWS Bedrock key",
  },
];

const emptyInputs = () =>
  API_KEY_FIELDS.reduce((acc, { name }) => {
    acc[name] = "";
    return acc;
  }, {});

const emptyReveal = () =>
  API_KEY_FIELDS.reduce((acc, { name }) => {
    acc[name] = false;
    return acc;
  }, {});

export default function ApiKeyManagementSection({ active, onKeysSaved }) {
  const [status, setStatus] = useState({});
  const [inputs, setInputs] = useState(emptyInputs);
  const [reveal, setReveal] = useState(emptyReveal);
  const [isSaving, setIsSaving] = useState(false);
  const [message, setMessage] = useState(null);

  const fetchKeys = async () => {
    try {
      const res = await fetch("/api/api-keys");
      const data = await res.json();
      if (data && !data.error) setStatus(data);
    } catch {
      // Surface read failures only on save attempts; mounting silently is fine.
    }
  };

  useEffect(() => {
    if (active) {
      fetchKeys();
      setMessage(null);
    }
  }, [active]);

  const handleChange = (name) => (e) => {
    setInputs((prev) => ({ ...prev, [name]: e.target.value }));
  };

  const toggleReveal = (name) => () => {
    setReveal((prev) => ({ ...prev, [name]: !prev[name] }));
  };

  const handleSave = async () => {
    const payload = {};
    for (const { name } of API_KEY_FIELDS) {
      const value = inputs[name].trim();
      if (value) payload[name] = value;
    }

    if (Object.keys(payload).length === 0) {
      setMessage({
        type: "error",
        text: "Enter a value for at least one API key.",
      });
      return;
    }

    setIsSaving(true);
    setMessage(null);
    try {
      const res = await fetch("/api/api-keys", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        throw new Error(data.error || "Failed to update API keys");
      }
      setInputs(emptyInputs());
      setReveal(emptyReveal());
      await fetchKeys();
      setMessage({ type: "success", text: "API keys saved." });
      if (typeof onKeysSaved === "function") {
        try {
          await onKeysSaved(data);
        } catch {
          // Parent refresh failures shouldn't surface as save errors.
        }
      }
    } catch (err) {
      setMessage({
        type: "error",
        text: err.message || "Failed to update API keys",
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="mb-5 rounded-xl border border-border-default bg-surface-muted p-5">
      <div className="mb-4">
        <h3 className="m-0 text-lg font-semibold text-text-primary">
          API Key Management
        </h3>
        <p className="mt-1 text-sm text-text-muted">
          Update provider API keys stored in your <code>.env</code> file. Keys
          are hidden by default. Leave a field blank to keep its current value.
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {API_KEY_FIELDS.map(({ name, label, placeholder }) => {
          const isSet = !!status[`${name}_set`];
          const masked = status[name];
          const isRevealed = reveal[name];
          return (
            <div key={name} className="flex flex-col gap-2">
              <label
                htmlFor={`api-key-${name}`}
                className="text-sm font-semibold text-text-primary"
              >
                {label}
              </label>
              <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                <input
                  id={`api-key-${name}`}
                  type={isRevealed ? "text" : "password"}
                  className="flex-1 rounded-lg border border-border-default bg-surface-panel px-3 py-2 font-mono text-sm text-text-primary transition-colors focus:border-primary focus:outline-none disabled:bg-surface-hover"
                  value={inputs[name]}
                  onChange={handleChange(name)}
                  placeholder={placeholder}
                  autoComplete="off"
                  spellCheck={false}
                  disabled={isSaving}
                />
                <button
                  type="button"
                  className="inline-flex items-center justify-center gap-1.5 rounded-lg border border-border-default bg-surface-panel px-3 py-2 text-sm font-medium text-text-primary transition-colors hover:bg-surface-hover"
                  onClick={toggleReveal(name)}
                  aria-pressed={isRevealed}
                  aria-label={isRevealed ? `Hide ${label}` : `Show ${label}`}
                >
                  {isRevealed ? (
                    <EyeOff className="h-4 w-4" />
                  ) : (
                    <Eye className="h-4 w-4" />
                  )}
                  {isRevealed ? "Hide" : "Show"}
                </button>
              </div>
              <span
                className={`rounded px-2 py-1 break-all font-mono text-xs ${
                  isSet
                    ? "bg-emerald-100 text-emerald-900"
                    : "bg-red-100 text-red-900"
                }`}
              >
                Current: {isSet ? masked || "set" : "not set"}
              </span>
            </div>
          );
        })}
      </div>

      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          className={btnPillSm}
          onClick={handleSave}
          disabled={isSaving}
        >
          {isSaving ? "Saving..." : "Save API Keys"}
        </button>
      </div>

      {message && (
        <div
          className={`mt-3 rounded-md px-3 py-2 text-sm font-medium ${
            message.type === "success"
              ? "border border-emerald-200 bg-emerald-50 text-emerald-800"
              : "border border-red-200 bg-red-50 text-red-800"
          }`}
        >
          {message.text}
        </div>
      )}
    </div>
  );
}
