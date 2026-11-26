"""Bounded safe calculator and read-only knowledge tools."""

import ast
import math
import operator

from pydantic import BaseModel, Field


class SearchArgs(BaseModel):
    query: str = Field(min_length=1, max_length=1000)
    top_k: int = Field(default=4, ge=1, le=6)


class ReadArgs(BaseModel):
    document_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    chunk_id: str | None = None


class CalculateArgs(BaseModel):
    expression: str = Field(min_length=1, max_length=160)


def calculate(expression: str) -> float:
    tree = ast.parse(expression, mode="eval")
    if len(list(ast.walk(tree))) > 40:
        raise ValueError("Expression too complex")
    ops = {
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.Pow: operator.pow,
    }

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            value = node.value
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand) * (1 if isinstance(node.op, ast.UAdd) else -1)
        elif isinstance(node, ast.BinOp) and type(node.op) in ops:
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10:
                raise ValueError("Exponent too large")
            value = ops[type(node.op)](left, right)
        else:
            raise ValueError("Only arithmetic is allowed")
        if not math.isfinite(value) or abs(value) > 1e15:
            raise ValueError("Result exceeds limit")
        return value

    return visit(tree.body)


class PortArgs(BaseModel):
    port: int = Field(strict=True, ge=1, le=65535)


class SystemArgs(BaseModel):
    pass


class Tools:
    def __init__(self, knowledge, *, allow_diagnostics: bool = False):
        self.knowledge = knowledge
        self.allow_diagnostics = allow_diagnostics
        self.schemas = {
            "search_knowledge": SearchArgs,
            "read_document": ReadArgs,
            "calculator": CalculateArgs,
        }
        if allow_diagnostics:
            self.schemas.update({"check_port": PortArgs, "system_info": SystemArgs})

    def definitions(self):
        descriptions = {
            "search_knowledge": "Search imported local documents for evidence.",
            "read_document": "Read an imported document or its specific chunk, bounded to 6000 characters.",
            "calculator": "Calculate a numeric expression using + - * / ** and parentheses.",
            "check_port": "Read-only query of local TCP listening processes for a port. Never stops processes.",
            "system_info": "Read-only OS, CPU, memory and disk information without machine identifiers.",
        }
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": descriptions[name],
                    "parameters": schema.model_json_schema(),
                },
            }
            for name, schema in self.schemas.items()
        ]

    async def run(self, name, arguments):
        if name not in self.schemas:
            raise ValueError("Unknown tool")
        args = self.schemas[name].model_validate(arguments)
        if name in {"check_port", "system_info"}:
            if not self.allow_diagnostics:
                raise ValueError("Local diagnostics are not authorized for this task")
            from app.agent.diagnostics import check_port, system_info

            return await check_port(args.port) if name == "check_port" else await system_info()
        if name == "calculator":
            return {"result": calculate(args.expression)}
        if name == "search_knowledge":
            return {"chunks": await self.knowledge.search(args.query, args.top_k)}
        doc = self.knowledge.preview(args.document_id)
        chunks = doc["chunks"]
        if args.chunk_id:
            chunks = [c for c in chunks if c["chunk_id"] == args.chunk_id]
            if not chunks:
                raise ValueError("Chunk does not belong to document")
        return {
            "title": doc["document"]["title"],
            "content": "\n\n".join(c["text"] for c in chunks)[:6000],
            "truncated": sum(len(c["text"]) for c in chunks) > 6000,
        }
