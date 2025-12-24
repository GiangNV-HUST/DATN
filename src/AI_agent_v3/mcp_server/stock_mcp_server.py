"""
Stock MCP Server
HTTP server cung cấp stock analysis tools via REST API (MCP-like protocol)
"""

import asyncio
import json
import logging
from aiohttp import web
from typing import Dict, Any
from stock_tools import StockToolsRegistry

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class StockMCPServer:
    """MCP Server for Stock Analysis Tools"""

    def __init__(self, host: str = "0.0.0.0", port: int = 5000):
        self.host = host
        self.port = port
        self.tools_registry = StockToolsRegistry()
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/health', self.handle_health)
        self.app.router.add_get('/tools', self.handle_list_tools)
        self.app.router.add_get('/tools/schema', self.handle_get_schemas)
        self.app.router.add_post('/tools/call', self.handle_call_tool)

    async def handle_health(self, request: web.Request) -> web.Response:
        """Health check endpoint"""
        return web.json_response({
            "status": "healthy",
            "server": "Stock MCP Server",
            "version": "3.0.0"
        })

    async def handle_list_tools(self, request: web.Request) -> web.Response:
        """Liệt kê tất cả tools available"""
        try:
            schemas = self.tools_registry.get_tool_schemas()
            tool_names = [tool["name"] for tool in schemas]

            return web.json_response({
                "success": True,
                "tools": tool_names,
                "count": len(tool_names)
            })
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)

    async def handle_get_schemas(self, request: web.Request) -> web.Response:
        """Trả về schemas của tất cả tools"""
        try:
            schemas = self.tools_registry.get_tool_schemas()

            return web.json_response({
                "success": True,
                "schemas": schemas,
                "count": len(schemas)
            })
        except Exception as e:
            logger.error(f"Error getting schemas: {e}")
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)

    async def handle_call_tool(self, request: web.Request) -> web.Response:
        """Execute một tool"""
        try:
            # Parse request body
            data = await request.json()
            tool_name = data.get("tool")
            arguments = data.get("arguments", {})

            if not tool_name:
                return web.json_response({
                    "success": False,
                    "error": "Missing 'tool' parameter"
                }, status=400)

            logger.info(f"📞 Tool call: {tool_name}({arguments})")

            # Execute tool
            result = await self.tools_registry.execute_tool(tool_name, arguments)

            return web.json_response(result)

        except json.JSONDecodeError:
            return web.json_response({
                "success": False,
                "error": "Invalid JSON in request body"
            }, status=400)
        except Exception as e:
            logger.error(f"Error calling tool: {e}", exc_info=True)
            return web.json_response({
                "success": False,
                "error": str(e)
            }, status=500)

    async def start(self):
        """Start MCP server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, self.host, self.port)
        await site.start()

        logger.info(f"")
        logger.info(f"{'='*60}")
        logger.info(f"🚀 Stock MCP Server Started!")
        logger.info(f"{'='*60}")
        logger.info(f"📍 URL: http://{self.host}:{self.port}")
        logger.info(f"🔧 Tools available: {len(self.tools_registry.get_tool_schemas())}")
        logger.info(f"")
        logger.info(f"📚 Endpoints:")
        logger.info(f"   GET  /health         - Health check")
        logger.info(f"   GET  /tools          - List all tools")
        logger.info(f"   GET  /tools/schema   - Get tool schemas")
        logger.info(f"   POST /tools/call     - Execute a tool")
        logger.info(f"")
        logger.info(f"💡 Example tool call:")
        logger.info(f"   curl -X POST http://localhost:{self.port}/tools/call \\")
        logger.info(f"     -H 'Content-Type: application/json' \\")
        logger.info(f"     -d '{{\"tool\": \"get_latest_price\", \"arguments\": {{\"ticker\": \"VCB\"}}}}'")
        logger.info(f"")
        logger.info(f"{'='*60}")

        # Keep server running
        try:
            await asyncio.Event().wait()
        finally:
            await runner.cleanup()


async def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Stock MCP Server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    args = parser.parse_args()

    server = StockMCPServer(host=args.host, port=args.port)
    await server.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n👋 Server stopped by user")
    except Exception as e:
        logger.error(f"❌ Server error: {e}", exc_info=True)
