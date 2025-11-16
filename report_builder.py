from dotenv import load_dotenv
import os
import time
from loguru import logger
from langfuse import Langfuse, observe
from openai import OpenAI
from unstructured.partition.pdf import partition_pdf
import tiktoken
from typing import Optional, Tuple


load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_BASE_URL = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")
PROMPT_NAME = os.getenv("PROMPT_NAME")
LANGUAGE = os.getenv("LANGUAGE", "french")  # Default to "english", can be "french" or "english"

# Initialize Langfuse client
langfuse = Langfuse(
    secret_key=LANGFUSE_SECRET_KEY,
    public_key=LANGFUSE_PUBLIC_KEY,
    host=LANGFUSE_BASE_URL
)

# Initialize OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)
MODEL = os.getenv("MODEL", "gpt-4o-mini")

# Model context limits (input + output tokens)
# These are approximate - leaving buffer for system prompt and response
MODEL_CONTEXT_LIMITS = {
    "gpt-4o": 128000,  # 128k context
    "gpt-4o-mini": 128000,  # 128k context
    "gpt-4-turbo": 128000,
    "gpt-4": 8192,
    "gpt-3.5-turbo": 16385,
}

# Buffer for system prompt and response (conservative estimate)
TOKEN_BUFFER = 2000  # Reserve tokens for system prompt and response


def get_encoding_name(model: str = MODEL) -> str:
    """
    Get the tiktoken encoding name for a given model.
    
    Args:
        model: The model name
    
    Returns:
        Encoding name (e.g., "o200k_base", "cl100k_base")
    """
    encoding_map = {
        "gpt-4o": "o200k_base",
        "gpt-4o-mini": "o200k_base",
        "gpt-4-turbo": "cl100k_base",
        "gpt-4": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
    }
    return encoding_map.get(model, "cl100k_base")


def get_token_count(text: str, model: str = MODEL) -> int:
    """
    Count the number of tokens in a text string for a given model.
    
    Args:
        text: The text to count tokens for
        model: The model name (default: MODEL)
    
    Returns:
        Number of tokens
    """
    try:
        # Get encoding name for the model
        encoding_name = get_encoding_name(model)
        logger.debug(f"Counting tokens using encoding: {encoding_name} for model: {model}")
        
        # Get encoding
        encoding = tiktoken.get_encoding(encoding_name)
        
        # Count tokens
        tokens = encoding.encode(text)
        token_count = len(tokens)
        logger.debug(f"Token count: {token_count:,} tokens for {len(text):,} characters (ratio: {len(text)/token_count:.2f} chars/token)")
        return token_count
    except Exception as e:
        logger.warning(f"Error counting tokens with tiktoken: {e}. Using character-based estimation.")
        # Fallback: rough estimation (1 token ≈ 4 characters for English)
        estimated_tokens = len(text) // 4
        logger.warning(f"Using fallback estimation: {estimated_tokens:,} tokens (estimated from {len(text):,} characters)")
        return estimated_tokens


def get_model_context_limit(model: str = MODEL) -> int:
    """
    Get the context limit for a given model.
    
    Args:
        model: The model name
    
    Returns:
        Context limit in tokens
    """
    # Extract base model name (handle versions like "gpt-4o-2024-08-06")
    base_model = model.split("-")[0] + "-" + model.split("-")[1] if "-" in model else model
    if "gpt-4o" in model:
        base_model = "gpt-4o"
    elif "gpt-4-turbo" in model:
        base_model = "gpt-4-turbo"
    elif "gpt-4" in model:
        base_model = "gpt-4"
    elif "gpt-3.5-turbo" in model:
        base_model = "gpt-3.5-turbo"
    
    return MODEL_CONTEXT_LIMITS.get(base_model, 128000)  # Default to 128k if unknown


