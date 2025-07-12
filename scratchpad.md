```python
class RAGAgent:
    def __init__(self):
        # INITIALIZATION CODE NOT SHOWN
        self.project = AIProjectClient(
            credential=DefaultAzureCredential(),
            endpoint=endpoint)
        self.agent = self.project.agents.get_agent(agent_id)

    async def invoke(self, question: str) -> str:
        thread = self.project.agents.threads.create()

        message = self.project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=question
        )
        run = self.project.agents.runs.create_and_process(
            thread_id=thread.id,
            agent_id=self.agent.id)
        messages = list(self.project.agents.messages.list(thread_id=thread.id, order=ListSortOrder.ASCENDING))

        # ...
```

```python
class CalculatorAgentExecutor(AgentExecutor):

    def __init__(self):
        self.agent = RAGAgent()

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        message_text = context.get_user_input()
        
        result = await self.agent.invoke(message_text)

        await event_queue.enqueue_event(new_agent_text_message(result))
        
    async def cancel(self, context: RequestContext, event_queue: EventQueue):
        raise Exception("Cancel not supported")
```

```python
import logging
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from agent_executor import RagAgentExecutor

def main():
    skill = AgentSkill(
        id="rag_skill",
        name="RAG Skill",
        description="Search knowledge base for project information",
        tags=["rag", "agent", "information"],
        examples=["What is project Astro and what tech is used in it?"],
    )
    agent_card = AgentCard(
        name="RAG Agent",
        description="A simple agent that searches the knowledge base for information",
        url="http://Geerts-MacBook-Air-2.local:9998/",
        defaultInputModes=["text"],
        defaultOutputModes=["text"],
        skills=[skill],
        version="1.0.0",
        capabilities=AgentCapabilities(),
    )
    request_handler = DefaultRequestHandler(
        agent_executor=RagAgentExecutor(),
        task_store=InMemoryTaskStore(),
    )
    server = A2AStarletteApplication(
        http_handler=request_handler,
        agent_card=agent_card,
    )
    uvicorn.run(server.build(), host="0.0.0.0", port=9998)
if __name__ == "__main__":
    main()
```