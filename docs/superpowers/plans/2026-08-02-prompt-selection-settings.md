# Prompt Selection Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Settings section where users can choose and create prompt files for title, description, and each of the 4 image generation types, organized into typed subfolders on disk with selections persisted in localStorage.

**Architecture:** Prompts are reorganized into `prompts/title/`, `prompts/description/`, and `prompts/image/` subfolders. Two new Flask endpoints list and create prompt files. Frontend state mirrors the `textModel` pattern: lazy localStorage init, useEffect persistence, fetch on mount + settings-tab focus. Selections are passed as optional fields on existing generation API calls; backend resolves the full path and falls back to current defaults when omitted.

**Tech Stack:** Python/Flask (backend), React + Tailwind v4 (frontend), localStorage (persistence)

---

## File Map

| File | Action | What changes |
|---|---|---|
| `prompts/title/generateTitlePrompt.txt` | Create (move) | Moved from `prompts/` root |
| `prompts/description/generateDescriptionPrompt.txt` | Create (move) | Moved from `prompts/` root |
| `prompts/image/generateImageFromWorld.txt` | Create (move) | Moved from `prompts/` root |
| `prompts/image/generateImageFromProfessional.txt` | Create (rename+move) | Was extensionless in root |
| `prompts/image/generateImageAngleVariant.txt` | Create (move) | Moved from `prompts/` root |
| `prompts/image/experimental.txt` | Create (move) | Moved from `prompts/` root |
| `prompts/image/generateImageStabilityControl.txt` | Create (move) | Moved from `prompts/` root |
| `prompts/image/generateImageStabilityRecolor.txt` | Create (move) | Moved from `prompts/` root |
| `backend/copyScripts/create_text.py` | Modify | `_load_prompt` gains `comp_titles` param; `create_text` + `create_text_stream` gain `title_prompt`, `description_prompt` params |
| `backend/copyScripts/create_image.py` | Modify | Prompt path lookup uses passed-in filename instead of hardcoded map; Stability overrides updated to new subfolder paths |
| `app.py` | Modify | Two new routes (`GET/POST /api/prompts/<type>`); `generate-text`, `generate-images`, `regenerate-images`, `create-listing` routes forward prompt filenames |
| `frontend/src/App.jsx` | Modify | 6 new prompt-selection state vars + localStorage persistence; `imagePromptOptions`, `titlePromptOptions`, `descriptionPromptOptions` fetch state; new Settings section; Add Prompt modal; API calls updated |

---

## Task 1: Reorganize prompt files into subfolders

**Files:**
- Create: `prompts/title/`, `prompts/description/`, `prompts/image/` (directories)
- Move: all listed prompt files into their typed subfolder

- [ ] **Step 1: Create subfolders and move files**

Run from the project root:

```bash
mkdir -p prompts/title prompts/description prompts/image

# Title
cp "prompts/generateTitlePrompt.txt" "prompts/title/generateTitlePrompt.txt"

# Description
cp "prompts/generateDescriptionPrompt.txt" "prompts/description/generateDescriptionPrompt.txt"

# Image (rename extensionless file while moving)
cp "prompts/generateImageFromProfessional" "prompts/image/generateImageFromProfessional.txt"
cp "prompts/generateImageFromWorld.txt" "prompts/image/generateImageFromWorld.txt"
cp "prompts/generateImageAngleVariant.txt" "prompts/image/generateImageAngleVariant.txt"
cp "prompts/experimental.txt" "prompts/image/experimental.txt"
cp "prompts/generateImageStabilityControl.txt" "prompts/image/generateImageStabilityControl.txt"
cp "prompts/generateImageStabilityRecolor.txt" "prompts/image/generateImageStabilityRecolor.txt"
```

- [ ] **Step 2: Delete the originals from the root**

```bash
rm prompts/generateTitlePrompt.txt
rm prompts/generateDescriptionPrompt.txt
rm prompts/generateImageFromProfessional
rm prompts/generateImageFromWorld.txt
rm prompts/generateImageAngleVariant.txt
rm prompts/experimental.txt
rm prompts/generateImageStabilityControl.txt
rm prompts/generateImageStabilityRecolor.txt
```

- [ ] **Step 3: Verify structure**

```bash
find prompts -type f | sort
```

Expected output:
```
prompts/categorizeImage.txt
prompts/description/generateDescriptionPrompt.txt
prompts/image/experimental.txt
prompts/image/generateImageAngleVariant.txt
prompts/image/generateImageFromProfessional.txt
prompts/image/generateImageFromWorld.txt
prompts/image/generateImageStabilityControl.txt
prompts/image/generateImageStabilityRecolor.txt
prompts/title/generateTitlePrompt.txt
prompts/increaseTitlePrompt.txt
prompts/trimTitlePrompt.txt
```

- [ ] **Step 4: Commit**

```bash
git add prompts/
git commit -m "refactor: reorganize prompt files into title/description/image subfolders"
```

---

## Task 2: Update `create_text.py` to use typed subfolders and new params

**Files:**
- Modify: `backend/copyScripts/create_text.py`

