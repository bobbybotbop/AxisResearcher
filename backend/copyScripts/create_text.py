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
