import uuid

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import (
    AgentCard,
    Message,
    MessageSendParams,
    Part,
    Role,
    SendStreamingMessageRequest,
    TextPart,
)
import click

PUBLIC_AGENT_CARD_PATH = "/.well-known/agent.json"


async def run_client(port: int, question: str) -> None:
    # Configure client with longer timeout to match agent execution time
    timeout = httpx.Timeout(200.0, read=200.0, write=30.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as httpx_client:
        # Initialize A2ACardResolver
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=f"http://localhost:{port}",
        )

        final_agent_card_to_use: AgentCard | None = None

        try:
            print(
                f"Fetching public agent card from: http://localhost:{port}{PUBLIC_AGENT_CARD_PATH}"
            )
            _public_card = await resolver.get_agent_card()
            print("Fetched public agent card")
            print(_public_card.model_dump_json(indent=2))

            final_agent_card_to_use = _public_card

        except Exception as e:
            print(f"Error fetching public agent card: {e}")
            raise RuntimeError("Failed to fetch public agent card")

        client = A2AClient(
            httpx_client=httpx_client, agent_card=final_agent_card_to_use
        )
        print("A2AClient initialized")

        message_payload = Message(
            role=Role.user,
            messageId=str(uuid.uuid4()),
            parts=[Part(root=TextPart(text=question))],
        )
        streaming_request = SendStreamingMessageRequest(
            id=str(uuid.uuid4()),
            params=MessageSendParams(
                message=message_payload,
            ),
        )
        print("Sending message")

        stream_response = client.send_message_streaming(streaming_request)

        async for chunk in stream_response:
            # Only print status updates and text responses
            chunk_dict = chunk.model_dump(mode='json', exclude_none=True)
            
            if 'result' in chunk_dict:
                result = chunk_dict['result']
                
                # Handle status updates
                if result.get('kind') == 'status-update':
                    status = result.get('status', {})
                    state = status.get('state', 'unknown')
                    
                    if 'message' in status:
                        message = status['message']
                        if 'parts' in message:
                            for part in message['parts']:
                                if part.get('kind') == 'text':
                                    print(f"[{state.upper()}] {part.get('text', '')}")
                    else:
                        print(f"[{state.upper()}]")
                
                # Handle artifact updates (contain actual responses)
                elif result.get('kind') == 'artifact-update':
                    artifact = result.get('artifact', {})
                    if 'parts' in artifact:
                        for part in artifact['parts']:
                            if part.get('kind') == 'text':
                                print(f"[RESPONSE] {part.get('text', '')}")
                
                # Handle initial task submission
                elif result.get('kind') == 'task':
                    print(f"[TASK SUBMITTED] ID: {result.get('id', 'unknown')}")
                    
                # Handle final completion
                elif result.get('final') is True:
                    print("[TASK COMPLETED]")


@click.command()
@click.option('--port', default=9996, help='Port of the agent.')
@click.option('--question', prompt='Your question', help='The question to ask the agent.')
def main(port: int, question: str) -> None:
    import asyncio
    asyncio.run(run_client(port, question))


if __name__ == "__main__":
    main()


 
