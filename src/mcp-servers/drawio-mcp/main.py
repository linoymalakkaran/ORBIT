"""
Phase 09 – G08: Draw.io MCP Server
FastAPI service providing structured diagram generation and manipulation
tools callable by ORBIT Architecture Agent.
"""
import os
import re
import textwrap
import xml.etree.ElementTree as ET
from typing import Any
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

LITELLM_URL   = os.environ.get("LITELLM_URL",   "http://litellm-gateway.litellm.svc:4000")
LITELLM_KEY   = os.environ.get("LITELLM_API_KEY", "")
DEFAULT_MODEL = os.environ.get("DRAWIO_MODEL",   "gpt-4o")

app = FastAPI(title="Draw.io MCP", version="1.0.0")

# ── Models ────────────────────────────────────────────────────────────────────

class Component(BaseModel):
    name: str
    type: str  # service | database | queue | gateway | cache | external
    description: str = ""


class Relationship(BaseModel):
    from_: str
    to: str
    label: str = ""
    type: str = "http"  # http | event | database | grpc | mq


class GenerateArchitectureDiagramRequest(BaseModel):
    components: list[Component]
    relationships: list[Relationship]
    diagram_type: str = "component"  # component | deployment | c4-context


class Actor(BaseModel):
    name: str
    type: str = "actor"  # actor | system | database


class Message(BaseModel):
    from_: str
    to: str
    label: str
    sequence_number: int = 1


class GenerateSequenceDiagramRequest(BaseModel):
    actors: list[Actor]
    messages: list[Message]
    title: str = "Sequence Diagram"


class ExportDiagramRequest(BaseModel):
    xml: str
    format: str = "svg"  # svg | png (png requires draw.io CLI)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health/live")
async def live():
    return {"status": "healthy"}


@app.get("/health/ready")
async def ready():
    return {"status": "healthy"}


# ── LLM helper ───────────────────────────────────────────────────────────────

async def _llm(prompt: str) -> str:
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"{LITELLM_URL}/chat/completions",
            headers={"Authorization": f"Bearer {LITELLM_KEY}"},
            json={
                "model": DEFAULT_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are an expert draw.io XML generator. "
                            "Always return ONLY valid draw.io XML wrapped in <mxGraphModel> tags. "
                            "No markdown, no explanation, no code fences."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.1,
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()


# ── Tool 1: generate_architecture_diagram ────────────────────────────────────

@app.post("/tools/generate_architecture_diagram")
async def generate_architecture_diagram(req: GenerateArchitectureDiagramRequest) -> dict[str, Any]:
    """Generates a draw.io XML component/deployment diagram from components and relationships."""
    components_text = "\n".join(
        f"  - {c.name} (type={c.type}): {c.description}" for c in req.components
    )
    relationships_text = "\n".join(
        f"  - {r.from_} --[{r.type}:{r.label}]--> {r.to}" for r in req.relationships
    )
    prompt = textwrap.dedent(f"""
        Generate a draw.io {req.diagram_type} diagram XML for the following architecture.

        Components:
        {components_text}

        Relationships:
        {relationships_text}

        Rules:
        - Use mxGraphModel with child mxCell elements
        - Style: services as rounded rectangles (#dae8fc fill), databases as cylinders (#d5e8d4 fill),
          queues as parallelograms (#fff2cc fill), gateways as hexagons (#f8cecc fill),
          external systems as dashed rectangles (#f5f5f5 fill)
        - Add directional arrows for relationships with the label on the edge
        - Space elements evenly with x/y coordinates
        - Set page=1, grid=1, gridSize=10
        Return ONLY the mxGraphModel XML.
    """)
    xml_content = await _llm(prompt)
    return {"diagram_type": req.diagram_type, "xml": xml_content}


# ── Tool 2: generate_sequence_diagram ────────────────────────────────────────

@app.post("/tools/generate_sequence_diagram")
async def generate_sequence_diagram(req: GenerateSequenceDiagramRequest) -> dict[str, Any]:
    """Generates a draw.io XML sequence diagram from actors and messages."""
    actors_text = "\n".join(f"  - {a.name} ({a.type})" for a in req.actors)
    messages_text = "\n".join(
        f"  {m.sequence_number}. {m.from_} → {m.to}: {m.label}" for m in sorted(req.messages, key=lambda x: x.sequence_number)
    )
    prompt = textwrap.dedent(f"""
        Generate a draw.io sequence diagram XML titled "{req.title}".

        Actors:
        {actors_text}

        Messages (in sequence order):
        {messages_text}

        Rules:
        - Use mxGraphModel with mxCell elements
        - Actors as vertical lifelines (rectangles at top, dashed vertical lines extending down)
        - Messages as horizontal arrows between lifelines, labeled with sequence number and message text
        - Use activation boxes (thin rectangles on lifelines) for synchronous calls
        - Return arrows for responses (dashed arrows)
        Return ONLY the mxGraphModel XML.
    """)
    xml_content = await _llm(prompt)
    return {"title": req.title, "xml": xml_content}


# ── Tool 3: export_diagram ────────────────────────────────────────────────────

@app.post("/tools/export_diagram")
async def export_diagram(req: ExportDiagramRequest) -> dict[str, Any]:
    """
    Exports draw.io XML as SVG (inline) or PNG (requires draw.io CLI in container).
    For SVG: returns the SVG XML inline.
    For PNG: invokes draw.io CLI and returns base64.
    """
    if req.format == "svg":
        # Inline SVG: return the XML as-is with SVG wrapper hint
        return {
            "format": "svg",
            "note": "Render this XML in draw.io viewer or embed in HTML",
            "content": req.xml,
        }
    elif req.format == "png":
        import subprocess, base64, tempfile, os as _os
        with tempfile.NamedTemporaryFile(suffix=".drawio", delete=False, mode="w") as f:
            f.write(req.xml)
            tmp_in = f.name
        tmp_out = tmp_in.replace(".drawio", ".png")
        try:
            subprocess.run(
                ["drawio", "--export", "--format", "png", "--output", tmp_out, tmp_in],
                check=True,
                timeout=30,
            )
            with open(tmp_out, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            return {"format": "png", "base64": encoded}
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            raise HTTPException(500, f"draw.io CLI export failed: {e}")
        finally:
            for p in [tmp_in, tmp_out]:
                if _os.path.exists(p):
                    _os.unlink(p)
    else:
        raise HTTPException(400, f"Unsupported format '{req.format}'. Use 'svg' or 'png'.")


# ── Tool 4: validate_diagram ──────────────────────────────────────────────────

@app.post("/tools/validate_diagram")
async def validate_diagram(xml: str) -> dict[str, Any]:
    """Validates that the provided string is well-formed draw.io XML."""
    errors = []
    try:
        root = ET.fromstring(xml)
        if root.tag != "mxGraphModel":
            errors.append(f"Root element must be 'mxGraphModel', got '{root.tag}'")
        cells = root.findall(".//mxCell")
        if not cells:
            errors.append("No mxCell elements found in diagram")
        # Check required attribute on cells
        for i, cell in enumerate(cells[:10]):  # sample first 10
            if "id" not in cell.attrib:
                errors.append(f"mxCell at index {i} missing 'id' attribute")
    except ET.ParseError as e:
        errors.append(f"XML parse error: {e}")

    return {"valid": len(errors) == 0, "errors": errors}
