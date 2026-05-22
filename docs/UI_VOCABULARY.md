# UI Vocabulary

Canonical names for UI pieces in this project. Use the **Reference ID** in chat (e.g. “change `listing-bar-pre-link`”) so agents map to the right code without ambiguity.

Full source of truth for agents: this file. Cursor also loads `.cursor/rules/ui-vocabulary.mdc`.

---

## Listing workflow — MessageBarInput (two states)

Both states use the **same** `MessageBarInput` component in `CreateWorkflow.jsx`. They differ by layout and behavior, controlled by `listingLinkSubmitted` (create tab) or `testListingLinkSubmitted` (test-workflow tab).

| Reference ID | Short name | When | What the user sees |
|--------------|------------|------|-------------------|
| `listing-bar-pre-link` | **Pre-link message bar** | Before an eBay link is submitted (`listingLinkSubmitted === false`) | Centered hero: heading “Reimagine Any Listing”, pill input with placeholder “Paste any eBay link”, no fixed top bar |
| `listing-bar-post-link` | **Post-link message bar** | After submit (`listingLinkSubmitted === true`) | Pill input fixed at the **bottom** under sidebar offset, floating above page content (no full-width dock bar or border), always visible (no auto-hide), heading hidden, with an integrated `ChatContextSelector` inside the pill (Title / Description / Photos / Metadata); input placeholder follows the selected context (e.g. “Edit the title”) via `getChatContextInputPlaceholder` |

### Aliases (same thing)

- “message bar before link” / “hero bar” / “landing bar” → `listing-bar-pre-link`
- “message bar after link” / “bottom bar” / “dock” → `listing-bar-post-link`

### Code map

| Reference ID | Component | Wrapper / state |
|--------------|-----------|-----------------|
| `listing-bar-pre-link` | `MessageBarInput` | `CreateWorkflow` when `listingLinkSubmitted` is false — centered `barWrapperClassName`, visible `<h1>`, form `mt-12 md:mt-16` |
| `listing-bar-post-link` | `MessageBarInput` (includes `ChatContextSelector`) | `CreateWorkflow` when `listingLinkSubmitted` is true — fixed bottom float (`fixed bottom-0`, transparent wrapper, `left: sidebarLeft`), Motion `layout` animation from hero, no slide-hide, hidden heading, `showChatContextSelector` on `MessageBarInput` |

**Files**

- `frontend/src/components/MessageBarInput.jsx` — shared input UI
- `frontend/src/components/ChatContextSelector.jsx` — context dropdown shown in `listing-bar-post-link`
- `frontend/src/constants/chatContextModes.js` — `CHAT_CONTEXT_MODES` and `DEFAULT_CHAT_CONTEXT` (single source of truth for AI editor integration)
- `frontend/src/components/CreateWorkflow.jsx` — both states; owns local `chatContext` state for now
- `frontend/src/App.jsx` — sets `listingLinkSubmitted` on fetch (`fetchListingPhotos`); stays true after submit even if the input is cleared

**Props on `MessageBarInput` (both states)**

- `fullWidth`, `value={listingId}`, `onChange={onListingIdChange}`, `placeholder` — `"Paste any eBay link"` pre-link; post-link, per `chatContext` from `getChatContextInputPlaceholder` in `chatContextModes.js`, `disabled={loading}`, `loading={loading}`, `aria-label="eBay listing URL or ID"`

### State transition

1. User on **Create** tab, `listing-bar-pre-link` visible.
2. User submits form → `setListingLinkSubmitted(true)` in `fetchListingPhotos` → UI becomes `listing-bar-post-link` while listing loads and workflow continues.
3. Post-link layout persists after submit; clearing `listingId` does not return to `listing-bar-pre-link`.

---

## Listing workflow — source listing summary

| Reference ID | Short name | When | What the user sees |
|--------------|------------|------|-------------------|
| `listing-source-summary` | **Source listing summary** | After link submit (`listingLinkSubmitted === true`) and listing data is loaded | Compact panel above Original Photos showing the fetched eBay listing: title, `{sku} · date · N images · Cat …` meta line, price on the right, scrollable description. Replaces the old standalone “Current SKU” banner and the bottom `ListingDetails` panel. |

### Aliases (same thing)

- “source listing card” / “listing summary” / “top listing details” → `listing-source-summary`

### Code map

| Reference ID | Component | Wrapper / state |
|--------------|-----------|-----------------|
| `listing-source-summary` | `ListingDetails` | `CreateWorkflow` renders it once when `listingLinkSubmitted && listing`, above `PhotoGallery`. Header layout mirrors `GeneratedListingCard`’s content column. |

**Files**

- `frontend/src/components/ListingDetails.jsx` — summary panel
- `frontend/src/components/CreateWorkflow.jsx` — placement above `PhotoGallery`, passes `listing`, `photos`, `sku={currentSku}`
- `frontend/src/utils/listingDisplay.js` — shared `formatPrice`, `formatListingDateTime`, `formatCategoryShort` (also used by `GeneratedListingCard`)

---

## Adding terms

When adding a new entry, include:

1. **Reference ID** — kebab-case, stable (e.g. `listing-bar-pre-link`)
2. **Short name** — plain English label
3. **When** — user-visible condition or code flag
4. **Code map** — file paths and key variables
