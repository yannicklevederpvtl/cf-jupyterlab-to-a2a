"""
Summarizer Module - Core summarization logic extracted from Notebook-Lab4

This module contains the summarization logic directly from the notebook.
It creates a LangChain LLMChain that can summarize text using an OpenAI-compatible LLM.
"""

import httpx
import warnings
from langchain_core.prompts import ChatPromptTemplate
from langchain_classic.chains import LLMChain
from langchain_openai import ChatOpenAI
from cfutils import CFGenAIService

warnings.filterwarnings('ignore')


def create_summarization_chain():
    """
    Creates a LangChain LLMChain for text summarization.
    
    This function extracts the core logic from Notebook-Lab4:
    - Steps 2-5: Service setup, LLM initialization, prompt template, and chain creation
    
    Returns:
        LLMChain: A configured chain ready to summarize text
    """
    
    # ============================================================================
    # FROM NOTEBOOK: Step 2 - Set up the OpenAI API credentials
    # ============================================================================
    # Load your service details - Gen AI service is bound to the app
    chat_service = CFGenAIService("tanzu-gpt-oss-120b")
    
    # List available models
    models = chat_service.list_models()
    print(f"[INFO] Available models:")
    for m in models:
        print(f"  - {m['name']} (capabilities: {', '.join(m['capabilities'])})")
    
    # Construct chat_credentials
    chat_credentials = {
        "api_base": chat_service.api_base + "/openai/v1",
        "api_key": chat_service.api_key,
        "model_name": models[0]["name"]
    }
    
    # ============================================================================
    # FROM NOTEBOOK: Step 3 - Initialize the LLM
    # ============================================================================
    # HTTP client (optional but recommended for custom config)
    httpx_client = httpx.Client(verify=False)  # verify=False if your endpoint needs --insecure
    
    # Initialize the LLM
    llm = ChatOpenAI(
        temperature=0.9,
        model=chat_credentials["model_name"],   # model name from CF service
        base_url=chat_credentials["api_base"],  # OpenAI-compatible endpoint
        api_key=chat_credentials["api_key"],    # Bearer token
        http_client=httpx_client
    )
    
    # ============================================================================
    # FROM NOTEBOOK: Step 4 - Create a prompt template
    # ============================================================================
    template = """<s>[INST]
You are a helpful, respectful and honest assistant.
Always assist with care, respect, and truth. Respond with utmost utility yet securely.
Avoid harmful, unethical, prejudiced, or negative content. Ensure replies promote fairness and positivity.
I will give you a text that you must summarize as best as you can.

### TEXT:
{input}

### SUMMARY:
[/INST]
"""
    PROMPT = ChatPromptTemplate.from_template(template)
    
    # ============================================================================
    # FROM NOTEBOOK: Step 5 - Create a chain
    # ============================================================================
    # Create the LLMChain that will be used for summarization
    conversation = LLMChain(
        llm=llm,
        prompt=PROMPT,
        verbose=False
    )
    
    return conversation


def summarize_text(chain, text: str) -> str:
    """
    Summarize a given text using the provided chain.
    
    This function encapsulates the logic from Notebook-Lab4 Step 7:
    - Takes text input and runs it through the conversation chain
    - Returns the summary
    
    Args:
        chain: The LLMChain instance created by create_summarization_chain()
        text: The text to summarize
        
    Returns:
        str: The summarized text
    """
    # ============================================================================
    # FROM NOTEBOOK: Step 7 - Run the chain (extracted from the loop)
    # ============================================================================
    # This is the core prediction call from the notebook:
    # summary_text = conversation.predict(input=summary_input)
    summary_text = chain.predict(input=text)
    return summary_text
