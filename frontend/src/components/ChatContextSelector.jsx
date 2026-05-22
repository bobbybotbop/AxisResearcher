import { useEffect, useRef, useState } from "react";
import { ChevronDown } from "lucide-react";
import { CHAT_CONTEXT_MODES } from "../constants/chatContextModes";

function ChatContextSelector({ value, onChange, disabled = false }) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);

  const selected =
    CHAT_CONTEXT_MODES.find((mode) => mode.id === value) ??
    CHAT_CONTEXT_MODES[0];
  const SelectedIcon = selected.Icon;

  useEffect(() => {
    if (!open) return;
    const handlePointerDown = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    const handleKeyDown = (e) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
    };
  }, [open]);

  const handleSelect = (id) => {
    onChange?.(id);
    setOpen(false);
  };

  return (
    <div ref={rootRef} className="contextSelector">
      <button
        type="button"
        className="contextTrigger"
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
        aria-label={`Chat context: ${selected.label}`}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <SelectedIcon size={18} strokeWidth={1.75} aria-hidden />
        <span className="contextLabel">{selected.label}</span>
        <ChevronDown
          size={16}
          strokeWidth={1.75}
          className={`contextChevron${open ? " contextChevronOpen" : ""}`}
          aria-hidden
        />
      </button>

      {open && (
        <ul
          className="contextMenu"
          role="listbox"
          aria-label="Chat context"
        >
          {CHAT_CONTEXT_MODES.map((mode) => {
            const Icon = mode.Icon;
            const isActive = mode.id === selected.id;
            return (
              <li key={mode.id} role="option" aria-selected={isActive}>
                <button
                  type="button"
                  className={`contextOption${isActive ? " contextOptionActive" : ""}`}
                  onClick={() => handleSelect(mode.id)}
                >
                  <Icon size={16} strokeWidth={1.75} aria-hidden />
                  <span>{mode.label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

export default ChatContextSelector;
