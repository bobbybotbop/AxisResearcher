# Chat Bar AI Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Repurpose the bottom input bar (post-link state) so submitting a prompt regenerates the title, description, photos, or metadata depending on the selected `ChatContextSelector` mode.

**Architecture:** A single `handleChatSubmit(prompt, context)` handler in `App.jsx` dispatches to four dedicated handlers. The bar's form `onSubmit` branches on `listingLinkSubmitted` — pre-link continues calling `fetchListingPhotos`, post-link calls `handleChatSubmit` and clears the input. Three new Flask endpoints handle title/description/metadata regeneration; photo re-generation reuses the existing image generation infrastructure with a new selection-mode UI state.

**Tech Stack:** React (Vite), Flask, `call_text_llm` from `backend/ebay_cli.py`, existing `update_listing_title_description` and `load_listing_data` from `backend/copyScripts/combine_data.py`.

---

## File Map

| File | Change |
|---|---|
| `frontend/src/components/CreateWorkflow.jsx` | Branch form `onSubmit`; add `onChatSubmit` prop; pass photo-selection props to image grid |
| `frontend/src/App.jsx` | Add `handleChatSubmit`, `regenerateTitle`, `regenerateDescription`, `enterPhotoSelectionMode`, `regenerateMetadata`; new state flags; new props to `CreateWorkflow` |
| `app.py` | Add `POST /api/regenerate-title`, `POST /api/regenerate-description`, `POST /api/regenerate-metadata` |
| `backend/copyScripts/combine_data.py` | Add `extract_metadata_for_llm(listing_data)` helper |

---

## Task 1: Clear input on post-link submit + wire `onChatSubmit` prop

**Files:**
- Modify: `frontend/src/components/CreateWorkflow.jsx:120-144`
- Modify: `frontend/src/App.jsx` (add `onChatSubmit` prop pass-through)

- [ ] **Step 1: Add `onChatSubmit` to `CreateWorkflow` props destructuring**

In `CreateWorkflow.jsx`, find the props list starting at line 16 and add `onChatSubmit` after `onSubmit`:

```jsx
  onSubmit,
  onChatSubmit,
```

- [ ] **Step 2: Replace the `<form onSubmit>` handler with a branching handler**

In `CreateWorkflow.jsx`, replace:
```jsx
        <form
          onSubmit={onSubmit}
```
with:
```jsx
        <form
          onSubmit={(e) => {
            if (!listingLinkSubmitted) {
              onSubmit(e);
            } else {
              e.preventDefault();
              const prompt = listingId.trim();
              if (!prompt) return;
              onListingIdChange("");
              onChatSubmit(prompt, chatContext);
            }
          }}
```

- [ ] **Step 3: Add stub `handleChatSubmit` in `App.jsx` and pass as prop**

In `App.jsx`, add after `handleSubmit` (around line 932):

```js
  const handleChatSubmit = (prompt, context) => {
    if (context === "title") regenerateTitle(prompt);
    else if (context === "description") regenerateDescription(prompt);
    else if (context === "photos") enterPhotoSelectionMode(prompt);
    else if (context === "metadata") regenerateMetadata(prompt);
  };

  const regenerateTitle = async (_prompt) => { /* TODO Task 2 */ };
  const regenerateDescription = async (_prompt) => { /* TODO Task 3 */ };
  const enterPhotoSelectionMode = (_prompt) => { /* TODO Task 4 */ };
  const regenerateMetadata = async (_prompt) => { /* TODO Task 5 */ };
```

In the `<CreateWorkflow>` JSX (around line 3127), add the new prop:
```jsx
              onSubmit={handleSubmit}
              onChatSubmit={handleChatSubmit}
```

- [ ] **Step 4: Verify manually**