The updated title and description prompts now include a `{comp_titles}` placeholder. `_load_prompt` must accept and pass through a `comp_titles` argument (defaulting to empty string) or the `.format()` call raises a `KeyError`.

- [ ] **Step 1: Replace `_load_prompt` and update `create_text` + `create_text_stream`**

Replace the entire contents of `backend/copyScripts/create_text.py` with:

```python
"""
Create Text Module

Title and description are generated via parallel LLM calls.
"""

import json
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


def _load_prompt(path, original_title, original_description, comp_titles=""):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().format(
            original_title=original_title,
            original_description=original_description,
            comp_titles=comp_titles,
        )


def create_text(
    old_title,
    old_description,
    model="deepseek/deepseek-v4-flash",
    title_prompt=None,
    description_prompt=None,
    comp_titles="",
):
    """
    Generate optimized listing content using two parallel LLM calls.

    Args:
        title_prompt: filename inside prompts/title/. Defaults to generateTitlePrompt.txt.
        description_prompt: filename inside prompts/description/. Defaults to generateDescriptionPrompt.txt.
        comp_titles: optional string of comparable listing titles passed into the prompt.

    Returns:
        dict: {"edited_title": "...", "edited_description": "..."} or None on failure
    """
    from backend.ebay_cli import call_text_llm

    title_file = title_prompt or "generateTitlePrompt.txt"
    desc_file = description_prompt or "generateDescriptionPrompt.txt"

    try:
        title_prompt_text = _load_prompt(
            f"prompts/title/{title_file}", old_title, old_description, comp_titles
        )
        desc_prompt_text = _load_prompt(
            f"prompts/description/{desc_file}", old_title, old_description, comp_titles
        )
    except Exception as e:
        print(f"❌ Error loading prompt templates: {e}")
        return None

    results = {}

    def call_title():
        response = call_text_llm(title_prompt_text, model=model)
        if response:
            try:
                return "title", json.loads(response)
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing title LLM response: {e}")
        return "title", None

    def call_description():
        response = call_text_llm(desc_prompt_text, model=model)
        if response:
            try:
                return "description", json.loads(response)
            except json.JSONDecodeError as e:
                print(f"❌ Error parsing description LLM response: {e}")
        return "description", None

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(call_title), executor.submit(call_description)]
        for future in as_completed(futures):
            key, data = future.result()
            if data:
                results.update(data)

    if "edited_title" not in results or "edited_description" not in results:
        print("❌ Failed to get complete response from text LLM")
        return None

    print("\n🎯 Optimized eBay Listing:")
    print("=" * 50)
    print(f"📝 Optimized Title ({len(results['edited_title'])} chars):")
    print(f"   {results['edited_title']}")
    print(f"\n📄 Optimized Description:")
    print(f"   {results['edited_description']}")
    print("=" * 50)

    return results


def _find_closing_quote(s):
    """Return index of first unescaped double-quote in s, or -1."""
    i = 0
    while i < len(s):
        if s[i] == '\\':
            i += 2
            continue
        if s[i] == '"':
            return i
        i += 1
    return -1


def _stream_field(prompt, field, model, out_queue):
    """
    Run a streaming LLM call for a single-field JSON response and push events onto out_queue.

    Pushes: {"type": "token", "field": field, "delta": "..."} events, then
            {"type": "_done", "field": field, "data": {field: "..."}}
    On error pushes: {"type": "error", "error": "..."}
    """
    import re as _re
    from backend.ebay_cli import call_text_llm_stream

    accumulated = ""
    marker = f'"{field}"'
    state = "before_field"

    for token in call_text_llm_stream(prompt, model):
        if token is None:
            out_queue.put({"type": "error", "error": f"LLM stream returned no content for {field}"})
            return

        accumulated += token

        if state == "before_field":
            if marker in accumulated:
                marker_end = accumulated.index(marker) + len(marker)
                rest = accumulated[marker_end:]
                colon_pos = rest.find(":")
                if colon_pos != -1:
                    after_colon = rest[colon_pos + 1:].lstrip()
                    if after_colon.startswith('"'):
                        content = after_colon[1:]
                        close_pos = _find_closing_quote(content)
                        if close_pos != -1:
                            content = content[:close_pos]
                            if content:
                                out_queue.put({"type": "token", "field": field, "delta": content})
                            state = "done"
                        else:
                            if content:
                                out_queue.put({"type": "token", "field": field, "delta": content})
                            state = "in_field"

        elif state == "in_field":
            if '"' in token:
                parts = token.split('"', 1)
                if parts[0]:
                    out_queue.put({"type": "token", "field": field, "delta": parts[0]})
                state = "done"
            else:
                out_queue.put({"type": "token", "field": field, "delta": token})

    # Parse final result
    result = None
    try:
        clean = accumulated.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean.strip())
    except json.JSONDecodeError:
        pass

    if result is None:
        m = _re.search(r'\{[\s\S]*\}', accumulated)
        if m:
            try:
                result = json.loads(m.group(0))
            except json.JSONDecodeError:
                pass

    if result is not None:
        out_queue.put({"type": "_done", "field": field, "data": result})
    else:
        out_queue.put({"type": "error", "error": f"Failed to parse {field} JSON response: {accumulated[:200]}"})


_SENTINEL = object()


def create_text_stream(
    old_title,
    old_description,
    model="deepseek/deepseek-v4-flash",
    title_prompt=None,
    description_prompt=None,
    comp_titles="",
):
    """
    Stream optimized title/description tokens from two parallel LLM calls.

    Args:
        title_prompt: filename inside prompts/title/. Defaults to generateTitlePrompt.txt.
        description_prompt: filename inside prompts/description/. Defaults to generateDescriptionPrompt.txt.
        comp_titles: optional string of comparable listing titles passed into the prompt.

    Yields dicts:
      {"type": "token", "field": "title",       "delta": "<chars>"}
      {"type": "token", "field": "description", "delta": "<chars>"}
      {"type": "result", "data": {"edited_title": "...", "edited_description": "..."}}
      {"type": "error",  "error": "<message>"}
    """
    title_file = title_prompt or "generateTitlePrompt.txt"
    desc_file = description_prompt or "generateDescriptionPrompt.txt"

    try:
        title_prompt_text = _load_prompt(
            f"prompts/title/{title_file}", old_title, old_description, comp_titles
        )
        desc_prompt_text = _load_prompt(
            f"prompts/description/{desc_file}", old_title, old_description, comp_titles
        )
    except Exception as e:
        yield {"type": "error", "error": f"Failed to load prompts: {e}"}
        return

    event_queue = queue.Queue()
    done_count = [0]
    lock = threading.Lock()

    def run_title():
        _stream_field(title_prompt_text, "edited_title", model, event_queue)
        with lock:
            done_count[0] += 1
        if done_count[0] == 2:
            event_queue.put(_SENTINEL)

    def run_description():
        _stream_field(desc_prompt_text, "edited_description", model, event_queue)
        with lock:
            done_count[0] += 1
        if done_count[0] == 2:
            event_queue.put(_SENTINEL)

    threading.Thread(target=run_title, daemon=True).start()
    threading.Thread(target=run_description, daemon=True).start()

    combined_result = {}

    while True:
        item = event_queue.get()
        if item is _SENTINEL:
            break
        if item.get("type") == "_done":
            combined_result.update(item["data"])
        else:
            yield item

    if "edited_title" in combined_result and "edited_description" in combined_result:
        yield {"type": "result", "data": combined_result}
    else:
        missing = [f for f in ("edited_title", "edited_description") if f not in combined_result]
        yield {"type": "error", "error": f"Missing fields from LLM responses: {missing}"}
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
python -c "from backend.copyScripts.create_text import create_text, create_text_stream; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/copyScripts/create_text.py
git commit -m "feat: create_text uses typed prompt subfolders, supports custom prompt filenames and comp_titles"
```

