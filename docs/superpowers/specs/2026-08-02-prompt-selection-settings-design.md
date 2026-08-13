# Prompt Selection Settings Design

**Date:** 2026-08-02

## Overview

Add a Prompt Selection section to the Settings tab. Users can choose which prompt file drives title generation, description generation, and each of the 4 image generation types. Users can also add new prompts from within the UI. Prompt files are organized into 3 subfolders on disk. Selections are persisted in localStorage.

---

## 1. Prompt Folder Structure

Move existing prompt files into 3 typed subfolders. Non-selectable system prompts stay in `prompts/` root.

```
prompts/
  title/
    generateTitlePrompt.txt              (existing, default for title)
  description/
    generateDescriptionPrompt.txt        (existing, default for description)
  image/
    generateImageFromProfessional.txt    (existing file renamed: remove extensionless)
    generateImageFromWorld.txt           (existing, default for REAL_WORLD)
    generateImageAngleVariant.txt        (existing)
    experimental.txt                     (existing)
    generateImageStabilityControl.txt    (existing)
    generateImageStabilityRecolor.txt    (existing)

  -- root (unchanged, not user-selectable) --
  categorizeImage.txt
  trimTitlePrompt.txt
  increaseTitlePrompt.txt
```

Note: `generateImageFromProfessional` (currently has no `.txt` extension) is renamed to `generateImageFromProfessional.txt` as part of this work. All backend references are updated accordingly.

---

## 2. Default Prompt Selections Per Slot

| Slot | localStorage key | Default filename |
|---|---|---|
| Title | `axisPrompt_title` | `generateTitlePrompt.txt` |
| Description | `axisPrompt_description` | `generateDescriptionPrompt.txt` |
| Image - Real World | `axisPrompt_image_real_world` | `generateImageFromWorld.txt` |
| Image - Professional | `axisPrompt_image_professional` | `generateImageFromProfessional.txt` |
| Image - Angle Variant | `axisPrompt_image_angle_variant` | `generateImageAngleVariant.txt` |
| Image - Experimental | `axisPrompt_image_experimental` | `experimental.txt` |

These defaults exactly preserve the current backend behavior. A user who never touches the settings gets identical output to today.

---

## 3. Backend API

### `GET /api/prompts/<type>`

Lists all `.txt` filenames in `prompts/<type>/` (type = `title` | `description` | `image`).

Response:
```json
{ "prompts": ["generateImageFromWorld.txt", "generateImageFromProfessional.txt", ...] }
```

Files are returned in alphabetical order.

### `POST /api/prompts/<type>`

Creates a new prompt file in `prompts/<type>/`.

Request body:
```json
{ "name": "myCustomPrompt.txt", "content": "You are an expert..." }
```

