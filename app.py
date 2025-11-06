"""
A2A Summarization Agent - Main Application Entry Point

This module wraps the summarization logic from Notebook-Lab4 with Google's A2A protocol.
It creates an A2A server that exposes the summarization capability as a network-accessible agent.

Architecture:
1. Summarizer module (summarizer.py) - Contains notebook logic
2. AgentExecutor - Wraps summarizer with A2A protocol
3. Request Handler - Handles A2A JSON-RPC requests
4. Server - Exposes the agent via HTTP
"""

import os
import json
import asyncio
import uvicorn

# ============================================================================
# A2A WRAPPER: Import A2A SDK components
# ============================================================================
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater, InMemoryTaskStore
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.apps import A2AStarletteApplication
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    Task,
    TaskState
)
from a2a.utils import (
    new_agent_text_message,
    new_task,
)

# ============================================================================
# FROM NOTEBOOK: Import our summarization module
# ============================================================================
# This contains the core logic extracted from Notebook-Lab4
from summarizer import create_summarization_chain, summarize_text


# ============================================================================
# A2A WRAPPER: Agent Skill Definition
# ============================================================================
summarization_skill = AgentSkill(
    id='text-summarization',
    name='Text Summarization',
    description='Summarizes input text using LLM, producing concise summaries while preserving key information',
    tags=['summarization', 'text-processing', 'llm']
)


# ============================================================================
# A2A WRAPPER: Agent Card
# ============================================================================
def get_agent_card(base_url: str) -> AgentCard:
    """
    Creates the Agent Card that describes this agent to A2A clients.
    Published at /.well-known/agent.json
    """
    return AgentCard(
        name='Text Summarization Agent',
        description='A2A agent that summarizes text using LangChain and OpenAI-compatible LLM endpoints',
        url=base_url,
        version='1.0.0',
        defaultInputModes=['text'],
        defaultOutputModes=['text'],
        capabilities=AgentCapabilities(streaming=True),
        skills=[summarization_skill]
    )


# ============================================================================
# A2A WRAPPER: Agent Executor
# ============================================================================
class SummarizationAgentExecutor(AgentExecutor):
    """
    Agent Executor that wraps the summarization chain with A2A protocol.
    
    Implements the A2A AgentExecutor interface:
    1. Receives requests from A2A clients via RequestContext
    2. Executes the summarization logic
    3. Publishes updates via EventQueue
    4. Manages task lifecycle (submitted -> working -> completed)
    """
    
    def __init__(self):
        """Initialize the executor and create the summarization chain."""
        print("[INFO] Initializing SummarizationAgentExecutor...")
        # FROM NOTEBOOK: Create the summarization chain (Steps 2-5)
        self.summarization_chain = create_summarization_chain()
        print("[INFO] Summarization chain created successfully")
    
    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """
        Execute the summarization task.
        
        Args:
            context: RequestContext containing the user's message and metadata
            event_queue: EventQueue for publishing task updates to the client
        """
        # Extract the user's text input from the A2A message
        query = context.get_user_input()
        print(f"[INFO] Received summarization request: {query[:100]}...")
        
        # Get or create the task
        task = context.current_task
        if not task:
            task = new_task(context.message)
            event_queue.enqueue_event(task)
        
        # Get context_id from context (not from task)
        context_id = context.context_id or context.task_id
        
        # Create a TaskUpdater to publish status updates
        updater = TaskUpdater(event_queue, task.id, context_id)
        
        try:
            # ====================================================================
            # A2A WRAPPER: Update task status to "working"
            # ====================================================================
            await updater.update_status(
                TaskState.working,
                new_agent_text_message(
                    "Processing your text for summarization...",
                    context_id,
                    task.id,
                ),
            )
            
            # ====================================================================
            # FROM NOTEBOOK: Execute the summarization (Step 7 logic)
            # ====================================================================
            # Run in executor to avoid blocking the event loop
            loop = asyncio.get_event_loop()
            summary_result = await loop.run_in_executor(
                None, 
                summarize_text, 
                self.summarization_chain, 
                query
            )
            
            # ====================================================================
            # A2A WRAPPER: Mark task as completed with the summary
            # ====================================================================
            await updater.complete(
                message=new_agent_text_message(
                    summary_result,
                    context_id,
                    task.id,
                )
            )
            print(f"[INFO] Summarization completed successfully")
            
        except Exception as e:
            print(f"[ERROR] Summarization failed: {e}")
            import traceback
            traceback.print_exc()
            # A2A WRAPPER: Send error message to client
            await updater.complete(
                message=new_agent_text_message(
                    f"Error during summarization: {str(e)}",
                    context_id,
                    task.id,
                )
            )
    
    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        """Handle task cancellation request from A2A client."""
        print("[INFO] Task cancellation requested")
        return None