---

## Task 3: Update `create_image.py` to use typed subfolder and accept a prompt filename

**Files:**
- Modify: `backend/copyScripts/create_image.py` (lines ~565-638)

- [ ] **Step 1: Update the Bedrock stability prompt paths and the ImageType prompt map**

In `generate_image_from_urls`, replace the two blocks that build `prompt_file_path`.

**Stability block** (currently lines ~571-580) -- change the three `prompt_file_path` assignments:

Old:
```python
            if "control-structure" in model:
                prompt_file_path = script_dir / "prompts" / "generateImageStabilityControl.txt"
            elif "search-recolor" in model:
                prompt_file_path = script_dir / "prompts" / "generateImageStabilityRecolor.txt"
            else:
                prompt_file_path = script_dir / "prompts" / "generateImageStabilityControl.txt"
```

New:
```python
            if "control-structure" in model:
                prompt_file_path = script_dir / "prompts" / "image" / "generateImageStabilityControl.txt"
            elif "search-recolor" in model:
                prompt_file_path = script_dir / "prompts" / "image" / "generateImageStabilityRecolor.txt"
            else:
                prompt_file_path = script_dir / "prompts" / "image" / "generateImageStabilityControl.txt"
```

**ImageType map block** (currently lines ~617-624) -- replace with a version that accepts an optional `prompt_filename` parameter. First update the function signature to add the new parameter:

Old signature:
```python
def generate_image_from_urls(
    image_urls,
    image_type,
    custom_prompt=None,
    prompt_modifier=None,
    extra_instructions=None,
    model="sourceful/riverflow-v2-fast",
):
```

New signature:
```python
def generate_image_from_urls(
    image_urls,
    image_type,
    custom_prompt=None,
    prompt_modifier=None,
    extra_instructions=None,
    model="sourceful/riverflow-v2-fast",
    prompt_filename=None,
):
```

Then replace the ImageType prompt map block:

