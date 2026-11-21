import { useEffect, useState } from "react";
import { btnPillSm } from "../styles/buttonPill";
import NumberInput from "./NumberInput";

interface TitleSimplificationConfig {
  stopwords: string[];
  max_words: number;
}

interface TitleSimplificationSettingsProps {
  addToast: (type: string, message: string) => void;
}

/**
 * Editable knobs for the Copy Seller title-simplification hook (ticket 07):
 * the sales-term stopword list and the max-words cap behind the deterministic
 * trim. Reads/writes /api/research/title-simplification.
 */
export default function TitleSimplificationSettings({
  addToast,
}: TitleSimplificationSettingsProps) {
  const [stopwords, setStopwords] = useState("");
  const [maxWords, setMaxWords] = useState(6);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const res = await fetch("/api/research/title-simplification");
        if (!res.ok) throw new Error(`Failed to load config (${res.status})`);
        const data: TitleSimplificationConfig = await res.json();
        setStopwords(data.stopwords.join(", "));
        setMaxWords(data.max_words);
      } catch (err) {
        addToast("error", (err as Error).message);
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSave = async (): Promise<void> => {
    setSaving(true);
    try {
      const list = stopwords
        .split(",")
        .map((w) => w.trim())
        .filter((w) => w.length > 0);
      const res = await fetch("/api/research/title-simplification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ stopwords: list, max_words: maxWords }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Failed to save config");
      setStopwords(data.stopwords.join(", "));
      setMaxWords(data.max_words);
      addToast("success", "Title simplification settings saved");
    } catch (err) {
      addToast("error", (err as Error).message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col gap-3 rounded-lg border border-border-default bg-surface-muted p-4">
      <div>
        <h3 className="m-0 text-base font-semibold text-text-primary">
          Copy Seller — Title Simplification
        </h3>
        <p className="mt-1 text-sm text-text-muted">
          Sales terms stripped from listing titles to build the search phrase,
          and the maximum phrase length. Deterministic and offline.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <label
          htmlFor="title-simplification-stopwords"
          className="text-sm font-semibold text-text-primary"
        >
          Stopwords (comma-separated):
        </label>
        <textarea
          id="title-simplification-stopwords"
          rows={3}
          className="rounded-lg border-2 border-border-default bg-surface-panel px-3 py-2 text-sm text-text-primary transition-colors focus:border-primary focus:outline-none disabled:bg-surface-hover"
          value={stopwords}
          onChange={(e) => setStopwords(e.target.value)}
          placeholder="lot, pack, new, purple, ..."
          disabled={loading || saving}
        />
      </div>

      <div className="flex flex-col gap-2">
        <label
          htmlFor="title-simplification-max-words"
          className="text-sm font-semibold text-text-primary"
        >
          Max words:
        </label>
        <NumberInput
          value={maxWords}
          onCommit={setMaxWords}
          min={1}
          max={20}
          commitOn="blur"
          ariaLabel="Max words"
          className="w-24 rounded-lg border-2 border-border-default bg-surface-panel px-3 py-2 text-sm text-text-primary transition-colors focus:border-primary focus:outline-none disabled:bg-surface-hover"
        />
      </div>

      <button
        type="button"
        className={`w-fit ${btnPillSm}`}
        onClick={handleSave}
        disabled={loading || saving}
      >
        {saving ? "Saving..." : "Save Title Simplification"}
      </button>
    </div>
  );
}
