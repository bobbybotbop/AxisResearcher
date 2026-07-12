"""
Create Text Module

This module contains functions for creating optimized eBay listing text.
"""

import json


def create_text(old_title, old_description, model="deepseek/deepseek-v4-flash"):
    """
    Generate optimized listing content using LLM from original title and description.
    
    Args:
        old_title (str): Original listing title
        old_description (str): Original listing description (should be HTML-cleaned)
    
    Returns:
        dict: Optimized listing content with edited_title and edited_description, or None on failure
    """
    # Import here to avoid circular import issues
    from backend.ebay_cli import call_text_llm
    
    # Load prompt template from file
    prompt_template_path = "prompts/generateTextPrompt.txt"
    try:
        with open(prompt_template_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()
    except FileNotFoundError:
        print(f"❌ Prompt template file not found: {prompt_template_path}")
        return None
    except Exception as e:
        print(f"❌ Error loading prompt template: {e}")
        return None
    
    # Format the prompt with listing data
    prompt = prompt_template.format(
        original_title=old_title,
        original_description=old_description
    )
    
    # Call the configured text LLM (OpenRouter or Bedrock based on model id)
    llm_response = call_text_llm(prompt, model=model)
    
    if llm_response:
        try:
            # Parse JSON response
            optimized_content = json.loads(llm_response)
            
            print("\n🎯 Optimized eBay Listing:")
            print("=" * 50)
            print(f"📝 Optimized Title ({len(optimized_content.get('edited_title', ''))} chars):")
            print(f"   {optimized_content.get('edited_title', 'N/A')}")
            print(f"\n📄 Optimized Description:")
            print(f"   {optimized_content.get('edited_description', 'N/A')}")
            print("=" * 50)
            
            return optimized_content
            
        except json.JSONDecodeError as e:
            print(f"❌ Error parsing LLM response as JSON: {e}")
            print(f"Raw response: {llm_response}")
            return None
    else:
        print("❌ Failed to get response from text LLM")
        return None


def _find_closing_quote(s):
    """Return index of first unescaped double-quote in s, or -1."""
    i = 0
    while i < len(s):
        if s[i] == '\\':
            i += 2  # skip escaped char
            continue
        if s[i] == '"':
            return i
        i += 1
    return -1


def create_text_stream(old_title, old_description, model="deepseek/deepseek-v4-flash"):
    """
    Stream optimized title/description tokens as they arrive from the LLM.

    Yields dicts:
      {"type": "token", "field": "title",       "delta": "<chars>"}
      {"type": "token", "field": "description", "delta": "<chars>"}
      {"type": "result", "data": {"edited_title": "...", "edited_description": "..."}}
      {"type": "error",  "error": "<message>"}
    """
    from backend.ebay_cli import call_text_llm_stream

    prompt_template_path = "prompts/generateTextPrompt.txt"
    try:
        with open(prompt_template_path, "r", encoding="utf-8") as f:
            prompt_template = f.read()
    except Exception as e:
        yield {"type": "error", "error": f"Failed to load prompt: {e}"}
        return

    prompt = prompt_template.format(
        original_title=old_title,
        original_description=old_description,
    )

    accumulated = ""
    # State machine: "before_title" -> "in_title" -> "before_desc" -> "in_description" -> "done"
    state = "before_title"
    # Markers that signal entry into each field value (JSON string after the key colon)
    TITLE_MARKER = '"edited_title"'
    DESC_MARKER = '"edited_description"'

    for token in call_text_llm_stream(prompt, model):
        if token is None:
            yield {"type": "error", "error": "LLM stream returned no content"}
            return

        accumulated += token

        if state == "before_title":
            if TITLE_MARKER in accumulated:
                # Find the opening quote of the value
                marker_end = accumulated.index(TITLE_MARKER) + len(TITLE_MARKER)
                rest = accumulated[marker_end:]
                # Skip : and whitespace to find the opening "
                colon_pos = rest.find(":")
                if colon_pos != -1:
                    after_colon = rest[colon_pos + 1:].lstrip()
                    if after_colon.startswith('"'):
                        # Everything after the opening quote is title content
                        title_content = after_colon[1:]
                        # Find the first unescaped closing quote in the buffered content
                        close_pos = _find_closing_quote(title_content)
                        if close_pos != -1:
                            title_content = title_content[:close_pos]
                            if title_content:
                                yield {"type": "token", "field": "title", "delta": title_content}
                            state = "before_desc"  # title already complete
                        else:
                            if title_content:
                                yield {"type": "token", "field": "title", "delta": title_content}
                            state = "in_title"

        elif state == "in_title":
            # Send the new token; stop at closing unescaped quote
            # Simple heuristic: if the token ends the title value
            if '"' in token:
                # Split at first unescaped quote
                parts = token.split('"', 1)
                if parts[0]:
                    yield {"type": "token", "field": "title", "delta": parts[0]}
                state = "before_desc"
            else:
                yield {"type": "token", "field": "title", "delta": token}

        elif state == "before_desc":
            if DESC_MARKER in accumulated:
                marker_end = accumulated.rindex(DESC_MARKER) + len(DESC_MARKER)
                rest = accumulated[marker_end:]
                colon_pos = rest.find(":")
                if colon_pos != -1:
                    after_colon = rest[colon_pos + 1:].lstrip()
                    if after_colon.startswith('"'):
                        desc_content = after_colon[1:]
                        if desc_content:
                            yield {"type": "token", "field": "description", "delta": desc_content}
                        state = "in_description"

        elif state == "in_description":
            if '"' in token:
                parts = token.split('"', 1)
                if parts[0]:
                    yield {"type": "token", "field": "description", "delta": parts[0]}
                state = "done"
            else:
                yield {"type": "token", "field": "description", "delta": token}

        elif state == "done":
            pass  # ignore remaining JSON tokens after description closes

    # Parse final accumulated JSON for the clean result
    try:
        # Strip markdown fences if present
        clean = accumulated.strip()
        if clean.startswith("```"):
            clean = clean.split("```")[1]
            if clean.startswith("json"):
                clean = clean[4:]
        result = json.loads(clean.strip())
        yield {"type": "result", "data": result}
    except json.JSONDecodeError:
        yield {"type": "error", "error": f"Failed to parse LLM JSON response: {accumulated[:200]}"}