Old:
```python
        if image_type == ImageType.PROFESSIONAL:
            prompt_file_path = script_dir / "prompts" / "generateImageFromProfessional"
        elif image_type == ImageType.REAL_WORLD:
            prompt_file_path = script_dir / "prompts" / "generateImageFromWorld.txt"
        elif image_type == ImageType.ANGLE_VARIANT:
            prompt_file_path = script_dir / "prompts" / "generateImageAngleVariant.txt"
        else:  # ImageType.EXPERIMENTAL
            prompt_file_path = script_dir / "prompts" / "experimental.txt"
```

New:
```python
        _DEFAULT_IMAGE_PROMPTS = {
            ImageType.PROFESSIONAL: "generateImageFromProfessional.txt",
            ImageType.REAL_WORLD: "generateImageFromWorld.txt",
            ImageType.ANGLE_VARIANT: "generateImageAngleVariant.txt",
            ImageType.EXPERIMENTAL: "experimental.txt",
        }
        filename = prompt_filename or _DEFAULT_IMAGE_PROMPTS.get(image_type, "generateImageFromWorld.txt")
        prompt_file_path = script_dir / "prompts" / "image" / filename
```

- [ ] **Step 2: Verify the module imports cleanly**

```bash
python -c "from backend.copyScripts.create_image import generate_image_from_urls, ImageType; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/copyScripts/create_image.py
git commit -m "feat: image prompts use typed subfolder, generate_image_from_urls accepts prompt_filename"
```

---

## Task 4: Update `generate_image_with_delay` in `app.py` to forward `prompt_filename`

**Files:**
- Modify: `app.py` (lines ~303-347)

- [ ] **Step 1: Add `prompt_filename` param to `generate_image_with_delay` and forward it**

Old signature (line 303):
```python
def generate_image_with_delay(
    photo_url,
    image_type,
    index,
    delay_ms=500,
    task_id=None,
    prompt_modifier=None,
    extra_instructions=None,
    image_model=None,
):
```

New:
```python
def generate_image_with_delay(
    photo_url,
    image_type,
    index,
    delay_ms=500,
    task_id=None,
    prompt_modifier=None,
    extra_instructions=None,
    image_model=None,
    prompt_filename=None,
):
```

Old call to `generate_image_from_urls` inside `generate_image_with_delay` (lines ~341-347):
```python
        result = generate_image_from_urls(
            [photo_url],
            image_type,
            prompt_modifier=prompt_modifier,
            extra_instructions=extra_instructions,
            model=image_model or DEFAULT_IMAGE_MODEL,
        )
```

New:
```python
        result = generate_image_from_urls(
            [photo_url],
            image_type,
            prompt_modifier=prompt_modifier,
            extra_instructions=extra_instructions,
            model=image_model or DEFAULT_IMAGE_MODEL,
            prompt_filename=prompt_filename,
        )
```

- [ ] **Step 2: Commit**

```bash
git add app.py
git commit -m "feat: generate_image_with_delay forwards prompt_filename to generate_image_from_urls"
```

---

## Task 5: Add `/api/prompts/<type>` GET and POST routes to `app.py`

**Files:**
- Modify: `app.py`

Add the two new routes anywhere after the existing imports, before the first route definition (or grouped with settings/config routes).

- [ ] **Step 1: Add the routes**

Insert the following into `app.py` (after the imports, before or near the first `@app.route`):

```python
PROMPT_TYPES = {"title", "description", "image"}

@app.route('/api/prompts/<prompt_type>', methods=['GET'])
def list_prompts(prompt_type):
    if prompt_type not in PROMPT_TYPES:
        return jsonify({"error": f"Invalid prompt type: {prompt_type}"}), 400
    folder = os.path.join("prompts", prompt_type)
    try:
        files = sorted(
            f for f in os.listdir(folder)
            if os.path.isfile(os.path.join(folder, f)) and f.endswith(".txt")
        )
        return jsonify({"prompts": files}), 200
    except FileNotFoundError:
        return jsonify({"prompts": []}), 200


@app.route('/api/prompts/<prompt_type>', methods=['POST'])
def create_prompt(prompt_type):
    if prompt_type not in PROMPT_TYPES:
        return jsonify({"error": f"Invalid prompt type: {prompt_type}"}), 400
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body must be JSON"}), 400
    name = data.get("name", "").strip()
    content = data.get("content", "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400
    if not content:
        return jsonify({"error": "content is required"}), 400
    if not name.endswith(".txt"):
        name = name + ".txt"
    if any(c in name for c in ("/", "\\", "..")):
        return jsonify({"error": "Invalid filename"}), 400
    folder = os.path.join("prompts", prompt_type)
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, name)
    if os.path.exists(file_path):
        return jsonify({"error": f"Prompt '{name}' already exists"}), 400
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return jsonify({"name": name}), 201
```

- [ ] **Step 2: Verify routes load**

```bash
python -c "import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add GET/POST /api/prompts/<type> routes for listing and creating prompt files"
```

---

## Task 6: Wire prompt selections into existing generation routes in `app.py`

**Files:**
- Modify: `app.py` (generate-text, generate-images, regenerate-images, create-listing routes)

- [ ] **Step 1: Update `/api/generate-text` to read and forward prompt filenames**