Start the dev server (`npm run dev`), paste an eBay link, wait for the bar to move to the bottom, type something in the bar and press Enter — the input should clear and nothing should crash (handlers are stubs). The pre-link flow (pasting a URL into the centered hero bar) must still work.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/CreateWorkflow.jsx frontend/src/App.jsx
git commit -m "feat: branch chat bar submit — clear input + dispatch onChatSubmit post-link"
```

---

## Task 2: Title regeneration (backend + frontend)

**Files:**
- Modify: `app.py` (add `/api/regenerate-title`)
- Modify: `frontend/src/App.jsx` (implement `regenerateTitle`)

- [ ] **Step 1: Add the Flask endpoint in `app.py`**

Add after the `update_title` route (after line ~1068):

```python
@app.route('/api/regenerate-title', methods=['POST'])
def regenerate_title():
    """
    Regenerate the listing title using the LLM.

    Accepts JSON body:
    {
        "sku": "AXIS_XX",
        "current_title": "current editable title",
        "user_prompt": "make it shorter and highlight the brand",
        "model": "deepseek/deepseek-v4-flash"
    }
    """
    try:
        print("[API] /api/regenerate-title endpoint called")
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        sku = data.get("sku")
        current_title = data.get("current_title", "")
        user_prompt = data.get("user_prompt", "")
        model = data.get("model", DEFAULT_TEXT_MODEL)

        if not sku:
            return jsonify({"error": "sku is required"}), 400
        if not current_title:
            return jsonify({"error": "current_title is required"}), 400
        if not user_prompt:
            return jsonify({"error": "user_prompt is required"}), 400

        from backend.ebay_cli import call_text_llm
        prompt = (
            f"Here is an eBay listing title:\n\n{current_title}\n\n"
            f"Please edit the title according to this instruction: {user_prompt}\n\n"
            "Return only the new title text, no quotes, no explanation."
        )
        result = call_text_llm(prompt, model=model)
        if not result:
            return jsonify({"error": "LLM returned no response"}), 500

        new_title = result.strip().strip('"').strip("'")

        listing_data = load_listing_data(sku=sku)
        if listing_data:
            current_desc = listing_data.get("inventoryItem", {}).get("product", {}).get("description", "")
            update_listing_title_description(sku, {
                "edited_title": new_title,
                "edited_description": current_desc
            })

        updated_data = load_listing_data(sku=sku)
        return jsonify({"title": new_title, "listing_data": updated_data}), 200

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while regenerating title (encoding error)"
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {error_msg}"}), 500
```

- [ ] **Step 2: Implement `regenerateTitle` in `App.jsx`**

Add new state flag after `isSavingDescription` (around line 344):
```js
  const [isRegeneratingTitle, setIsRegeneratingTitle] = useState(false);
```

Replace the stub `regenerateTitle` with:
```js
  const regenerateTitle = async (prompt) => {
    if (!currentSku || !editableTitle) return;
    setIsRegeneratingTitle(true);
    try {
      const res = await fetch("/api/regenerate-title", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku: currentSku,
          current_title: editableTitle,
          user_prompt: prompt,
          model: textModel,
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setError(data.error || "Failed to regenerate title");
        return;
      }
      setEditableTitle(data.title);
      if (data.listing_data) setListingData(data.listing_data);
    } catch (err) {
      setError(err.message || "Failed to regenerate title");
    } finally {
      setIsRegeneratingTitle(false);
    }
  };
```

- [ ] **Step 3: Pass `isRegeneratingTitle` as `loading` to the bar (optional visual feedback)**

In the `<CreateWorkflow>` JSX, update `loading` prop on the bar so it shows a spinner while regenerating. The existing `loading` prop controls the bar's `disabled`/`loading` state. Add `isRegeneratingTitle` to the bar-disabled calculation.

In `App.jsx` near line 3106, the existing prop is:
```jsx
              loading={loading}
```
Change to:
```jsx
              loading={loading || isRegeneratingTitle || isRegeneratingDescription || isRegeneratingMetadata}
```
(The other two flags are defined in Tasks 3 and 5 — declare them as `false` stubs for now alongside `isRegeneratingTitle` so this doesn't break.)

Add alongside `isRegeneratingTitle`:
```js
  const [isRegeneratingDescription, setIsRegeneratingDescription] = useState(false);
  const [isRegeneratingMetadata, setIsRegeneratingMetadata] = useState(false);
