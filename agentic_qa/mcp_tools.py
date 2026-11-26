"""MCP read-only tool gateway: allowlist, typed arguments and bounded responses."""
import asyncio
import json
import os
from typing import Any, Literal
from pydantic import BaseModel, Field

class ToolCall(BaseModel):
    name: Literal["get_defect_evidence", "get_test_coverage", "get_failure_diagnostics"]
    arguments: dict[str, Any] = Field(default_factory=dict)

class EvidenceQuery(BaseModel):
    release_id: str = Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")

class MCPToolGateway:
    def __init__(self, command: str, args: list[str] | None = None, *, env: dict[str, str] | None = None):
        if not isinstance(command, str) or not command:
            raise ValueError("MCP server executable must be configured by an operator")
        self.command = command
        self.args = args or []
        self.env = env or {}

    async def invoke(self, request: ToolCall) -> dict[str, Any]:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        query = EvidenceQuery.model_validate(request.arguments)
        params = StdioServerParameters(command=self.command, args=self.args, env={**os.environ, **self.env})
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                available = await session.list_tools()
                if request.name not in {tool.name for tool in available.tools}:
                    raise LookupError(f"MCP server does not expose {request.name}")
                result = await asyncio.wait_for(session.call_tool(request.name, query.model_dump()), timeout=30)
                if result.isError:
                    raise RuntimeError("MCP tool returned an error")
                if result.structuredContent is not None:
                    payload = result.structuredContent
                else:
                    texts = [block.text for block in result.content if getattr(block, "type", None) == "text"]
                    if len(texts) != 1:
                        raise ValueError("Expected exactly one JSON response")
                    payload = json.loads(texts[0])
                if not isinstance(payload, dict) or len(json.dumps(payload).encode()) > 262144:
                    raise ValueError("Invalid or oversized MCP evidence")
                return payload

    def call(self, request: ToolCall) -> dict[str, Any]:
        return asyncio.run(self.invoke(request))

def gateway_from_env() -> MCPToolGateway:
    command = os.getenv("QA_MCP_COMMAND", "").strip()
    if not command:
        raise ValueError("Set QA_MCP_COMMAND to the reviewed MCP server executable")
    args = json.loads(os.getenv("QA_MCP_ARGS_JSON", "[]"))
    if not isinstance(args, list) or any(not isinstance(a, str) for a in args):
        raise ValueError("QA_MCP_ARGS_JSON must contain a JSON array of strings")
    return MCPToolGateway(command, args)
