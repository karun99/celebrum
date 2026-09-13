"""Minimal Model Context Protocol (MCP) stdio server for Celebrum.

Exposes FR-5.1/5.2/5.3 tools to OpenWorker and any MCP client:
  * celebrum.recall
  * celebrum.simulate
  * celebrum.propose_guardrail
  * celebrum.approve_guardrail
  * celebrum.snapshot
  * celebrum.validate

Protocol: JSON-RPC 2.0 newline-delimited on stdio (the standard MCP transport).
"""

from __future__ import annotations

import json
import sys

from .engine import Celebrum

TOOLS = [
    {
        "name": "celebrum.recall",
        "description": "Recall memories (neurons) grounded in identity and evidence (ID-RAG + PGMem).",
        "inputSchema": {"type": "object", "properties": {
            "query": {"type": "string"},
            "k": {"type": "integer", "default": 5},
            "identity": {"type": "boolean", "default": True},
        }, "required": ["query"]},
    },
    {
        "name": "celebrum.simulate",
        "description": "Run a 'what if' scenario through the Persona Model; returns stance, reasoning and value conflicts.",
        "inputSchema": {"type": "object", "properties": {
            "scenario": {"type": "string"},
        }, "required": ["scenario"]},
    },
    {
        "name": "celebrum.propose_guardrail",
        "description": "Propose persona guardrail adaptations tiered by risk (low/medium/high).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "celebrum.approve_guardrail",
        "description": "Approve/reject a pending or active guardrail by id (high tier requires approval).",
        "inputSchema": {"type": "object", "properties": {
            "guardrail_id": {"type": "string"},
            "approve": {"type": "boolean"},
            "by": {"type": "string", "default": "openworker"},
        }, "required": ["guardrail_id"]},
    },
    {
        "name": "celebrum.snapshot",
        "description": "Return a snapshot of the whole brain (persona, memory, truth, guardrails, tensor).",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "celebrum.validate",
        "description": "Run the neural validation harness (BRIDGE, ID-RAG, PGMem, PTM, DPDP, performance).",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


class McpServer:
    def __init__(self, engine: Celebrum, out=None):
        self.engine = engine
        self.out = out or sys.stdout

    def _tools_call(self, name, args):
        if name == "celebrum.recall":
            return self.engine.recall(args.get("query"), k=args.get("k", 5),
                                      identity=args.get("identity", True), log=False)
        if name == "celebrum.simulate":
            return self.engine.simulate(args.get("scenario"))
        if name == "celebrum.propose_guardrail":
            return self.engine.propose()
        if name == "celebrum.approve_guardrail":
            gid = args.get("guardrail_id")
            if args.get("approve"):
                return self.engine.approve(gid, by=args.get("by", "openworker"))
            return self.engine.reject(gid, by=args.get("by", "openworker"))
        if name == "celebrum.snapshot":
            return self.engine.snapshot()
        if name == "celebrum.validate":
            return self.engine.validate()
        raise KeyError(f"unknown tool {name}")

    def handle(self, msg):
        if not isinstance(msg, dict):
            return None
        method = msg.get("method")
        idx = msg.get("id")
        if method == "initialize":
            return json.dumps({"jsonrpc": "2.0", "id": idx, "result": {
                "protocolVersion": "2025-06-18",
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "celebrum-mcp", "version": "0.1.0"},
            }})
        if method == "notifications/initialized":
            return None
        if method == "tools/list":
            return json.dumps({"jsonrpc": "2.0", "id": idx, "result": {"tools": TOOLS}})
        if method == "tools/call":
            params = msg.get("params", {}) or {}
            try:
                out = self._tools_call(params.get("name"), params.get("arguments", {}) or {})
                return json.dumps({"jsonrpc": "2.0", "id": idx, "result": {
                    "content": [{"type": "text", "text": _encode(out)}],
                    "isError": False,
                }})
            except Exception as e:  # noqa: BLE001
                return json.dumps({"jsonrpc": "2.0", "id": idx, "error": {
                    "code": -32000, "message": str(e)}})
        return json.dumps({"jsonrpc": "2.0", "id": idx, "error": {"code": -32601,
                                                                  "message": f"method not found: {method}"}})

    def serve_forever(self, stdin=None):
        inp = stdin or sys.stdin
        for line in inp:
            line = line.strip()
            if not line:
                continue
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            resp = self.handle(msg)
            if resp is not None:
                print(resp, flush=True)


def _encode(obj):
    try:
        return json.dumps(obj, ensure_ascii=False, default=str)
    except TypeError:
        return str(obj)


def main(argv=None):
    import argparse
    from .engine import default_home
    p = argparse.ArgumentParser(prog="celebrum mcp", description="Celebrum MCP stdio server")
    p.add_argument("--home", default=default_home())
    args = p.parse_args(argv or sys.argv[1:])
    engine = Celebrum(home=args.home)
    McpServer(engine).serve_forever()


if __name__ == "__main__":
    main()