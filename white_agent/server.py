"""A2A Server for the ALFWorld White Agent."""

import os
import dotenv
import uvicorn
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentSkill, AgentCard, AgentCapabilities
from a2a.utils import new_agent_text_message

from .agent import WhiteAgent


dotenv.load_dotenv()


def create_agent_card(url: str) -> AgentCard:
    """Create the ALFWorld White Agent card programmatically."""
    skill = AgentSkill(
        id="alfworld_task_solving",
        name="ALFWorld Task Solving",
        description="Solve household tasks in a text-based environment with cleanup awareness.",
        tags=["reasoning", "exploration", "planning", "cleanup"],
        examples=[
            "Put a clean plate in the drawer",
            "Heat the egg in the microwave",
            "Cool the lettuce in the fridge",
        ],
    )
    
    card = AgentCard(
        name="ALFWorld White Agent",
        description="""ALFWorld White Agent (Assessee) - A reflection-augmented GPT-4o agent for household tasks.

Features:
- Structured workflow: Understand → Explore → Interact → Manipulate → Complete
- Multi-objective: Task completion + cleanup awareness
- Cross-episode reflection learning
- Repetition and cycle detection""",
        url=url,
        version="1.1.0",
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        capabilities=AgentCapabilities(streaming=True),
        skills=[skill],
    )
    return card


class ALFWorldAgentExecutor(AgentExecutor):
    """Executor that bridges A2A requests to the WhiteAgent."""

    def __init__(self):
        # Create agent with inline config (no file dependencies)
        self.agent = None
        self.context_to_agent = {}

    def _get_or_create_agent(self, context_id: str) -> WhiteAgent:
        """Get existing agent for context or create new one."""
        if context_id not in self.context_to_agent:
            # Create agent with inline configuration
            agent = WhiteAgent.__new__(WhiteAgent)
            agent.system_prompt = self._get_system_prompt()
            agent.policy_type = "neural"
            agent.model = os.environ.get("MODEL", "gpt-4o")
            agent.max_reflections = 3
            agent.max_steps = 50
            agent.track_cleanup = True
            agent.client = None
            agent.state = {}
            agent.reflections = []
            
            # Initialize OpenAI client if API key is present
            api_key = os.environ.get("OPENAI_API_KEY")
            if api_key:
                from openai import OpenAI
                agent.client = OpenAI(api_key=api_key)
            
            self.context_to_agent[context_id] = agent
        
        return self.context_to_agent[context_id]

    def _get_system_prompt(self) -> str:
        """Return the system prompt for the agent."""
        return """## Your Role
You are the **White Agent (Assessee)** in the ALFWorld environment.
Your goal is to successfully complete household tasks based on text-based instructions while maintaining a clean environment.

## Your Capabilities
Common commands: `go to [location]`, `take [object] from [receptacle]`, `put [object] in/on [receptacle]`, `open [receptacle]`, `close [receptacle]`, `heat [object] with [source]`, `cool [object] with [source]`, `clean [object] with [source]`, `use [object]`, `examine [object]`, `look`, `inventory`.

## Workflow
1. **Understand**: Read the goal carefully.
2. **Explore**: Navigate and `look` to find objects.
3. **Interact**: `take` what you need.
4. **Manipulate**: Heat/cool/clean if required.
5. **Complete**: Place the object. ALWAYS close containers after use.

## Rules
- Output ONLY the command (no reasoning).
- Use exact object names (e.g., `apple 1`).
- Close all containers after opening.
- Don't repeat failed actions."""

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute a task request."""
        user_input = context.get_user_input()
        agent = self._get_or_create_agent(context.context_id)
        
        # Check if this is a new episode (reset) or continuation
        if not agent.state or agent.state.get("done", False):
            agent.reset(user_input)
        
        # Get action from agent
        action = agent.act(user_input)
        
        # Send response
        await event_queue.enqueue_event(
            new_agent_text_message(action, context_id=context.context_id)
        )

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel the current task."""
        # Clean up agent state for this context
        if context.context_id in self.context_to_agent:
            del self.context_to_agent[context.context_id]


# Custom endpoints for AgentBeats compatibility
async def status_endpoint(request):
    """Health check / status endpoint for AgentBeats."""
    return JSONResponse({
        "status": "ok",
        "agent": "ALFWorld White Agent",
        "version": "1.1.0",
        "ready": True
    })


async def health_endpoint(request):
    """Health check endpoint."""
    return JSONResponse({"status": "healthy"})


def start_white_agent(host: str = "0.0.0.0", port: int = 9002):
    """Start the White Agent A2A server."""
    print(f"Starting ALFWorld White Agent on {host}:{port}...")
    
    # Get the agent URL from environment or construct from host/port
    agent_url = os.environ.get("AGENT_URL", f"http://{host}:{port}")
    print(f"Agent URL: {agent_url}")
    
    card = create_agent_card(agent_url)
    
    request_handler = DefaultRequestHandler(
        agent_executor=ALFWorldAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    
    a2a_app = A2AStarletteApplication(
        agent_card=card,
        http_handler=request_handler,
    )
    
    # Build the A2A app and add custom routes
    starlette_app = a2a_app.build()
    
    # Add custom routes for AgentBeats compatibility
    starlette_app.routes.append(Route("/status", status_endpoint, methods=["GET"]))
    starlette_app.routes.append(Route("/health", health_endpoint, methods=["GET"]))
    
    print(f"Agent card will be available at: {agent_url}/.well-known/agent.json")
    print(f"Status endpoint: {agent_url}/status")
    uvicorn.run(starlette_app, host=host, port=port)

