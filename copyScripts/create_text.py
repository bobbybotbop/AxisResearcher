"""
Create Text Module

This module contains functions for creating optimized eBay listing text.
"""

import json


def create_text(old_title, old_description):
    """
    Generate optimized listing content using LLM from original title and description.
    
    Args:
        old_title (str): Original listing title
        old_description (str): Original listing description (should be HTML-cleaned)
    
    Returns:
        dict: Optimized listing content with edited_title and edited_description, or None on failure
    """
    # Import here to avoid circular import issues
    from main_ebay_commands import call_openrouter_llm
    
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
    
    # Call OpenRouter API to get optimized content
    llm_response = call_openrouter_llm(prompt)
    
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
        print("❌ Failed to get response from OpenRouter")
        return None