def truncate_content_intelligently(content: str, max_tokens: int, model: str = MODEL) -> str:
    """
    Intelligently truncate content while preserving important sections.
    Tries to keep: abstract, introduction, key sections, and conclusion.
    
    Args:
        content: The content to truncate
        max_tokens: Maximum number of tokens allowed
        model: Model name for token counting
    
    Returns:
        Truncated content
    """
    truncate_start_time = time.time()
    current_tokens = get_token_count(content, model)
    original_length = len(content)
    
    if current_tokens <= max_tokens:
        logger.debug(f"Content within token limit ({current_tokens:,} <= {max_tokens:,}), no truncation needed")
        return content
    
    logger.warning(
        f"Content exceeds token limit ({current_tokens:,} > {max_tokens:,}). "
        f"Truncating intelligently (reduction: {((current_tokens - max_tokens) / current_tokens * 100):.1f}%)..."
    )
    
    # Split content into sections (looking for common paper structure)
    lines = content.split('\n')
    sections = []
    current_section = []
    section_headers = ['abstract', 'introduction', 'methodology', 'methods', 
                      'results', 'discussion', 'conclusion', 'references']
    
    for line in lines:
        line_lower = line.lower().strip()
        # Check if this line looks like a section header
        is_header = any(header in line_lower and len(line_lower) < 100 
                       for header in section_headers)
        
        if is_header and current_section:
            sections.append(('\n'.join(current_section), current_section[0] if current_section else ''))
            current_section = [line]
        else:
            current_section.append(line)
    
    if current_section:
        sections.append(('\n'.join(current_section), current_section[0] if current_section else ''))
    
    # If we couldn't identify sections, do simple truncation
    if len(sections) <= 1:
        logger.warning("Could not identify sections. Using simple truncation.")
        logger.info(f"Attempting simple truncation from {current_tokens:,} to {max_tokens:,} tokens")
        # Use the appropriate encoding for the model
        encoding_name = get_encoding_name(model)
        encoding = tiktoken.get_encoding(encoding_name)
        tokens = encoding.encode(content)
        truncated_tokens = tokens[:max_tokens]
        truncated_content = encoding.decode(truncated_tokens)
        truncate_time = time.time() - truncate_start_time
        logger.info(f"Simple truncation complete in {truncate_time:.2f}s - Reduced from {len(content):,} to {len(truncated_content):,} characters")
        return truncated_content
    
    # Prioritize sections: abstract, introduction, conclusion
    priority_sections = ['abstract', 'introduction', 'conclusion']
    prioritized = []
    others = []
    
    for section_text, header in sections:
        header_lower = header.lower()
        if any(prio in header_lower for prio in priority_sections):
            prioritized.append((section_text, header))
        else:
            others.append((section_text, header))
    
    # Build truncated content starting with prioritized sections
    truncated_content = []
    token_count = 0
    
    # Add prioritized sections first
    for section_text, header in prioritized:
        section_tokens = get_token_count(section_text, model)
        if token_count + section_tokens <= max_tokens:
            truncated_content.append(section_text)
            token_count += section_tokens
        else:
            # Truncate this section if needed
            remaining = max_tokens - token_count
            if remaining > 100:  # Only if we have meaningful space
                encoding_name = get_encoding_name(model)
                encoding = tiktoken.get_encoding(encoding_name)
                tokens = encoding.encode(section_text)
                truncated_tokens = tokens[:remaining]
                truncated_content.append(encoding.decode(truncated_tokens))
            break
    
    # Add other sections if space allows
    for section_text, header in others:
        section_tokens = get_token_count(section_text, model)
        if token_count + section_tokens <= max_tokens:
            truncated_content.append(section_text)
            token_count += section_tokens
        else:
            # Try to add partial section
            remaining = max_tokens - token_count
            if remaining > 100:
                encoding_name = get_encoding_name(model)
                encoding = tiktoken.get_encoding(encoding_name)
                tokens = encoding.encode(section_text)
                truncated_tokens = tokens[:remaining]
                truncated_content.append(encoding.decode(truncated_tokens))
            break
    
    result = '\n\n'.join(truncated_content)
    final_tokens = get_token_count(result, model)
    final_length = len(result)
    truncate_time = time.time() - truncate_start_time
    logger.info(f"Intelligent truncation complete in {truncate_time:.2f}s")
    logger.info(f"Truncated content from {current_tokens:,} to {final_tokens:,} tokens ({((current_tokens - final_tokens) / current_tokens * 100):.1f}% reduction)")
    logger.info(f"Character count reduced from {original_length:,} to {final_length:,} ({((original_length - final_length) / original_length * 100):.1f}% reduction)")
    logger.info(f"Added {len(prioritized)} prioritized sections and {len(truncated_content) - len(prioritized)} other sections")
    
    return result


