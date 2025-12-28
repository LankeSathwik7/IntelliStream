"""Tool definitions for agent tool calling."""

import json
import math
import re
from typing import Dict, List, Any, Callable
from datetime import datetime, timezone


class ToolRegistry:
    """Registry of available tools for agents."""

    def __init__(self):
        self.tools: Dict[str, Dict] = {}
        self._register_default_tools()

    def register(
        self,
        name: str,
        description: str,
        parameters: Dict,
        handler: Callable
    ):
        """Register a new tool."""
        self.tools[name] = {
            "name": name,
            "description": description,
            "parameters": parameters,
            "handler": handler
        }

    def get_tool(self, name: str) -> Dict:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_all_schemas(self) -> List[Dict]:
        """Get OpenAI-compatible tool schemas for all tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["parameters"]
                }
            }
            for tool in self.tools.values()
        ]

    async def execute(self, name: str, arguments: Dict) -> Any:
        """Execute a tool with given arguments."""
        tool = self.tools.get(name)
        if not tool:
            return {"error": f"Tool '{name}' not found"}

        try:
            handler = tool["handler"]
            if callable(handler):
                result = handler(**arguments)
                return result
            return {"error": "Tool handler not callable"}
        except Exception as e:
            return {"error": str(e)}

    def _register_default_tools(self):
        """Register built-in tools."""

        # Calculator tool
        self.register(
            name="calculator",
            description="Perform mathematical calculations. Supports basic arithmetic, trigonometry, and common math functions.",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)')"
                    }
                },
                "required": ["expression"]
            },
            handler=self._calculator
        )

        # Date/Time tool
        self.register(
            name="datetime",
            description="Get current date and time information.",
            parameters={
                "type": "object",
                "properties": {
                    "timezone": {
                        "type": "string",
                        "description": "Timezone name (e.g., 'UTC', 'US/Eastern'). Default: UTC"
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format: 'full', 'date', 'time', 'iso'. Default: 'full'"
                    }
                },
                "required": []
            },
            handler=self._datetime
        )

        # Unit converter tool
        self.register(
            name="unit_converter",
            description="Convert between units of measurement.",
            parameters={
                "type": "object",
                "properties": {
                    "value": {
                        "type": "number",
                        "description": "The value to convert"
                    },
                    "from_unit": {
                        "type": "string",
                        "description": "Source unit (e.g., 'km', 'miles', 'celsius', 'fahrenheit')"
                    },
                    "to_unit": {
                        "type": "string",
                        "description": "Target unit"
                    }
                },
                "required": ["value", "from_unit", "to_unit"]
            },
            handler=self._unit_converter
        )

        # Text analysis tool
        self.register(
            name="text_stats",
            description="Analyze text and return statistics.",
            parameters={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Text to analyze"
                    }
                },
                "required": ["text"]
            },
            handler=self._text_stats
        )

        # JSON validator tool
        self.register(
            name="json_validator",
            description="Validate and format JSON data.",
            parameters={
                "type": "object",
                "properties": {
                    "json_string": {
                        "type": "string",
                        "description": "JSON string to validate"
                    }
                },
                "required": ["json_string"]
            },
            handler=self._json_validator
        )

    def _calculator(self, expression: str) -> Dict:
        """Safe mathematical expression evaluator."""
        try:
            # Define safe functions
            safe_dict = {
                "abs": abs,
                "round": round,
                "min": min,
                "max": max,
                "sum": sum,
                "pow": pow,
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pi": math.pi,
                "e": math.e,
                "floor": math.floor,
                "ceil": math.ceil,
            }

            # Clean expression
            expression = expression.replace("^", "**")

            # Evaluate safely
            result = eval(expression, {"__builtins__": {}}, safe_dict)

            return {
                "expression": expression,
                "result": result,
                "formatted": f"{expression} = {result}"
            }

        except Exception as e:
            return {"error": f"Calculation error: {str(e)}"}

    def _datetime(
        self,
        tz: str = "UTC",
        format: str = "full"
    ) -> Dict:
        """Get current date/time."""
        try:
            now = datetime.now(timezone.utc)

            if format == "iso":
                formatted = now.isoformat()
            elif format == "date":
                formatted = now.strftime("%Y-%m-%d")
            elif format == "time":
                formatted = now.strftime("%H:%M:%S")
            else:  # full
                formatted = now.strftime("%Y-%m-%d %H:%M:%S UTC")

            return {
                "datetime": formatted,
                "timestamp": now.timestamp(),
                "year": now.year,
                "month": now.month,
                "day": now.day,
                "hour": now.hour,
                "minute": now.minute,
                "weekday": now.strftime("%A")
            }

        except Exception as e:
            return {"error": str(e)}

    def _unit_converter(
        self,
        value: float,
        from_unit: str,
        to_unit: str
    ) -> Dict:
        """Convert between units."""
        conversions = {
            # Length
            ("km", "miles"): lambda x: x * 0.621371,
            ("miles", "km"): lambda x: x * 1.60934,
            ("m", "ft"): lambda x: x * 3.28084,
            ("ft", "m"): lambda x: x * 0.3048,
            ("cm", "inches"): lambda x: x * 0.393701,
            ("inches", "cm"): lambda x: x * 2.54,

            # Temperature
            ("celsius", "fahrenheit"): lambda x: (x * 9/5) + 32,
            ("fahrenheit", "celsius"): lambda x: (x - 32) * 5/9,
            ("celsius", "kelvin"): lambda x: x + 273.15,
            ("kelvin", "celsius"): lambda x: x - 273.15,

            # Weight
            ("kg", "lbs"): lambda x: x * 2.20462,
            ("lbs", "kg"): lambda x: x * 0.453592,
            ("g", "oz"): lambda x: x * 0.035274,
            ("oz", "g"): lambda x: x * 28.3495,

            # Volume
            ("liters", "gallons"): lambda x: x * 0.264172,
            ("gallons", "liters"): lambda x: x * 3.78541,
        }

        key = (from_unit.lower(), to_unit.lower())

        if key in conversions:
            result = conversions[key](value)
            return {
                "original": f"{value} {from_unit}",
                "converted": f"{result:.4f} {to_unit}",
                "value": result
            }
        else:
            return {"error": f"Conversion from {from_unit} to {to_unit} not supported"}

    def _text_stats(self, text: str) -> Dict:
        """Analyze text statistics."""
        words = text.split()
        sentences = re.split(r'[.!?]+', text)
        sentences = [s for s in sentences if s.strip()]

        return {
            "character_count": len(text),
            "word_count": len(words),
            "sentence_count": len(sentences),
            "paragraph_count": text.count('\n\n') + 1,
            "average_word_length": sum(len(w) for w in words) / len(words) if words else 0,
            "average_sentence_length": len(words) / len(sentences) if sentences else 0,
        }

    def _json_validator(self, json_string: str) -> Dict:
        """Validate and format JSON."""
        try:
            parsed = json.loads(json_string)
            formatted = json.dumps(parsed, indent=2)
            return {
                "valid": True,
                "formatted": formatted,
                "type": type(parsed).__name__
            }
        except json.JSONDecodeError as e:
            return {
                "valid": False,
                "error": str(e),
                "position": e.pos
            }


# Singleton instance
tool_registry = ToolRegistry()
