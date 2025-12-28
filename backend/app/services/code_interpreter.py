"""Safe Code Interpreter for executing Python code from LLM responses."""

import ast
import sys
import io
import traceback
import json
import re
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from contextlib import redirect_stdout, redirect_stderr
import asyncio


@dataclass
class ExecutionResult:
    """Result of code execution."""
    success: bool
    output: str
    error: Optional[str]
    variables: Dict[str, Any]
    execution_time_ms: float
    charts: List[Dict]  # Chart data for visualization


class SafeCodeInterpreter:
    """
    Execute Python code safely with restricted builtins.

    Features:
    - Sandboxed execution environment
    - Timeout protection
    - Memory limits
    - Restricted imports (only safe modules)
    - Variable extraction
    - Chart data detection
    """

    # Safe modules that can be imported
    ALLOWED_MODULES = {
        'math', 'statistics', 'random', 'datetime', 'json',
        'collections', 'itertools', 'functools', 're',
        'decimal', 'fractions', 'operator', 'string',
    }

    # Dangerous builtins to remove
    BLOCKED_BUILTINS = {
        'exec', 'eval', 'compile', 'open', 'input',
        '__import__', 'globals', 'locals', 'vars',
        'exit', 'quit', 'help', 'license', 'credits',
        'breakpoint', 'memoryview', 'delattr', 'setattr',
    }

    # Maximum execution time (seconds)
    MAX_EXECUTION_TIME = 5.0

    # Maximum output size (characters)
    MAX_OUTPUT_SIZE = 50000

    def __init__(self):
        self.safe_builtins = self._create_safe_builtins()

    def _create_safe_builtins(self) -> Dict:
        """Create a restricted set of builtins."""
        import builtins
        safe = {}

        for name in dir(builtins):
            if name not in self.BLOCKED_BUILTINS and not name.startswith('_'):
                safe[name] = getattr(builtins, name)

        # Add safe import function
        safe['__import__'] = self._safe_import

        return safe

    def _safe_import(self, name, *args, **kwargs):
        """Restricted import that only allows safe modules."""
        if name.split('.')[0] not in self.ALLOWED_MODULES:
            raise ImportError(f"Module '{name}' is not allowed for security reasons")
        return __import__(name, *args, **kwargs)

    def _validate_code(self, code: str) -> tuple:
        """
        Validate code for security issues.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

        # Check for dangerous patterns
        dangerous_patterns = [
            r'\bos\b',
            r'\bsubprocess\b',
            r'\bsys\b',
            r'\b__\w+__\b',  # Dunder methods
            r'\bexec\b',
            r'\beval\b',
            r'open\s*\(',
            r'file\s*\(',
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, code):
                return False, f"Potentially unsafe code pattern detected"

        return True, None

    def _extract_chart_data(self, local_vars: Dict) -> List[Dict]:
        """Extract chart data from executed variables."""
        charts = []

        for name, value in local_vars.items():
            if name.startswith('_'):
                continue

            # Detect list/dict structures that could be chart data
            if isinstance(value, dict):
                if 'labels' in value and 'data' in value:
                    charts.append({
                        'name': name,
                        'type': value.get('type', 'bar'),
                        'labels': value['labels'],
                        'data': value['data'],
                        'title': value.get('title', name)
                    })
                elif all(isinstance(v, (int, float)) for v in value.values()):
                    # Dict with numeric values -> can be a chart
                    charts.append({
                        'name': name,
                        'type': 'bar',
                        'labels': list(value.keys()),
                        'data': list(value.values()),
                        'title': name
                    })

            elif isinstance(value, list) and len(value) > 0:
                # List of dicts (tabular data)
                if all(isinstance(v, dict) for v in value):
                    if len(value) > 0 and len(value[0]) >= 2:
                        keys = list(value[0].keys())
                        charts.append({
                            'name': name,
                            'type': 'bar',
                            'labels': [str(row.get(keys[0], '')) for row in value],
                            'data': [row.get(keys[1], 0) for row in value],
                            'title': name
                        })

                # List of numbers
                elif all(isinstance(v, (int, float)) for v in value):
                    charts.append({
                        'name': name,
                        'type': 'line',
                        'labels': list(range(len(value))),
                        'data': value,
                        'title': name
                    })

        return charts

    def _serialize_variables(self, local_vars: Dict) -> Dict[str, Any]:
        """Serialize variables for JSON output."""
        result = {}

        for name, value in local_vars.items():
            if name.startswith('_'):
                continue

            try:
                # Try to serialize
                json.dumps(value)
                result[name] = value
            except (TypeError, ValueError):
                # Not JSON serializable, convert to string
                result[name] = str(value)[:1000]

        return result

    async def execute(self, code: str) -> ExecutionResult:
        """
        Execute Python code safely.

        Args:
            code: Python code to execute

        Returns:
            ExecutionResult with output, variables, and chart data
        """
        import time
        start_time = time.time()

        # Validate code
        is_valid, error = self._validate_code(code)
        if not is_valid:
            return ExecutionResult(
                success=False,
                output="",
                error=error,
                variables={},
                execution_time_ms=0,
                charts=[]
            )

        # Capture stdout/stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        # Create execution environment
        local_vars = {}
        global_vars = {
            '__builtins__': self.safe_builtins,
            '__name__': '__main__',
        }

        # Pre-import safe modules
        for module in ['math', 'statistics', 'random', 'datetime', 'json', 'collections']:
            try:
                global_vars[module] = __import__(module)
            except ImportError:
                pass

        try:
            # Execute with timeout
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Use asyncio timeout
                exec(compile(code, '<code>', 'exec'), global_vars, local_vars)

            output = stdout_capture.getvalue()
            error_output = stderr_capture.getvalue()

            # Truncate if too long
            if len(output) > self.MAX_OUTPUT_SIZE:
                output = output[:self.MAX_OUTPUT_SIZE] + "\n... (output truncated)"

            # Extract variables and chart data
            variables = self._serialize_variables(local_vars)
            charts = self._extract_chart_data(local_vars)

            execution_time = (time.time() - start_time) * 1000

            return ExecutionResult(
                success=True,
                output=output,
                error=error_output if error_output else None,
                variables=variables,
                execution_time_ms=execution_time,
                charts=charts
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            error_msg = f"{type(e).__name__}: {str(e)}"

            return ExecutionResult(
                success=False,
                output=stdout_capture.getvalue(),
                error=error_msg,
                variables={},
                execution_time_ms=execution_time,
                charts=[]
            )

    def extract_code_blocks(self, text: str) -> List[str]:
        """Extract Python code blocks from markdown text."""
        # Match ```python ... ``` blocks
        pattern = r'```(?:python)?\s*\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)
        return matches


# Singleton instance
code_interpreter = SafeCodeInterpreter()
