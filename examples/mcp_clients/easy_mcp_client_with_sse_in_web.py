import asyncio

from mcp import ClientSession
from mcp.client.sse import sse_client


async def mcp_client():
    url = "http://localhost:9000/mcp/sse"  # SSE endpoint in standalone mode
    # SSE client uses Server-Sent Events for bidirectional communication
    async with sse_client(url) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            tools = await session.list_tools()
            print("Available tools:", [tools])
            # Call a tool (example: slack_post_message)
            res = await session.call_tool(
                name="slack_post_message",
                arguments={
                    "input_params": {
                        "channel": "C091SAB2F5Y",
                        "text": "This is Python script as a MCP client test",
                    },
                },
            )
            print("slack_post_message →", res.model_dump())


if __name__ == "__main__":
    asyncio.run(mcp_client())
