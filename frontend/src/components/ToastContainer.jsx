import { useEffect } from "react";
import ReactDOM from "react-dom";

function Toast({ toast, onRemove }) {
  useEffect(() => {
    if (toast.type === "success") {
      const t = setTimeout(() => onRemove(toast.id), 4000);
      return () => clearTimeout(t);
    }
  }, [toast.id, toast.type, onRemove]);

  const isSuccess = toast.type === "success";
  return (
    <div
      className={`flex items-start gap-3 rounded-lg px-4 py-3 shadow-lg ${
        isSuccess ? "bg-success text-white" : "bg-red-600 text-white"
      }`}
      style={{ minWidth: "280px", maxWidth: "480px" }}
    >
      <span className="mt-0.5 shrink-0 text-sm font-bold">
        {isSuccess ? "✓" : "✕"}
      </span>
      <div className="flex-1">
        <p className="text-sm font-medium leading-snug">{toast.message}</p>
        {toast.detail && (
          <p className="mt-0.5 text-xs opacity-80">{toast.detail}</p>
        )}
      </div>
      <button
        onClick={() => onRemove(toast.id)}
        className="ml-1 shrink-0 text-sm opacity-60 hover:opacity-100"
        aria-label="Dismiss"
      >
        ✕
      </button>
    </div>
  );
}

export default function ToastContainer({ toasts, onRemove }) {
  if (toasts.length === 0) return null;
  return ReactDOM.createPortal(
    <div
      className="flex flex-col gap-2"
      style={{
        position: "fixed",
        top: "1rem",
        left: "50%",
        transform: "translateX(-50%)",
        zIndex: 9999,
      }}
    >
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onRemove={onRemove} />
      ))}
    </div>,
    document.body,
  );
}