def prepare_content_for_model(content: str, system_prompt: str, model: str = MODEL) -> Tuple[str, int, int]:
    """
    Prepare content by checking token limits and truncating if necessary.
    
    Args:
        content: The user content to process
        system_prompt: The system prompt text
        model: The model name
    
    Returns:
        Tuple of (prepared_content, content_tokens, total_tokens)
    """
    prepare_start_time = time.time()
    logger.info(f"[Content Preparation] Starting content preparation for model: {model}")
    
    # Get model context limit
    context_limit = get_model_context_limit(model)
    logger.info(f"[Content Preparation] Model context limit: {context_limit:,} tokens")
    
    # Count system prompt tokens
    logger.debug(f"[Content Preparation] Counting system prompt tokens...")
    system_tokens = get_token_count(system_prompt, model)
    logger.info(f"[Content Preparation] System prompt tokens: {system_tokens:,}")
    
    # Calculate available tokens for user content
    available_tokens = context_limit - system_tokens - TOKEN_BUFFER
    logger.info(f"[Content Preparation] Available tokens for content: {available_tokens:,} (limit: {context_limit:,} - system: {system_tokens:,} - buffer: {TOKEN_BUFFER:,})")
    
    if available_tokens <= 0:
        logger.error(f"[Content Preparation] ERROR: System prompt ({system_tokens:,} tokens) exceeds or leaves no room in context limit ({context_limit:,})")
        raise ValueError("System prompt is too long for the model context limit")
    
    # Count content tokens
    logger.debug(f"[Content Preparation] Counting content tokens...")
    content_tokens = get_token_count(content, model)
    logger.info(f"[Content Preparation] Original content tokens: {content_tokens:,}")
    
    # Truncate if necessary
    if content_tokens > available_tokens:
        logger.warning(
            f"[Content Preparation] Content ({content_tokens:,} tokens) exceeds available space ({available_tokens:,} tokens). "
            f"Truncating..."
        )
        content = truncate_content_intelligently(content, available_tokens, model)
        content_tokens = get_token_count(content, model)
        logger.info(f"[Content Preparation] After truncation: {content_tokens:,} tokens")
    else:
        logger.info(f"[Content Preparation] Content fits within available tokens, no truncation needed")
    
    total_tokens = system_tokens + content_tokens
    prepare_time = time.time() - prepare_start_time
    
    logger.info(
        f"[Content Preparation] ✓ Preparation complete in {prepare_time:.2f}s"
    )
    logger.info(
        f"[Content Preparation] Token usage - System: {system_tokens:,}, Content: {content_tokens:,}, "
        f"Total: {total_tokens:,}/{context_limit:,} ({total_tokens/context_limit*100:.1f}%)"
    )
    
    return content, content_tokens, total_tokens