In the `generate()` closure of the `/api/generate-text` route (around line 125-163), add after the existing `text_model` line:

```python
        title_prompt = data.get("title_prompt") or None
        description_prompt = data.get("description_prompt") or None
```

Then update the `create_text_stream` call (line 142):

Old:
```python
            for event in create_text_stream(title, description, model=text_model):
```

New:
```python
            for event in create_text_stream(
                title, description, model=text_model,
                title_prompt=title_prompt,
                description_prompt=description_prompt,
            ):
```

Also update the `_nudge_title_length` call path -- no changes needed there (nudge uses its own prompts).

- [ ] **Step 2: Update `/api/generate-images` to read and forward per-type prompt filenames**

In the `generate_images` route, after the existing `image_model` line, add:

```python
        image_prompt_real_world = data.get("image_prompt_real_world") or None
        image_prompt_professional = data.get("image_prompt_professional") or None
        image_prompt_angle_variant = data.get("image_prompt_angle_variant") or None
```

Build a per-type lookup dict and pass it through to `generate_image_with_delay`. Add this dict right before the `tasks_to_generate` loop:

```python
        image_prompt_map = {
            ImageType.REAL_WORLD: image_prompt_real_world,
            ImageType.PROFESSIONAL: image_prompt_professional,
            ImageType.ANGLE_VARIANT: image_prompt_angle_variant,
        }
```

Inside `run_generation()`, find the `executor.submit(generate_image_with_delay, ...)` call and add `prompt_filename=image_prompt_map.get(image_type)`:

Old:
```python
                        future = executor.submit(
                            generate_image_with_delay,
                            photo_url, image_type, idx, delay_ms=500, task_id=task_id,
                            prompt_modifier=angle if angle else (prompt_modifier or None),
                            extra_instructions=prompt_modifier if angle else None,
                            image_model=image_model,
                        )
```

New:
```python
                        future = executor.submit(
                            generate_image_with_delay,
                            photo_url, image_type, idx, delay_ms=500, task_id=task_id,
                            prompt_modifier=angle if angle else (prompt_modifier or None),
                            extra_instructions=prompt_modifier if angle else None,
                            image_model=image_model,
                            prompt_filename=image_prompt_map.get(image_type),
                        )
```

Note: `image_prompt_map` must be captured in the `run_generation` closure. Since `run_generation` is a nested function defined in the same scope, it already captures all local variables -- no extra change needed.

- [ ] **Step 3: Update `/api/regenerate-images` to read and forward the experimental prompt filename**

In the `regenerate_images` route, after the existing `image_model` line:

```python
        image_prompt_experimental = data.get("image_prompt_experimental") or None
```

Then find the `generate_image_from_urls` call inside the loop and add `prompt_filename=image_prompt_experimental`:

Old:
```python
                result = generate_image_from_urls(
                    [image_url],
                    ImageType.EXPERIMENTAL,
                    custom_prompt=prompt.strip(),
                    model=image_model,
                )
```

New:
```python
                result = generate_image_from_urls(
                    [image_url],
                    ImageType.EXPERIMENTAL,
                    custom_prompt=prompt.strip(),
                    model=image_model,
                    prompt_filename=image_prompt_experimental,
                )
```

Note: `custom_prompt` is set (user typed a regeneration prompt), so `prompt_filename` is effectively ignored in the current `generate_image_from_urls` logic since `custom_prompt` takes precedence. The param is wired for completeness and future use.

- [ ] **Step 4: Update `/api/create-listing` to read and forward all prompt filenames**

In the `create_listing` route, after the existing `text_model` line, add:

```python
            title_prompt = data.get("title_prompt") or None
            description_prompt = data.get("description_prompt") or None
            image_prompt_real_world = data.get("image_prompt_real_world") or None
            image_prompt_professional = data.get("image_prompt_professional") or None
            image_prompt_angle_variant = data.get("image_prompt_angle_variant") or None
            image_prompt_experimental = data.get("image_prompt_experimental") or None
```

Then update the `create_text` call (line ~744):

Old:
```python
                optimized_content = create_text(old_title, old_description, model=text_model)
```

New:
```python
                optimized_content = create_text(
                    old_title, old_description, model=text_model,
                    title_prompt=title_prompt,
                    description_prompt=description_prompt,
                )
```

The `create-listing` route does not call `generate_image_from_urls` directly (images arrive pre-generated), so no image prompt wiring is needed here.

- [ ] **Step 5: Verify app starts**

```bash
python -c "import app; print('OK')"
```

Expected: `OK`

- [ ] **Step 6: Commit**

```bash
git add app.py
git commit -m "feat: generation routes accept and forward prompt filename selections"
```

---

## Task 7: Add frontend state, localStorage persistence, and prompt list fetching

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add the 6 prompt-selection state vars after the `classifierModel` state block (~line 313)**

