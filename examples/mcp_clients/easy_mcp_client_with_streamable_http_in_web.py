import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


async def mcp_client():
    # 1. Specify your FastAPI MCP endpoint
    url = "http://localhost:9000/mcp/mcp"

    # 2. Establish a single HTTP connection (read, write, close_fn)
    async with streamablehttp_client(url) as (
        read_stream,
        write_stream,
        _close_fn,            # Can be called to close connection when stopping (usually not needed)
    ):
        # 3. Create MCP Session
        async with ClientSession(read_stream, write_stream) as session:
            # 4. Initialize handshake
            await session.initialize()

            # 5. List all available tools
            tools_resp = await session.list_tools()
            print("Available tools:", [t.name for t in tools_resp.tools])

            # 6. Call example tool (using 'slack_post_message' as example)
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
