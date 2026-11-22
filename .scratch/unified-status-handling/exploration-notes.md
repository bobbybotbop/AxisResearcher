# Unified Status Store — Frontend Exploration Notes

Date: 2026-11-22
Branch: integration/unified-status-handling

---

## 1. `frontend/src/components/StartupToasts.tsx`

### Store shape

Module-level, hand-rolled external store (no library). Lines 24–37:

```ts
let toasts: StartupToast[] = [];
const listeners = new Set<() => void>();
```

`StartupToast` interface (lines 6–11):

```ts
interface StartupToast {
  id: number;
  status: "pending" | "success" | "error";
  label: string;
  message?: string;
}
```

Mutations replace the array (`toasts = [...]` / `.map` / `.filter`) so `useSyncExternalStore` snapshots stay referentially stable. `emit()` calls every listener, wrapping each in try/catch.

### `startTaskToast` handle API

Signature (line 54):

```ts
export function startTaskToast(label: string): TaskToastHandle
```

`TaskToastHandle` interface (lines 13–20):

```ts
export interface TaskToastHandle {
  update: (label: string, message?: string) => void;
  succeed: (message?: string) => void;
  fail: (message: string) => void;
}
```

Behavior:
- `id = Date.now() + Math.random()` (line 55).
- Never throws — all mutations wrapped in try/catch with `console.warn`.
- `update(label, message?)` — patches label/message in place; no-op after settle.
- `succeed(message?)` — sets status `success`, auto-dismisses after `SUCCESS_DISMISS_MS = 5000` (line 22, 78).
- `fail(message)` — sets status `error`, persists until manual dismiss.
- `settled` flag guards against double-settle.

Also exported: `dismissTaskToast(id: number)` (line 45).

### Subscription / render

`StartupToasts` default-export component (line 162):
- `useSyncExternalStore(subscribe, getSnapshot)` (line 163).
- Returns `null` when empty.
- Renders via `ReactDOM.createPortal` into `document.body` (line 165).
- Fixed bottom-right, `z-[9999]`, `pointer-events-none` container, `pointer-events-auto` items.
- Each item: spinner for `pending`, ✓/✕ for settled, dismiss button only when not pending.

### Mount point

`frontend/src/App.tsx`:
- Imported line 17: `import StartupToasts, { startTaskToast } from "./components/StartupToasts";`
- Rendered line 3914: `<StartupToasts />` (inside root layout div, sibling to `<ToastContainer />`).

---

## 2. `frontend/src/components/ToastContainer.tsx` + `addToast`

### `Toast` type

`frontend/src/types/toast.ts`:

```ts
export interface Toast {
  id: number;
  type: "success" | "error";
  message: string;
  detail?: string;
}
```

### `addToast` definition

`frontend/src/App.tsx` lines 155–162:

```ts
const [toasts, setToasts] = useState<Toast[]>([]);
const addToast = (type: "success" | "error", message: string, detail?: string): void => {
  const id = Date.now() + Math.random();
  setToasts((prev) => [...prev, { id, type, message, detail }]);
};
const removeToast = useCallback((id: number): void => {
  setToasts((prev) => prev.filter((t) => t.id !== id));
}, []);
```

Note: `type` is typed `"success" | "error"` in App.tsx, but several call sites pass `"info"` (type-cast away at prop boundaries, e.g. `addToast as (type: string, message: string) => void`).

### `ToastContainer` component

`frontend/src/components/ToastContainer.tsx`:
- Props: `{ toasts: Toast[]; onRemove: (id: number) => void }`.
- Portal to `document.body`, fixed top-center (`top: 1rem; left: 50%; translateX(-50%); z-index: 9999`).
- Success toasts auto-dismiss after 4000 ms (line 13); error toasts persist.
- `aria-live="assertive"`.

### Call-site count

- `addToast(` appears **45 times** in `App.tsx` alone (includes definition line; ~44 call sites).
- Additional call sites in child components that receive `addToast` as a prop:
  - `ImageSearchSteps.tsx` (prop, ~5 calls)
  - `RenderProfileDropdown.tsx` (prop, 2 calls)
  - `RenderProfileEditor.tsx` (prop, 5 calls)
  - `ResearchPipeline.tsx` (prop, 5 calls)
  - `SharedDownloadRender.tsx` (prop, 2 calls)
  - `TitleSearchPipeline.tsx` (prop, ~7 calls)
  - `TitleSimplificationSettings.tsx` (prop, 3 calls)
  - `filterThreeDResults.ts` (utility, 1 call)

**Total: ~70+ call sites across 9 files.**

---

## 3. Global state management

**None.** No zustand, redux, jotai, recoil, valtio, mobx. No `createContext`/`useContext` anywhere in `src/`.

`frontend/package.json` dependencies (relevant excerpt):

```
react, react-dom, react-router-dom, styled-components,
@react-three/fiber, @react-three/drei, three, fabric,
motion, lucide-react, @mynaui/icons-react, jszip,
@hello-pangea/dnd
```

All state is `useState` / `useRef` / `useCallback` in `App.tsx` (5545 lines) with prop drilling. The only "global" pattern is the hand-rolled module-level store in `StartupToasts.tsx` (see §1), which is the closest existing analog to the proposed unified store.

---

## 4. `frontend/src/utils/fetchWithProgress.ts` — NDJSON event shape

Parses newline-delimited JSON from a streaming `fetch` response body.

