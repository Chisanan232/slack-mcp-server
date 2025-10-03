import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def mcp_client():
    url = "http://localhost:9000/mcp"  # Correct endpoint for streamable HTTP
    # streamablehttp_client uses a single HTTP connection for bidirectional communication
    async with streamablehttp_client(url) as (
        read_stream,
        write_stream,
        _close_fn,            # Third value, can be named _ or close_fn
    ):
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