```

- [ ] **Step 4: Test manually**

Start dev server, create a listing, wait for title to generate, type "make it shorter" in the bottom bar with Title context selected, press Enter. The title field should update with a new value. Check network tab for `POST /api/regenerate-title` returning 200.

- [ ] **Step 5: Commit**

```bash
git add app.py frontend/src/App.jsx
git commit -m "feat: regenerate title via bottom chat bar"
```

---

## Task 3: Description regeneration (backend + frontend)

**Files:**
- Modify: `app.py` (add `/api/regenerate-description`)
- Modify: `frontend/src/App.jsx` (implement `regenerateDescription`)

- [ ] **Step 1: Add the Flask endpoint in `app.py`**

Add after the `regenerate_title` route:

```python
@app.route('/api/regenerate-description', methods=['POST'])
def regenerate_description():
    """
    Regenerate the listing description using the LLM.

    Accepts JSON body:
    {
        "sku": "AXIS_XX",
        "current_description": "<p>...</p>",
        "user_prompt": "add bullet points for features",
        "model": "deepseek/deepseek-v4-flash"
    }
    """
    try:
        print("[API] /api/regenerate-description endpoint called")
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        sku = data.get("sku")
        current_description = data.get("current_description", "")
        user_prompt = data.get("user_prompt", "")
        model = data.get("model", DEFAULT_TEXT_MODEL)

        if not sku:
            return jsonify({"error": "sku is required"}), 400
        if not current_description:
            return jsonify({"error": "current_description is required"}), 400
        if not user_prompt:
            return jsonify({"error": "user_prompt is required"}), 400

        from backend.ebay_cli import call_text_llm
        prompt = (
            f"Here is an eBay listing description (HTML):\n\n{current_description}\n\n"
            f"Please edit the description according to this instruction: {user_prompt}\n\n"
            "Return only the new description HTML, no explanation, no markdown fences."
        )
        result = call_text_llm(prompt, model=model)
        if not result:
            return jsonify({"error": "LLM returned no response"}), 500

        new_description = result.strip()

        listing_data = load_listing_data(sku=sku)
        if listing_data:
            current_title = listing_data.get("inventoryItem", {}).get("product", {}).get("title", "")
            update_listing_title_description(sku, {
                "edited_title": current_title,
                "edited_description": new_description
            })

        updated_data = load_listing_data(sku=sku)
        return jsonify({"description": new_description, "listing_data": updated_data}), 200

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while regenerating description (encoding error)"
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {error_msg}"}), 500
```

- [ ] **Step 2: Implement `regenerateDescription` in `App.jsx`**

Replace the stub `regenerateDescription` with:
```js
  const regenerateDescription = async (prompt) => {
    if (!currentSku || !editableDescription) return;
    setIsRegeneratingDescription(true);
    try {
      const res = await fetch("/api/regenerate-description", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku: currentSku,
          current_description: editableDescription,
          user_prompt: prompt,
          model: textModel,
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setError(data.error || "Failed to regenerate description");
        return;
      }
      setEditableDescription(data.description);
      if (data.listing_data) setListingData(data.listing_data);
    } catch (err) {
      setError(err.message || "Failed to regenerate description");
    } finally {
      setIsRegeneratingDescription(false);
    }
  };
```

- [ ] **Step 3: Test manually**

Create a listing, switch context selector to Description, type "add bullet points for key features" in bar, press Enter. Description field should update. Check network tab for `POST /api/regenerate-description` 200.

- [ ] **Step 4: Commit**

```bash
git add app.py frontend/src/App.jsx
git commit -m "feat: regenerate description via bottom chat bar"
```

---

## Task 4: Photo selection mode + targeted re-generation

**Files:**
- Modify: `frontend/src/App.jsx` (add selection-mode state + `enterPhotoSelectionMode` + `handleConfirmPhotoRegeneration`)
- Modify: `frontend/src/components/CreateWorkflow.jsx` (pass selection props to image grid, add confirm button)

> Note: The existing image grid in `CreateWorkflow.jsx` already has `selectedImagesForRegen` and `onImageSelection` props wired to `handleImageSelection` in `App.jsx`. Selection mode here means auto-selecting all images and showing the confirm UI. Re-generation reuses `handleRegenerateImages`.

- [ ] **Step 1: Add photo selection mode state in `App.jsx`**

After the `isRegeneratingMetadata` state (from Task 2/5), add:
```js
  const [photoSelectionActive, setPhotoSelectionActive] = useState(false);
  const [pendingPhotoPrompt, setPendingPhotoPrompt] = useState("");
