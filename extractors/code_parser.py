import ast
import re
from pathlib import Path
from typing import Dict, Any, List
from utils.logger import setup_logger

logger = setup_logger("CodeParser")

class CodeParser:
    """Parses source code files using Python AST for .py and regex for other languages."""

    @classmethod
    def _parse_python_ast(cls, code_content: str) -> Dict[str, Any]:
        """Extracts classes, functions, docstrings, and imports using AST."""
        classes = []
        functions = []
        imports = []
        docstrings = []

        try:
            tree = ast.parse(code_content)
            module_doc = ast.get_docstring(tree)
            if module_doc:
                docstrings.append(module_doc)

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    doc = ast.get_docstring(node) or ""
                    classes.append({"name": node.name, "docstring": doc, "lineno": node.lineno})
                    if doc:
                        docstrings.append(doc)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    doc = ast.get_docstring(node) or ""
                    args = [arg.arg for arg in node.args.args]
                    functions.append({
                        "name": node.name,
                        "args": args,
                        "docstring": doc,
                        "lineno": node.lineno
                    })
                    if doc:
                        docstrings.append(doc)
                elif isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    mod = node.module or ""
                    for alias in node.names:
                        imports.append(f"{mod}.{alias.name}")

            # Also extract inline comments with regex
            comments = re.findall(r"#.*$", code_content, flags=re.MULTILINE)

            # Build enriched searchable representation
            summary_lines = []
            if docstrings:
                summary_lines.append("Docstrings:\n" + "\n".join(docstrings))
            if classes:
                summary_lines.append("Classes: " + ", ".join([c["name"] for c in classes]))
            if functions:
                func_strs = [f"{f['name']}({', '.join(f['args'])})" for f in functions]
                summary_lines.append("Functions: " + ", ".join(func_strs))
            if imports:
                summary_lines.append("Imports: " + ", ".join(imports[:30]))

            rich_text = f"{code_content}\n\n=== Code Structure Summary ===\n" + "\n".join(summary_lines)

            return {
                "text": rich_text,
                "language": "python",
                "classes": classes,
                "functions": functions,
                "imports": imports,
                "docstrings": docstrings,
                "comments_count": len(comments)
            }
        except SyntaxError as e:
            logger.warning(f"AST parsing syntax error: {e}. Falling back to regex.")
            return cls._parse_generic_code(code_content, language="python")

    @classmethod
    def _parse_generic_code(cls, code_content: str, language: str) -> Dict[str, Any]:
        """Extracts functions, classes, and comments using regex patterns."""
        # Function regex patterns for common languages (JS, TS, Java, C++, Go, etc.)
        func_patterns = [
            r"(?:function|def|func|fn)\s+([a-zA-Z0-9_]+)\s*\(",
            r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+([a-zA-Z0-9_]+)\s*\([^)]*\)\s*\{",
            r"const\s+([a-zA-Z0-9_]+)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>",
            r"([a-zA-Z0-9_]+)\s*:\s*function\s*\(",
        ]
        class_patterns = [
            r"(?:class|struct|interface|trait|enum)\s+([a-zA-Z0-9_]+)",
        ]
        import_patterns = [
            r"(?:import|require|include|use)\s+['\"]?([a-zA-Z0-9_\.\/\-]+)['\"]?",
        ]

        found_functions = []
        for pat in func_patterns:
            found_functions.extend(re.findall(pat, code_content))

        found_classes = []
        for pat in class_patterns:
            found_classes.extend(re.findall(pat, code_content))

        found_imports = []
        for pat in import_patterns:
            found_imports.extend(re.findall(pat, code_content))

        # Extract comments (//, /* */, #, --)
        comments = re.findall(r"(?://.*$|/\*[\s\S]*?\*/|#.*$|--.*$)", code_content, flags=re.MULTILINE)

        summary_lines = []
        if found_classes:
            summary_lines.append("Classes/Types: " + ", ".join(list(set(found_classes))))
        if found_functions:
            summary_lines.append("Functions: " + ", ".join(list(set(found_functions))))
        if found_imports:
            summary_lines.append("Dependencies: " + ", ".join(list(set(found_imports))[:20]))

        rich_text = f"{code_content}\n\n=== Code Symbols ===\n" + "\n".join(summary_lines)

        return {
            "text": rich_text,
            "language": language,
            "classes": [{"name": c} for c in set(found_classes)],
            "functions": [{"name": f} for f in set(found_functions)],
            "imports": list(set(found_imports)),
            "comments_count": len(comments)
        }

    @classmethod
    def parse(cls, file_path: str) -> Dict[str, Any]:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Source code file not found: {file_path}")

        ext = path.suffix.lower()
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            code_content = f.read()

        if ext == ".py":
            result = cls._parse_python_ast(code_content)
        else:
            lang_map = {
                ".js": "javascript", ".ts": "typescript", ".jsx": "react_jsx",
                ".tsx": "react_tsx", ".java": "java", ".c": "c", ".cpp": "cpp",
                ".h": "c_header", ".go": "go", ".rs": "rust", ".rb": "ruby",
                ".php": "php", ".sql": "sql", ".sh": "shell", ".html": "html",
                ".css": "css", ".json": "json", ".yaml": "yaml", ".yml": "yaml",
                ".md": "markdown"
            }
            lang = lang_map.get(ext, "code")
            result = cls._parse_generic_code(code_content, language=lang)

        result["metadata"] = {
            "language": result.get("language", "code"),
            "lines_of_code": len(code_content.splitlines()),
            "classes_count": len(result.get("classes", [])),
            "functions_count": len(result.get("functions", []))
        }
        return result