@observe()
def build_report(content, prompt_name=PROMPT_NAME, language=LANGUAGE):
    """
    Build a report using the agent with system prompt from Langfuse.
    
    Args:
        content: The user content/query to process
        prompt_name: The name of the prompt in Langfuse (default: "system_prompt")
                      You can also pass a tuple like ("prompt_name", "production") to get a specific label
        language: The language for templating (default: "english", can be "french" or "english")
    
    Returns:
        The generated report content
    """
    report_start_time = time.time()
    logger.info(f"=== Starting report generation ===")
    logger.info(f"Input content length: {len(content):,} characters")
    logger.info(f"Prompt name: {prompt_name}, Language: {language}, Model: {MODEL}")
    
    try:
        # Fetch the system prompt from Langfuse
        logger.info(f"[Report Generation] Fetching system prompt from Langfuse...")
        langfuse_fetch_start = time.time()
        # If prompt_name is a tuple, use it for (name, label), otherwise just use the name
        if isinstance(prompt_name, tuple):
            logger.info(f"[Report Generation] Fetching prompt '{prompt_name[0]}' with label 'production'")
            prompt = langfuse.get_prompt(prompt_name[0], label="production")
        else:
            logger.info(f"[Report Generation] Fetching prompt '{prompt_name}'")
            prompt = langfuse.get_prompt(prompt_name)
        
        langfuse_fetch_time = time.time() - langfuse_fetch_start
        logger.info(f"[Report Generation] ✓ Fetched prompt from Langfuse in {langfuse_fetch_time:.2f}s")
        
        # Get the prompt content - this is the system prompt text
        system_prompt = prompt.prompt
        system_prompt_length = len(system_prompt)
        logger.info(f"[Report Generation] System prompt length: {system_prompt_length:,} characters")
        
        # Validate input
        if not content or not content.strip():
            logger.error("[Report Generation] ERROR: Content is empty or contains only whitespace")
            raise ValueError("Content cannot be empty")
        
        # Replace template variables
        # Replace {{LANGUAGE}} with the actual language value
        logger.debug(f"[Report Generation] Replacing template variable {{LANGUAGE}} with '{language}'")
        system_prompt = system_prompt.replace("{{LANGUAGE}}", language)
        
        # Add the instruction text
        instruction_text = ""
        system_prompt = f"{instruction_text}\n\n{system_prompt}"
        logger.debug(f"[Report Generation] Added instruction text to system prompt")
        
        logger.info(f"[Report Generation] System prompt prepared (final length: {len(system_prompt):,} characters)")
        
        # Prepare content with token handling
        logger.info(f"[Report Generation] Preparing content for model...")
        prepared_content, content_tokens, total_tokens = prepare_content_for_model(
            content, system_prompt, MODEL
        )

        logger.info(f"[Report Generation] Content prepared: {content_tokens:,} tokens")
        
        # Create messages with system prompt
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prepared_content}
        ]
        logger.debug(f"[Report Generation] Created message array with {len(messages)} messages")
        
        # Use OpenAI client - the @observe() decorator will automatically log this call to Langfuse
        logger.info(f"[Report Generation] Sending request to OpenAI API...")
        logger.info(f"[Report Generation] Model: {MODEL}, Total tokens: {total_tokens:,}")
        openai_start_time = time.time()
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
        )
        openai_time = time.time() - openai_start_time
        
        # Log response details
        if hasattr(response, 'usage'):
            usage = response.usage
            logger.info(f"[Report Generation] ✓ OpenAI API response received in {openai_time:.2f}s")
            logger.info(f"[Report Generation] Token usage - Prompt: {usage.prompt_tokens:,}, Completion: {usage.completion_tokens:,}, Total: {usage.total_tokens:,}")
        else:
            logger.info(f"[Report Generation] ✓ OpenAI API response received in {openai_time:.2f}s")
        
        # Validate response
        if not response.choices or not response.choices[0].message.content:
            logger.error("[Report Generation] ERROR: Received empty response from OpenAI API")
            raise ValueError("Received empty response from OpenAI API")
        
        report_content = response.choices[0].message.content
        report_length = len(report_content)
        total_time = time.time() - report_start_time
        
        logger.info(f"[Report Generation] ✓ Report generation complete in {total_time:.2f}s")
        logger.info(f"[Report Generation] Generated report length: {report_length:,} characters")
        logger.info(f"=== Report generation complete ===")
        
        return report_content
        
    except Exception as e:
        processing_time = time.time() - report_start_time
        logger.error(f"=== ERROR in report generation after {processing_time:.2f}s ===")
        logger.error(f"Error type: {type(e).__name__}")
        logger.error(f"Error message: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Fallback: use without system prompt if Langfuse fetch fails
        logger.warning("[Report Generation] Attempting fallback mode without system prompt...")
        fallback_start_time = time.time()
        
        # Still need to handle token limits in fallback
        try:
            logger.info("[Report Generation Fallback] Calculating token limits...")
            context_limit = get_model_context_limit(MODEL)
            available_tokens = context_limit - TOKEN_BUFFER
            logger.info(f"[Report Generation Fallback] Available tokens: {available_tokens:,}")
            
            if available_tokens <= 0:
                logger.error(f"[Report Generation Fallback] ERROR: Model context limit ({context_limit:,}) is too small after buffer ({TOKEN_BUFFER:,})")
                raise ValueError("Model context limit is too small")
            
            content_tokens = get_token_count(content, MODEL)
            logger.info(f"[Report Generation Fallback] Content tokens: {content_tokens:,}")
            
            if content_tokens > available_tokens:
                logger.warning(f"[Report Generation Fallback] Truncating content ({content_tokens:,} > {available_tokens:,})")
                content = truncate_content_intelligently(content, available_tokens, MODEL)
                content_tokens = get_token_count(content, MODEL)
                logger.info(f"[Report Generation Fallback] After truncation: {content_tokens:,} tokens")
            
            logger.info(f"[Report Generation Fallback] Sending request to OpenAI API (model: {MODEL})...")
            openai_fallback_start = time.time()
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": content}],
            )
            openai_fallback_time = time.time() - openai_fallback_start
            logger.info(f"[Report Generation Fallback] ✓ OpenAI API response received in {openai_fallback_time:.2f}s")
            
            if not response.choices or not response.choices[0].message.content:
                logger.error("[Report Generation Fallback] ERROR: Received empty response from OpenAI API")
                raise ValueError("Received empty response from OpenAI API in fallback")
            
            fallback_content = response.choices[0].message.content
            fallback_time = time.time() - fallback_start_time
            logger.info(f"[Report Generation Fallback] ✓ Fallback report generation complete in {fallback_time:.2f}s")
            logger.info(f"[Report Generation Fallback] Generated report length: {len(fallback_content):,} characters")
            logger.warning("=== Report generation completed using fallback mode ===")
            
            return fallback_content
        except Exception as fallback_error:
            fallback_time = time.time() - fallback_start_time
            logger.error(f"[Report Generation Fallback] ERROR: Fallback failed after {fallback_time:.2f}s")
            logger.error(f"[Report Generation Fallback] Error type: {type(fallback_error).__name__}")
            logger.error(f"[Report Generation Fallback] Error message: {str(fallback_error)}")
            import traceback
            logger.error(f"[Report Generation Fallback] Traceback: {traceback.format_exc()}")
            raise

if __name__ == "__main__":
    #read a pdf using unstructured
    elements = partition_pdf(
            filename="uploads/attentionisallyouneed.pdf",
            strategy="auto",
            infer_table_structure=True,
            languages=["eng"],
            size={"longest_edge": 2048},
        )
        
    # Extract text content from elements
    extracted_text = "\n\n".join([str(element) for element in elements])
    report = build_report(extracted_text)
    
    # Save report to file
    with open("reports/report_1.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info("Report saved to report.md")
    print(f"Report saved to report.md ({len(report)} characters)")