```jsx
  const [titlePrompt, setTitlePrompt] = useState(() => {
    try { return localStorage.getItem("axisPrompt_title") || "generateTitlePrompt.txt"; }
    catch { return "generateTitlePrompt.txt"; }
  });
  const [descriptionPrompt, setDescriptionPrompt] = useState(() => {
    try { return localStorage.getItem("axisPrompt_description") || "generateDescriptionPrompt.txt"; }
    catch { return "generateDescriptionPrompt.txt"; }
  });
  const [imagePromptRealWorld, setImagePromptRealWorld] = useState(() => {
    try { return localStorage.getItem("axisPrompt_image_real_world") || "generateImageFromWorld.txt"; }
    catch { return "generateImageFromWorld.txt"; }
  });
  const [imagePromptProfessional, setImagePromptProfessional] = useState(() => {
    try { return localStorage.getItem("axisPrompt_image_professional") || "generateImageFromProfessional.txt"; }
    catch { return "generateImageFromProfessional.txt"; }
  });
  const [imagePromptAngleVariant, setImagePromptAngleVariant] = useState(() => {
    try { return localStorage.getItem("axisPrompt_image_angle_variant") || "generateImageAngleVariant.txt"; }
    catch { return "generateImageAngleVariant.txt"; }
  });
  const [imagePromptExperimental, setImagePromptExperimental] = useState(() => {
    try { return localStorage.getItem("axisPrompt_image_experimental") || "experimental.txt"; }
    catch { return "experimental.txt"; }
  });
```

- [ ] **Step 2: Add the 3 prompt options list state vars (after the state vars above)**

```jsx
  const [titlePromptOptions, setTitlePromptOptions] = useState([]);
  const [descriptionPromptOptions, setDescriptionPromptOptions] = useState([]);
  const [imagePromptOptions, setImagePromptOptions] = useState([]);
```

- [ ] **Step 3: Add Add-Prompt modal state vars (after the options state vars)**

```jsx
  const [promptModalOpen, setPromptModalOpen] = useState(false);
  const [promptModalType, setPromptModalType] = useState("title");
  const [promptModalSlot, setPromptModalSlot] = useState(null);
  const [promptModalName, setPromptModalName] = useState("");
  const [promptModalContent, setPromptModalContent] = useState("");
  const [promptModalError, setPromptModalError] = useState("");
  const [promptModalSaving, setPromptModalSaving] = useState(false);
```

- [ ] **Step 4: Add localStorage persistence useEffects for all 6 selections (near the existing `textModel` useEffect, ~line 478)**

```jsx
  useEffect(() => { try { localStorage.setItem("axisPrompt_title", titlePrompt); } catch {} }, [titlePrompt]);
  useEffect(() => { try { localStorage.setItem("axisPrompt_description", descriptionPrompt); } catch {} }, [descriptionPrompt]);
  useEffect(() => { try { localStorage.setItem("axisPrompt_image_real_world", imagePromptRealWorld); } catch {} }, [imagePromptRealWorld]);
  useEffect(() => { try { localStorage.setItem("axisPrompt_image_professional", imagePromptProfessional); } catch {} }, [imagePromptProfessional]);
  useEffect(() => { try { localStorage.setItem("axisPrompt_image_angle_variant", imagePromptAngleVariant); } catch {} }, [imagePromptAngleVariant]);
  useEffect(() => { try { localStorage.setItem("axisPrompt_image_experimental", imagePromptExperimental); } catch {} }, [imagePromptExperimental]);
```

- [ ] **Step 5: Add `fetchPromptOptions` callback and mount/settings-tab useEffects (near `fetchTextModels`, ~line 2407)**

```jsx
  const fetchPromptOptions = useCallback(async () => {
    try {
      const [titleRes, descRes, imgRes] = await Promise.all([
        fetch("/api/prompts/title"),
        fetch("/api/prompts/description"),
        fetch("/api/prompts/image"),
      ]);
      const [titleData, descData, imgData] = await Promise.all([
        titleRes.json(), descRes.json(), imgRes.json(),
      ]);
      if (Array.isArray(titleData?.prompts)) setTitlePromptOptions(titleData.prompts);
      if (Array.isArray(descData?.prompts)) setDescriptionPromptOptions(descData.prompts);
      if (Array.isArray(imgData?.prompts)) setImagePromptOptions(imgData.prompts);
    } catch {
      // leave existing options unchanged on fetch failure
    }
  }, []);

  useEffect(() => { fetchPromptOptions(); }, [fetchPromptOptions]);

  useEffect(() => {
    if (activeTab === "settings") fetchPromptOptions();
  }, [activeTab, fetchPromptOptions]);
```

- [ ] **Step 6: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add prompt selection state, localStorage persistence, and prompt options fetching"
```

---

## Task 8: Wire prompt selections into frontend API call bodies

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add to the `POST /api/generate-text` call body**

Find the fetch to `/api/generate-text` (line ~1109). Add to the JSON body:

```js
        title_prompt: titlePrompt,
        description_prompt: descriptionPrompt,
```

- [ ] **Step 2: Add to the `POST /api/generate-images` call body**

Find the fetch to `/api/generate-images` (line ~1376). Add to the JSON body:

```js
        image_prompt_real_world: imagePromptRealWorld,
        image_prompt_professional: imagePromptProfessional,
        image_prompt_angle_variant: imagePromptAngleVariant,