# ============================================================================
# A2A WRAPPER: Helper Functions
# ============================================================================
def get_base_url(host: str = "0.0.0.0", port: int = 8080) -> str:
    """
    Determine the base URL for the agent card.
    In Cloud Foundry, extract from VCAP_APPLICATION.
    Otherwise, use environment variable or construct from host/port.
    
    Returns:
        str: The base URL (e.g., https://cf-summarization-a2a.apps.domain.com)
    """
    # Priority 1: Explicit environment variable
    if os.getenv("A2A_BASE_URL"):
        return os.getenv("A2A_BASE_URL")
    
    # Priority 2: Cloud Foundry VCAP_APPLICATION
    vcap_app = os.getenv("VCAP_APPLICATION")
    if vcap_app:
        try:
            vcap_data = json.loads(vcap_app)
            # Get the first URI from application_uris
            uris = vcap_data.get("application_uris", [])
            if uris:
                # Use https for Cloud Foundry routes
                base_url = f"https://{uris[0]}"
                print(f"[INFO] Detected CF route from VCAP_APPLICATION: {base_url}")
                return base_url
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[WARNING] Failed to parse VCAP_APPLICATION: {e}")
    
    # Priority 3: Fallback to constructed URL (for local development)
    base_url = f"http://{host}:{port}"
    print(f"[INFO] Using default base URL: {base_url}")
    return base_url


# ============================================================================
# A2A WRAPPER: Server Setup
# ============================================================================
def create_a2a_server(host: str = "0.0.0.0", port: int = 8080):
    """
    Create and configure the A2A server.
    
    Returns:
        A2AStarletteApplication: The configured A2A server
    """
    print("[INFO] Creating A2A server...")
    
    # Determine the base URL for the agent card
    base_url = get_base_url(host, port)
    
    # Create the agent executor (wraps our summarization chain)
    agent_executor = SummarizationAgentExecutor()
    
    # Create the request handler
    request_handler = DefaultRequestHandler(
        agent_executor=agent_executor,
        task_store=InMemoryTaskStore()
    )
    
    # Create the agent card
    agent_card = get_agent_card(base_url)
    
    # Create the A2A Starlette application
    server = A2AStarletteApplication(
        agent_card=agent_card,
        http_handler=request_handler
    )
    
    print(f"[INFO] A2A server created with base URL: {base_url}")
    print(f"[INFO] Agent Card: {base_url}/.well-known/agent.json")
    
    return server


def main():
    """Main entry point - starts the A2A server."""
    port = int(os.getenv("PORT", 8080))
    host = os.getenv("HOST", "0.0.0.0")
    
    print("=" * 70)
    print("A2A Summarization Agent")
    print("=" * 70)
    print(f"Server starting on {host}:{port}")
    print(f"Agent Card: http://{host}:{port}/.well-known/agent.json")
    print("=" * 70)
    
    # Create and start the server
    server = create_a2a_server(host, port)
    uvicorn.run(server.build(), host=host, port=port)


if __name__ == "__main__":
    main()