- If `name` does not end in `.txt`, append it automatically.
- Reject names containing path separators (`/`, `\`, `..`).
- Return `400` if a file with that name already exists.

Response:
```json
{ "name": "myCustomPrompt.txt" }
```

---

## 4. Wiring Selections into Generation Calls

### Text generation

`POST /api/generate-text` gains two optional fields:
- `title_prompt` -- filename in `prompts/title/`. Defaults to `generateTitlePrompt.txt`.
- `description_prompt` -- filename in `prompts/description/`. Defaults to `generateDescriptionPrompt.txt`.

`create_text` and `create_text_stream` both gain two new optional parameters: `title_prompt=None` and `description_prompt=None`. The `_load_prompt()` helper already accepts a path -- when these params are provided, the path is constructed as `prompts/title/<title_prompt>` or `prompts/description/<description_prompt>`; when None, the existing defaults are used.

`POST /api/create-listing` also forwards these two fields into the internal text generation call.

### Image generation

`POST /api/generate-images` gains three optional fields:
- `image_prompt_real_world` -- filename in `prompts/image/`. Defaults to `generateImageFromWorld.txt`.
- `image_prompt_professional` -- filename in `prompts/image/`. Defaults to `generateImageFromProfessional.txt`.
- `image_prompt_angle_variant` -- filename in `prompts/image/`. Defaults to `generateImageAngleVariant.txt`.

`POST /api/regenerate-images` gains one optional field:
- `image_prompt_experimental` -- filename in `prompts/image/`. Defaults to `experimental.txt`.

`POST /api/create-listing` forwards all 4 image prompt fields into the internal image generation call.

In `app.py`, the per-ImageType prompt path lookup switches from the hardcoded map to using the incoming filename. The path is constructed as `prompts/image/<filename>`. The Bedrock stability model overrides (control-structure, search-recolor) remain hardcoded and are not exposed as user-selectable.

---

## 5. Frontend -- Settings Tab UI

A new **"Prompt Selection"** section is added to the Settings tab, below "AI Model Selection."

### Structure

```
Prompt Selection
  Title
    [dropdown: generateTitlePrompt.txt v]  [+ Add Prompt]

  Description
    [dropdown: generateDescriptionPrompt.txt v]  [+ Add Prompt]

  Image
    Real World     [dropdown: generateImageFromWorld.txt v]     [+ Add Prompt]
    Professional   [dropdown: generateImageFromProfessional.txt v]  [+ Add Prompt]
    Angle Variant  [dropdown: generateImageAngleVariant.txt v]   [+ Add Prompt]
    Experimental   [dropdown: experimental.txt v]               [+ Add Prompt]
```

Each dropdown is populated from `GET /api/prompts/<type>` (title, description, or image). All image type dropdowns share the same list from `GET /api/prompts/image`. A prompt added via any image `+ Add Prompt` button becomes available in all 4 image type dropdowns immediately.

Prompt lists are fetched once on Settings tab activation (same pattern as `textModelOptions`). Each list is stored in its own state variable: `titlePromptOptions`, `descriptionPromptOptions`, `imagePromptOptions`.

### Add Prompt Modal

Triggered by any `+ Add Prompt` button. The modal tracks which type it was opened for.

Fields:
- **Name** -- text input. `.txt` extension shown as static suffix if not already typed. Required.
- **Content** -- textarea, ~10 rows. Required.

Buttons:
- **Save** -- calls `POST /api/prompts/<type>`, then refreshes the relevant options list and auto-selects the new prompt in the slot that opened the modal. Closes modal on success.
- **Cancel** -- closes modal, discards input.

Error state: inline error message under the Name field if the API returns 400 (duplicate name).

### State

All selections initialized from localStorage on mount, falling back to the defaults in the table in section 2.

```
titlePrompt          (localStorage: axisPrompt_title)
descriptionPrompt    (localStorage: axisPrompt_description)
imagePromptRealWorld (localStorage: axisPrompt_image_real_world)
imagePromptProfessional (localStorage: axisPrompt_image_professional)
imagePromptAngleVariant (localStorage: axisPrompt_image_angle_variant)
imagePromptExperimental (localStorage: axisPrompt_image_experimental)

titlePromptOptions        []
descriptionPromptOptions  []
imagePromptOptions        []

promptModalOpen    bool
promptModalType    "title" | "description" | "image"
promptModalSlot    "real_world" | "professional" | "angle_variant" | "experimental" | null (for title/description)
promptModalName    string
promptModalContent string
promptModalError   string
```

### Sending selections to the backend

All 6 selection state values are included in the relevant API call bodies:
- `generate-text`: `title_prompt`, `description_prompt`
- `generate-images`: `image_prompt_real_world`, `image_prompt_professional`, `image_prompt_angle_variant`
- `regenerate-images`: `image_prompt_experimental`
- `create-listing`: all 6

---

## 6. What Does Not Change

- `categorizeImage.txt`, `trimTitlePrompt.txt`, `increaseTitlePrompt.txt` -- stay in root, not exposed.
- Bedrock stability model prompt overrides -- stay hardcoded, not exposed.
- The `prompt_modifier` / `custom_prompt` chat-bar flow -- unchanged.
- All other settings, state, and API contracts -- unchanged.