```

- [ ] **Step 3: Add to the `POST /api/regenerate-images` call body**

Find the fetch(es) to `/api/regenerate-images` (lines ~1653 and ~1793). Add to each JSON body:

```js
        image_prompt_experimental: imagePromptExperimental,
```

- [ ] **Step 4: Add to the `POST /api/create-listing` call body**

Find the fetch to `/api/create-listing` (line ~1882). Add to the JSON body:

```js
        title_prompt: titlePrompt,
        description_prompt: descriptionPrompt,
        image_prompt_real_world: imagePromptRealWorld,
        image_prompt_professional: imagePromptProfessional,
        image_prompt_angle_variant: imagePromptAngleVariant,
        image_prompt_experimental: imagePromptExperimental,
```

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: API calls include prompt filename selections"
```

---

## Task 9: Add Prompt Selection UI section to Settings tab

**Files:**
- Modify: `frontend/src/App.jsx`

- [ ] **Step 1: Add the `openPromptModal` and `handleSavePrompt` helpers near the other settings handlers**

```jsx
  const openPromptModal = useCallback((type, slot = null) => {
    setPromptModalType(type);
    setPromptModalSlot(slot);
    setPromptModalName("");
    setPromptModalContent("");
    setPromptModalError("");
    setPromptModalSaving(false);
    setPromptModalOpen(true);
  }, []);

  const handleSavePrompt = useCallback(async () => {
    const name = promptModalName.trim();
    const content = promptModalContent.trim();
    if (!name) { setPromptModalError("Name is required."); return; }
    if (!content) { setPromptModalError("Content is required."); return; }
    setPromptModalSaving(true);
    setPromptModalError("");
    try {
      const res = await fetch(`/api/prompts/${promptModalType}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, content }),
      });
      const data = await res.json();
      if (!res.ok) { setPromptModalError(data.error || "Failed to save."); setPromptModalSaving(false); return; }
      await fetchPromptOptions();
      // Auto-select the new prompt in the relevant slot
      const filename = data.name;
      if (promptModalType === "title") setTitlePrompt(filename);
      else if (promptModalType === "description") setDescriptionPrompt(filename);
      else if (promptModalSlot === "real_world") setImagePromptRealWorld(filename);
      else if (promptModalSlot === "professional") setImagePromptProfessional(filename);
      else if (promptModalSlot === "angle_variant") setImagePromptAngleVariant(filename);
      else if (promptModalSlot === "experimental") setImagePromptExperimental(filename);
      setPromptModalOpen(false);
    } catch { setPromptModalError("Network error."); setPromptModalSaving(false); }
  }, [promptModalType, promptModalSlot, promptModalName, promptModalContent, fetchPromptOptions]);
