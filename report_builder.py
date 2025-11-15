from dotenv import load_dotenv
import os
from loguru import logger
from langfuse import Langfuse, observe
from openai import OpenAI
from unstructured.partition.pdf import partition_pdf


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
    try:
        # Fetch the system prompt from Langfuse
        # If prompt_name is a tuple, use it for (name, label), otherwise just use the name
        if isinstance(prompt_name, tuple):
            prompt = langfuse.get_prompt(prompt_name[0], label="production")
        else:
            prompt = langfuse.get_prompt(prompt_name)
        
        # Get the prompt content - this is the system prompt text
        system_prompt = prompt.prompt
        
        # Replace template variables
        # Replace {{LANGUAGE}} with the actual language value
        system_prompt = system_prompt.replace("{{LANGUAGE}}", language)
        
        # Add the instruction text
        instruction_text = "Extract this paper and create a 5-minute pitch: [PDF]"
        system_prompt = f"{instruction_text}\n\n{system_prompt}"
        
        logger.info(f"Fetched system prompt '{prompt_name}' from Langfuse with language={language}")
        
        # Create messages with system prompt
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content}
        ]
        
        # Use OpenAI client - the @observe() decorator will automatically log this call to Langfuse
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error building report: {e}")
        # Fallback: use without system prompt if Langfuse fetch fails
        logger.warning("Falling back to request without system prompt")
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
        )
        return response.choices[0].message.content

if __name__ == "__main__":
    #read a pdf using unstructured
    elements = partition_pdf(
            filename="uploads/attentionisallyouneed.pdf",
            strategy="auto",
            infer_table_structure=True,
        )
        
        # Extract text content from elements
    extracted_text = "\n\n".join([str(element) for element in elements])
    report = build_report(extracted_text)
    
    # Save report to file
    with open("reports/report_1.md", "w", encoding="utf-8") as f:
        f.write(report)
    
    logger.info("Report saved to report.md")
    print(f"Report saved to report.md ({len(report)} characters)")