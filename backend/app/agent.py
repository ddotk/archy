"""Claude agent loop with local tools + server-side web search."""
import os
from anthropic import Anthropic
from .tools import zoning, knowledge

MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
MAX_TURNS = 12

SYSTEM = """You are an architecture and interior-design assistant. Reply in the user's language (Thai by default).
Phase 1 workflow: collect location/site polygon, building type and requirements; determine the rules; run zoning_check; summarise buildable area, footprint and floor limits.
Rule sources, in priority order: (1) documents the user uploaded (list_knowledge / read_knowledge: law, fengshui), (2) research with web_search for the chosen country/locality, (3) config via get_zoning_config.
Always state which source each rule came from and flag placeholder or unverified values. Treat feng shui as optional design guidance, not law, and keep it separate from legal limits.
Results are a preliminary check only and do not replace a licensed architect or the local authority. Ask for missing inputs instead of guessing."""

TOOLS = [
    {"name": "list_knowledge", "description": "List user-uploaded rule documents (law, fengshui, other).",
     "input_schema": {"type": "object", "properties": {}}},
    {"name": "read_knowledge", "description": "Read text of an uploaded document.",
     "input_schema": {"type": "object", "properties": {"category": {"type": "string", "enum": list(knowledge.CATEGORIES)},
                      "name": {"type": "string"}}, "required": ["category", "name"]}},
    {"name": "get_zoning_config", "description": "Load the editable zoning config for a country code (e.g. TH).",
     "input_schema": {"type": "object", "properties": {"country_code": {"type": "string"}}, "required": ["country_code"]}},
    {"name": "zoning_check", "description": "Compute buildable area, footprint and floor limits for a site polygon after setbacks.",
     "input_schema": {"type": "object", "properties": {
         "coords": {"type": "array", "items": {"type": "array", "items": {"type": "number"}}, "description": "[[x,y],...] local metres or [lon,lat]"},
         "crs": {"type": "string", "enum": ["local_m", "lonlat"]},
         "front_edge_index": {"type": "integer", "description": "Edge i runs from point i to i+1"},
         "setbacks_m": {"type": "object", "properties": {"front": {"type": "number"}, "side": {"type": "number"}, "rear": {"type": "number"}}},
         "max_bcr": {"type": "number"}, "max_far": {"type": "number"},
         "max_height_m": {"type": "number"}, "floor_height_m": {"type": "number"}},
         "required": ["coords"]}},
    {"type": "web_search_20250305", "name": "web_search", "max_uses": 5},
]

LOCAL = {
    "list_knowledge": lambda **kw: knowledge.list_files(),
    "read_knowledge": lambda **kw: knowledge.read(**kw),
    "get_zoning_config": lambda **kw: zoning.get_zoning_config(**kw),
    "zoning_check": lambda **kw: zoning.compute_envelope(**kw),
}


def run(history: list[dict], country: str, client: Anthropic | None = None):
    """history: [{role, content(str)}]. Returns (reply_text, trace)."""
    client = client or Anthropic()
    system = SYSTEM + f"\nSelected country: {country}."
    messages = list(history)
    trace = []
    for _ in range(MAX_TURNS):
        r = client.messages.create(model=MODEL, max_tokens=2000, system=system, tools=TOOLS, messages=messages)
        messages.append({"role": "assistant", "content": r.content})
        if r.stop_reason == "pause_turn":
            continue
        if r.stop_reason != "tool_use":
            return "".join(b.text for b in r.content if b.type == "text"), trace
        results = []
        for b in r.content:
            if b.type == "tool_use":
                try:
                    out = LOCAL[b.name](**b.input)
                except Exception as e:  # report to the model, let it recover
                    out = {"error": str(e)}
                trace.append({"tool": b.name, "input": b.input})
                results.append({"type": "tool_result", "tool_use_id": b.id, "content": str(out)})
        messages.append({"role": "user", "content": results})
    return "Stopped: too many tool rounds.", trace