```

- [ ] **Step 2: Add the Prompt Selection section in the Settings tab JSX, directly after the closing `</div>` of the "AI Model Selection" section (~line 3635)**

```jsx
              <div className="mb-5 rounded-xl border border-border-default bg-surface-muted p-5">
                <div className="mb-4">
                  <h3 className="m-0 text-lg font-semibold text-text-primary">
                    Prompt Selection
                  </h3>
                  <p className="mt-1 text-sm text-text-muted">
                    Choose which prompt file is used for each generation type. Use + Add Prompt to create new ones.
                  </p>
                </div>

                {/* Title */}
                <div className="mb-4">
                  <p className="mb-2 text-sm font-semibold text-text-primary">Title</p>
                  <div className="flex items-center gap-2">
                    <select
                      className="flex-1 rounded-lg border border-border-default bg-surface-panel px-3 py-2 text-sm font-medium text-text-primary focus:border-primary focus:outline-none"
                      value={titlePrompt}
                      onChange={(e) => setTitlePrompt(e.target.value)}
                    >
                      {titlePromptOptions.map((f) => (
                        <option key={f} value={f}>{f}</option>
                      ))}
                    </select>
                    <button
                      className="shrink-0 rounded-lg border border-border-default bg-surface-panel px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-muted"
                      onClick={() => openPromptModal("title")}
                    >
                      + Add Prompt
                    </button>
                  </div>
                </div>

                {/* Description */}
                <div className="mb-4">
                  <p className="mb-2 text-sm font-semibold text-text-primary">Description</p>
                  <div className="flex items-center gap-2">
                    <select
                      className="flex-1 rounded-lg border border-border-default bg-surface-panel px-3 py-2 text-sm font-medium text-text-primary focus:border-primary focus:outline-none"
                      value={descriptionPrompt}
                      onChange={(e) => setDescriptionPrompt(e.target.value)}
                    >
                      {descriptionPromptOptions.map((f) => (
                        <option key={f} value={f}>{f}</option>
                      ))}
                    </select>
                    <button
                      className="shrink-0 rounded-lg border border-border-default bg-surface-panel px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-muted"
                      onClick={() => openPromptModal("description")}
                    >
                      + Add Prompt
                    </button>
                  </div>
                </div>

                {/* Image */}
                <div>
                  <p className="mb-2 text-sm font-semibold text-text-primary">Image</p>
                  <div className="grid gap-3">
                    {[
                      { label: "Real World", slot: "real_world", value: imagePromptRealWorld, setter: setImagePromptRealWorld },
                      { label: "Professional", slot: "professional", value: imagePromptProfessional, setter: setImagePromptProfessional },
                      { label: "Angle Variant", slot: "angle_variant", value: imagePromptAngleVariant, setter: setImagePromptAngleVariant },
                      { label: "Experimental", slot: "experimental", value: imagePromptExperimental, setter: setImagePromptExperimental },
                    ].map(({ label, slot, value, setter }) => (
                      <div key={slot} className="flex items-center gap-2">
                        <span className="w-28 shrink-0 text-sm text-text-muted">{label}</span>
                        <select
                          className="flex-1 rounded-lg border border-border-default bg-surface-panel px-3 py-2 text-sm font-medium text-text-primary focus:border-primary focus:outline-none"
                          value={value}
                          onChange={(e) => setter(e.target.value)}
                        >
                          {imagePromptOptions.map((f) => (
                            <option key={f} value={f}>{f}</option>
                          ))}
                        </select>
                        <button
                          className="shrink-0 rounded-lg border border-border-default bg-surface-panel px-3 py-2 text-sm font-medium text-text-primary hover:bg-surface-muted"
                          onClick={() => openPromptModal("image", slot)}
                        >
                          + Add Prompt
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
```

- [ ] **Step 3: Add the Add Prompt modal JSX somewhere in the top-level return, alongside other modals**

```jsx
              {promptModalOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
                  <div className="w-full max-w-lg rounded-xl border border-border-default bg-surface-panel p-6 shadow-xl">
                    <h3 className="mb-4 text-lg font-semibold text-text-primary">
                      Add {promptModalType.charAt(0).toUpperCase() + promptModalType.slice(1)} Prompt
                    </h3>
                    <div className="mb-3">
                      <label className="mb-1 block text-sm font-semibold text-text-primary">Name</label>
                      <div className="flex items-center gap-1">
                        <input
                          className="flex-1 rounded-lg border border-border-default bg-surface-app px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none"
                          placeholder="myPrompt"
                          value={promptModalName}
                          onChange={(e) => setPromptModalName(e.target.value)}
                        />
                        <span className="text-sm text-text-muted">.txt</span>
                      </div>
                      {promptModalError && (
                        <p className="mt-1 text-xs text-red-500">{promptModalError}</p>
                      )}
                    </div>
                    <div className="mb-4">
                      <label className="mb-1 block text-sm font-semibold text-text-primary">Content</label>
                      <textarea
                        className="h-48 w-full rounded-lg border border-border-default bg-surface-app px-3 py-2 text-sm text-text-primary focus:border-primary focus:outline-none"
                        placeholder="Enter your prompt..."
                        value={promptModalContent}
                        onChange={(e) => setPromptModalContent(e.target.value)}
                      />
                    </div>
                    <div className="flex justify-end gap-2">
                      <button
                        className="rounded-lg border border-border-default bg-surface-panel px-4 py-2 text-sm font-medium text-text-primary hover:bg-surface-muted"
                        onClick={() => setPromptModalOpen(false)}
                        disabled={promptModalSaving}
                      >
                        Cancel
                      </button>
                      <button
                        className="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-white hover:opacity-90 disabled:opacity-50"
                        onClick={handleSavePrompt}
                        disabled={promptModalSaving}
                      >
                        {promptModalSaving ? "Saving..." : "Save"}
                      </button>
                    </div>
                  </div>
                </div>
              )}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/App.jsx
git commit -m "feat: add Prompt Selection settings section with dropdowns and Add Prompt modal"
```

---

## Task 10: Smoke test end-to-end

- [ ] **Step 1: Start the dev server**

```bash
npm run dev
```

- [ ] **Step 2: Open Settings tab and verify**

- All 3 prompt type sections appear below "AI Model Selection"
- Title and Description each show one dropdown (default file selected) and a "+ Add Prompt" button
- Image section shows 4 rows: Real World, Professional, Angle Variant, Experimental -- each with a dropdown and "+ Add Prompt" button
- All dropdowns are populated (not empty)

- [ ] **Step 3: Test Add Prompt**

- Click "+ Add Prompt" for Title
- Modal opens; type `testPrompt` in name field, type any content in textarea
- Click Save
- Dropdown refreshes and auto-selects `testPrompt.txt`
- Verify file was created: `ls prompts/title/`

- [ ] **Step 4: Test duplicate name rejection**

- Click "+ Add Prompt" for Title again, type `testPrompt`, click Save
- Expect inline error: "Prompt 'testPrompt.txt' already exists"

- [ ] **Step 5: Verify localStorage persistence**

- Select a different prompt in any slot
- Reload the page
- Verify the same prompt is still selected

- [ ] **Step 6: Final commit**

```bash
git add .
git commit -m "feat: prompt selection settings complete"
```