```ts
interface ProgressEvent {
  type: "progress";
  [key: string]: unknown;   // arbitrary fields: step, status, title, etc.
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
```

Signature:

```ts
export async function fetchWithProgress(
  url: string,
  options: RequestInit,
  onProgress: (event: ProgressEvent) => void,
): Promise<unknown>
```

Behavior:
- Reads `response.body` as a stream, splits on `\n`, JSON-parses each line.
- `type: "progress"` → forwarded to `onProgress` callback.
- `type: "result"` → captured; returned as the resolved value.
- `type: "error"` → captured; thrown as `Error(errorMsg)` at end.
- Malformed lines are warned and skipped.

### Observed `ProgressEvent` fields in the wild

From `ResearchPipeline.tsx` (lines 159–184) and `App.tsx` (lines 1057–1068):
- `step: string` — step name, e.g. `"Computing metrics (3/12)"`.
- `status: "in_progress" | "completed"`.
- `title?: string` — e.g. listing title during metrics computation.

The backend emits these from the Copy Seller pipeline and the photos/bg-removal endpoints.

### Call sites

`fetchWithProgress` is used in 7 files:
- `App.tsx` (5 call sites: bg-removal batch, photos fetch, create listing, upload, test workflow)
- `ImageSearchSteps.tsx`
- `RenderProfileEditor.tsx`
- `ResearchPipeline.tsx`
- `SharedDownloadRender.tsx`
- `TitleSearchPipeline.tsx`

---

## 5. Where `StartupToasts` is rendered / how `startTaskToast` is imported

### Render

`frontend/src/App.tsx` line 3914, inside the root return:

```tsx
<div className="flex min-h-screen bg-surface-app text-text-primary">
  <ToastContainer toasts={toasts} onRemove={removeToast} />   {/* line 3913 */}
  <StartupToasts />                                          {/* line 3914 */}
  <aside ...>
```

Both toast systems are mounted side-by-side at the app root. `StartupToasts` needs no props (self-contained store); `ToastContainer` receives `toasts` + `removeToast` from App-level `useState`.

### `startTaskToast` import

Only imported in `App.tsx` line 17:

```ts
import StartupToasts, { startTaskToast } from "./components/StartupToasts";
```

Two call sites, both in `App.tsx`:
1. Line 2408 — `startTaskToast("Refreshing eBay quantities…")` → `toast.succeed(...)` / `toast.fail(...)`.
2. Line 2779 — `startTaskToast("Refreshing eBay tokens…")` → `toast.update("Syncing with eBay…")` → `toast.succeed(...)` / `toast.fail(...)`.

No other file imports `startTaskToast`.

---

## 6. Existing pipeline / progress UI (context for the unified store)

### `ProgressIndicator` component

`frontend/src/components/ProgressIndicator.tsx` — reusable ordered-step list:
- Props: `{ steps: string[]; currentStep: string | null; completedSteps?: string[]; showProgressBar?: boolean }`.
- Renders a progress bar (`completedCount / totalCount`) + per-step rows with ✓ / spinner / ○ icons.
- Used in `CreateWorkflow.tsx` (3 instances: fetch, create-listing, upload) and `ResearchPipeline.tsx` (1 instance).

### Pipeline step model (Researc
hPipeline)

`frontend/src/components/ResearchPipeline.tsx` lines 16-20:

```ts
const STEP_BUDGET = "Checking API budget";
const STEP_COLLECT = "Collecting seller listings";
const STEP_DETAILS = "Fetching listing details";
const STEP_METRICS = "Computing metrics";
const PIPELINE_STEPS = [STEP_BUDGET, STEP_COLLECT, STEP_DETAILS, STEP_METRICS];
```

State tracked locally with `useState`: `currentStep`, `completedSteps`, `metricsProgress` (`{ current, total, title }`), `isRunning`. Progress events from `fetchWithProgress` drive transitions. This is the canonical "pipeline as ordered task sequence" pattern the unified store should absorb.

### Ad-hoc progress state in App.tsx

`App.tsx` line 384:

```ts
const [bgRemovalProgress, setBgRemovalProgress] = useState<ProgressState>({ ... });
```

Similar `ProgressState` shapes are threaded into `CreateWorkflow.tsx` as props (`fetchProgress`, `createListingProgress`, `uploadProgress`, `bgRemovalProgress`). These are all local `useState` + prop drilling — prime candidates for the unified store.

---

## Summary for the implementer

| Concern | Current state | Files |
|---|---|---|
| Task toasts (pending/success/error) | Hand-rolled module store + `useSyncExternalStore` | `StartupToasts.tsx` |
| One-shot notifications (success/error) | `useState` in App + prop drilling | `App.tsx`, `ToastContainer.tsx`, `types/toast.ts` |
| Pipeline progress (ordered steps) | Local `useState` per component | `ResearchPipeline.tsx`, `CreateWorkflow.tsx`, `ProgressIndicator.tsx` |
| Streaming progress transport | NDJSON over `fetch` | `utils/fetchWithProgress.ts` |
| Global state library | **None** | — |

The unified Status Store should replace: (a) the `StartupToasts` module store, (b) the `App.tsx` `toasts` state + `addToast` prop drilling, and (c) the per-component `currentStep`/`completedSteps` pipeline state. `fetchWithProgress` can stay as the transport layer; its `ProgressEvent` shape (`{ type: "progress", step, status, title, ... }`) is the natural input to the store's task-update actions.