```

- [ ] **Step 2: Implement `enterPhotoSelectionMode` in `App.jsx`**

Replace the stub:
```js
  const enterPhotoSelectionMode = (prompt) => {
    if (!generatedImages || generatedImages.length === 0) return;
    setPendingPhotoPrompt(prompt);
    setPhotoSelectionActive(true);
    // Auto-select all generated images by index
    setSelectedImagesForRegen(generatedImages.map((_, i) => i));
  };
```

- [ ] **Step 3: Add a `promptOverride` parameter to `handleRegenerateImages` in `App.jsx`**

`handleRegenerateImages` reads `customPrompt` from state closure, which won't reflect a same-render `setCustomPrompt` call. The fix is to accept an optional override.

Find `handleRegenerateImages` (around line 1187). Change its signature and the prompt resolution line:
```js
  const handleRegenerateImages = async (promptOverride) => {
    const promptToUse = (promptOverride ?? customPrompt)?.trim();
    if (!promptToUse) {
      setError("Please enter a prompt to guide the regeneration");
      return;
    }
```
Also find the line inside the function body:
```js
      const promptToUse = customPrompt.trim();
```
and **remove it** — it is now set at the top.

- [ ] **Step 4: Implement `handleConfirmPhotoRegeneration` in `App.jsx`**

Add after `enterPhotoSelectionMode`:
```js
  const handleConfirmPhotoRegeneration = () => {
    const prompt = pendingPhotoPrompt;
    setPhotoSelectionActive(false);
    setPendingPhotoPrompt("");
    handleRegenerateImages(prompt);
  };

  const handleCancelPhotoRegeneration = () => {
    setPhotoSelectionActive(false);
    setPendingPhotoPrompt("");
    setSelectedImagesForRegen([]);
  };
```

- [ ] **Step 5: Pass new props to `CreateWorkflow` in `App.jsx`**

In the `<CreateWorkflow>` JSX block (around line 3091), add:
```jsx
              photoSelectionActive={photoSelectionActive}
              pendingPhotoPrompt={pendingPhotoPrompt}
              onConfirmPhotoRegeneration={handleConfirmPhotoRegeneration}
              onCancelPhotoRegeneration={handleCancelPhotoRegeneration}
```

- [ ] **Step 6: Accept new props in `CreateWorkflow.jsx` and show confirm UI**

Add to `CreateWorkflow` props destructuring:
```jsx
  photoSelectionActive = false,
  pendingPhotoPrompt = "",
  onConfirmPhotoRegeneration,
  onCancelPhotoRegeneration,
```

Find where the generated images grid is rendered in `CreateWorkflow.jsx` (the section showing `generatedImages`). After the grid, add the confirm/cancel UI that shows only when `photoSelectionActive` is true:

```jsx
{photoSelectionActive && (
  <div className="mt-3 flex items-center gap-3 rounded-xl border border-border-default bg-surface-panel px-4 py-3">
    <span className="flex-1 text-sm text-text-muted">
      Regenerate selected with: <span className="font-medium text-text-primary">&quot;{pendingPhotoPrompt}&quot;</span>
    </span>
    <button
      type="button"
      className={btnPillSm}
      onClick={onCancelPhotoRegeneration}
    >
      Cancel
    </button>
    <button
      type="button"
      className={btnPillLg}
      onClick={onConfirmPhotoRegeneration}
    >
      Regenerate Selected
    </button>
  </div>
)}
```

- [ ] **Step 7: Test manually**

Create a listing, generate images, switch context to Photos, type "use a pure white background" in the bar, press Enter. All image checkboxes should become checked, and the confirm banner should appear with the prompt text. Uncheck one image. Click "Regenerate Selected" — only the checked images should re-generate. Cancel should dismiss without regenerating.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/App.jsx frontend/src/components/CreateWorkflow.jsx
git commit -m "feat: photo selection mode from chat bar with targeted re-generation"
```

---

## Task 5: Metadata regeneration (backend + frontend)

**Files:**
- Modify: `backend/copyScripts/combine_data.py` (add `extract_metadata_for_llm`)
- Modify: `app.py` (add `/api/regenerate-metadata`)
- Modify: `frontend/src/App.jsx` (implement `regenerateMetadata`)

- [ ] **Step 1: Add `extract_metadata_for_llm` to `combine_data.py`**

Find `load_listing_data` in `combine_data.py`. After it, add:

```python
def extract_metadata_for_llm(listing_data):
    """
    Extract only the eBay-upload-relevant fields from a draft listing dict,
    suitable for sending to an LLM for editing.

    Strips internal bookkeeping fields (sku, createdDateTime, ebayListingId,
    models) and returns a clean dict with inventoryItem product aspects,
    condition, and offer pricing/category — the fields a seller would actually
    want to edit.
    """
    inventory = listing_data.get("inventoryItem", {})
    product = inventory.get("product", {})
    offer = listing_data.get("offer", {})

    return {
        "condition": inventory.get("condition", ""),
        "aspects": product.get("aspects", {}),
        "price": offer.get("pricingSummary", {}).get("price", {}),
        "categoryId": offer.get("categoryId", ""),
    }
```

Also add `extract_metadata_for_llm` to the existing import line in `app.py` (see Step 2).

- [ ] **Step 2: Add `extract_metadata_for_llm` to the `app.py` import**

In `app.py`, find the line (around line 26):
```python
from backend.copyScripts.combine_data import get_next_sku, create_listing_with_preferences, update_listing_images, update_listing_title_description, update_listing_meta_data, load_listing_data, update_listing_with_aspects, save_ebay_listing_id, update_listing_models, get_auto_restock_settings, save_auto_restock_settings, update_local_listing_quantity
```
Add `extract_metadata_for_llm` to the end of that import.

- [ ] **Step 3: Add the Flask endpoint in `app.py`**

After `regenerate_description`, add:

```python
@app.route('/api/regenerate-metadata', methods=['POST'])
def regenerate_metadata():
    """
    Regenerate listing metadata (aspects, condition, price, category) using LLM.

    Accepts JSON body:
    {
        "sku": "AXIS_XX",
        "user_prompt": "it is black and made in the US",
        "model": "deepseek/deepseek-v4-flash"
    }
    """
    try:
        print("[API] /api/regenerate-metadata endpoint called")
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        sku = data.get("sku")
        user_prompt = data.get("user_prompt", "")
        model = data.get("model", DEFAULT_TEXT_MODEL)

        if not sku:
            return jsonify({"error": "sku is required"}), 400
        if not user_prompt:
            return jsonify({"error": "user_prompt is required"}), 400

        listing_data = load_listing_data(sku=sku)
        if not listing_data:
            return jsonify({"error": f"Listing not found for SKU: {sku}"}), 404

        metadata = extract_metadata_for_llm(listing_data)
        metadata_json = json.dumps(metadata, indent=2)

        from backend.ebay_cli import call_text_llm
        prompt = (
            f"{metadata_json}\n\n"
            f"Please edit the JSON according to this instruction and keep it in JSON format.\n\n"
            f"{user_prompt}"
        )
        result = call_text_llm(prompt, model=model)
        if not result:
            return jsonify({"error": "LLM returned no response"}), 500

        # Strip markdown fences if present
        clean = result.strip()
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.startswith("json"):
                clean = clean[4:]
        clean = clean.strip()

        try:
            updated_metadata = json.loads(clean)
        except json.JSONDecodeError as e:
            return jsonify({"error": f"LLM returned malformed JSON: {str(e)}. Raw: {result[:300]}"}), 400

        # Merge updated fields back into the listing file
        inventory = listing_data.get("inventoryItem", {})
        product = inventory.get("product", {})
        offer = listing_data.get("offer", {})

        if "condition" in updated_metadata:
            inventory["condition"] = updated_metadata["condition"]
        if "aspects" in updated_metadata:
            product["aspects"] = updated_metadata["aspects"]
        if "price" in updated_metadata:
            offer.setdefault("pricingSummary", {})["price"] = updated_metadata["price"]
        if "categoryId" in updated_metadata:
            offer["categoryId"] = updated_metadata["categoryId"]

        inventory["product"] = product
        listing_data["inventoryItem"] = inventory
        listing_data["offer"] = offer

        # Write updated listing back to disk
        base_dir = os.path.dirname(os.path.abspath(__file__))
        output_dir = os.path.join(base_dir, "Generated_Listings")
        filepath = os.path.join(output_dir, f"{sku}.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(listing_data, f, indent=2, ensure_ascii=False)

        updated_data = load_listing_data(sku=sku)
        return jsonify({"metadata": updated_metadata, "listing_data": updated_data}), 200

    except Exception as e:
        try:
            error_msg = str(e)
        except UnicodeEncodeError:
            error_msg = "An error occurred while regenerating metadata (encoding error)"
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"An error occurred: {error_msg}"}), 500
```

- [ ] **Step 4: Implement `regenerateMetadata` in `App.jsx`**

Replace the stub `regenerateMetadata` with:
```js
  const regenerateMetadata = async (prompt) => {
    if (!currentSku) return;
    setIsRegeneratingMetadata(true);
    try {
      const res = await fetch("/api/regenerate-metadata", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          sku: currentSku,
          user_prompt: prompt,
          model: textModel,
        }),
      });
      const data = await res.json();
      if (!res.ok || data.error) {
        setError(data.error || "Failed to regenerate metadata");
        return;
      }
      if (data.listing_data) setListingData(data.listing_data);
    } catch (err) {
      setError(err.message || "Failed to regenerate metadata");
    } finally {
      setIsRegeneratingMetadata(false);
    }
  };
```

- [ ] **Step 5: Test manually**

Create a listing, switch context selector to Metadata, type "it is black and made in the US", press Enter. Check that `listingData` gets updated (visible in the ListingDetails panel if it shows aspects). Check network tab for `POST /api/regenerate-metadata` returning 200 and a valid JSON body. Also test a prompt that would cause malformed JSON from the LLM — the endpoint should return a 400 with the error message surfaced in the UI.

- [ ] **Step 6: Commit**

```bash
git add backend/copyScripts/combine_data.py app.py frontend/src/App.jsx
git commit -m "feat: regenerate metadata via bottom chat bar"
```

---

## Task 6: Test-workflow mirror

**Files:**
- Modify: `frontend/src/App.jsx` (add test-workflow stubs for each new handler)

- [ ] **Step 1: Find the test-workflow `<CreateWorkflow>` render (around line 3091)**

The test-workflow tab renders a second `<CreateWorkflow>` with props prefixed `test*`. Find the second `<CreateWorkflow>` block after the `activeTab === "test-workflow"` check.

- [ ] **Step 2: Add `testHandleChatSubmit` and stubs**

After the real `handleChatSubmit` group, add:

```js
  const testHandleChatSubmit = (prompt, context) => {
    console.log("[Test] chat submit:", context, prompt);
    // Simulate a 1.5s delay and set a mock result depending on context
    if (context === "title") {
      setTimeout(() => {
        setTestListingData((prev) => prev ? {
          ...prev,
          inventoryItem: {
            ...prev.inventoryItem,
            product: {
              ...prev.inventoryItem.product,
              title: `[Regenerated] ${prompt}`,
            },
          },
        } : prev);
      }, 1500);
    } else if (context === "description") {
      setTimeout(() => {
        setTestListingData((prev) => prev ? {
          ...prev,
          inventoryItem: {
            ...prev.inventoryItem,
            product: {
              ...prev.inventoryItem.product,
              description: `<p>[Regenerated description for: ${prompt}]</p>`,
            },
          },
        } : prev);
      }, 1500);
    }
    // photos and metadata: no-op in test mode (photo selection involves real image list)
  };
```

> Note: `testListingData` and `setTestListingData` already exist as part of the test-workflow state.

- [ ] **Step 3: Pass `onChatSubmit` to the test-workflow `<CreateWorkflow>`**

In the test-workflow `<CreateWorkflow>` JSX, add:
```jsx
              onChatSubmit={testHandleChatSubmit}
```

Also pass the photo selection props with no-ops so the component doesn't crash:
```jsx
              photoSelectionActive={false}
              pendingPhotoPrompt=""
              onConfirmPhotoRegeneration={() => {}}
              onCancelPhotoRegeneration={() => {}}
```

- [ ] **Step 4: Test manually**

Open the Test Workflow tab, paste the mock link, wait for the bar to move to bottom. Type a prompt with Title context — after ~1.5s the title should change to `[Regenerated] <your prompt>`. Description context should similarly update.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: mirror chat bar handlers in test-workflow tab"
```
