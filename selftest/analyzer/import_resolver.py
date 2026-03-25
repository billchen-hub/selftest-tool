"""Classify imports into mock/real categories."""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass, field


# Python stdlib module names (works on 3.9 without sys.stdlib_module_names)
_STDLIB_MODULES: set[str] | None = None


def _get_stdlib_modules() -> set[str]:
    global _STDLIB_MODULES
    if _STDLIB_MODULES is not None:
        return _STDLIB_MODULES

    if hasattr(sys, "stdlib_module_names"):
        _STDLIB_MODULES = sys.stdlib_module_names
    else:
        # Fallback for Python 3.9
        _STDLIB_MODULES = {
            "abc", "aifc", "argparse", "array", "ast", "asynchat", "asyncio",
            "asyncore", "atexit", "audioop", "base64", "bdb", "binascii",
            "binhex", "bisect", "builtins", "bz2", "calendar", "cgi", "cgitb",
            "chunk", "cmath", "cmd", "code", "codecs", "codeop", "collections",
            "colorsys", "compileall", "concurrent", "configparser", "contextlib",
            "contextvars", "copy", "copyreg", "cProfile", "crypt", "csv",
            "ctypes", "curses", "dataclasses", "datetime", "dbm", "decimal",
            "difflib", "dis", "distutils", "doctest", "email", "encodings",
            "enum", "errno", "faulthandler", "fcntl", "filecmp", "fileinput",
            "fnmatch", "formatter", "fractions", "ftplib", "functools", "gc",
            "getopt", "getpass", "gettext", "glob", "grp", "gzip", "hashlib",
            "heapq", "hmac", "html", "http", "idlelib", "imaplib", "imghdr",
            "imp", "importlib", "inspect", "io", "ipaddress", "itertools",
            "json", "keyword", "lib2to3", "linecache", "locale", "logging",
            "lzma", "mailbox", "mailcap", "marshal", "math", "mimetypes",
            "mmap", "modulefinder", "multiprocessing", "netrc", "nis", "nntplib",
            "numbers", "operator", "optparse", "os", "ossaudiodev", "parser",
            "pathlib", "pdb", "pickle", "pickletools", "pipes", "pkgutil",
            "platform", "plistlib", "poplib", "posix", "posixpath", "pprint",
            "profile", "pstats", "pty", "pwd", "py_compile", "pyclbr",
            "pydoc", "queue", "quopri", "random", "re", "readline", "reprlib",
            "resource", "rlcompleter", "runpy", "sched", "secrets", "select",
            "selectors", "shelve", "shlex", "shutil", "signal", "site",
            "smtpd", "smtplib", "sndhdr", "socket", "socketserver", "sqlite3",
            "ssl", "stat", "statistics", "string", "stringprep", "struct",
            "subprocess", "sunau", "symtable", "sys", "sysconfig", "syslog",
            "tabnanny", "tarfile", "telnetlib", "tempfile", "termios", "test",
            "textwrap", "threading", "time", "timeit", "tkinter", "token",
            "tokenize", "trace", "traceback", "tracemalloc", "tty", "turtle",
            "turtledemo", "types", "typing", "unicodedata", "unittest",
            "urllib", "uu", "uuid", "venv", "warnings", "wave", "weakref",
            "webbrowser", "winreg", "winsound", "wsgiref", "xdrlib", "xml",
            "xmlrpc", "zipapp", "zipfile", "zipimport", "zlib",
            "_thread",
        }
    return _STDLIB_MODULES


@dataclass
class ImportResult:
    all_imports: list[str]
    mock_targets: list[str]
    real_imports: list[str]


def resolve_imports(
    source: str,
    mock_modules: list[str],
    never_mock: list[str],
) -> ImportResult:
    """Classify imports from source code.

    Args:
        source: Python source code
        mock_modules: module names to always mock
        never_mock: module names to never mock (overrides mock_modules)

    Returns:
        ImportResult with classified imports
    """
    tree = ast.parse(source)
    stdlib = _get_stdlib_modules()
    all_imports: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level = alias.name.split(".")[0]
                if top_level not in all_imports:
                    all_imports.append(top_level)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top_level = node.module.split(".")[0]
                if top_level not in all_imports:
                    all_imports.append(top_level)

    mock_targets = []
    real_imports = []

    for mod in all_imports:
        if mod in never_mock:
            real_imports.append(mod)
        elif mod in mock_modules:
            mock_targets.append(mod)
        elif mod in stdlib:
            real_imports.append(mod)
        else:
            # Unknown modules default to real (user can add to mock_modules)
            real_imports.append(mod)

    return ImportResult(
        all_imports=all_imports,
        mock_targets=mock_targets,
        real_imports=real_imports,
    )
