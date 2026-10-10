"""Run only v2.1.4 update methods against production, without starting the old app.

No school login, user config, scheduled task, installer launch, or real notification.
The downloaded installer is isolated in a temporary directory and removed on exit.
"""
import ast
import hashlib
import logging
import os
from pathlib import Path
import re
import subprocess
import tempfile
from unittest.mock import patch
from urllib.parse import unquote, urlparse

import requests

repo = Path(__file__).resolve().parents[1]
source = subprocess.check_output([
    "git", "show", "v2.1.4:RestoredSource/src/api.py",
], cwd=repo).decode("utf-8")
tree = ast.parse(source)
api_class = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "Api")
api_class.body = [node for node in api_class.body if isinstance(node, ast.FunctionDef)
                  and node.name in {"check_update", "download_update"}]
assert len(api_class.body) == 2
namespace = dict(os=os, re=re, requests=requests, unquote=unquote, urlparse=urlparse,
                 logger=logging.getLogger("legacy-update-test"))
exec(compile(ast.Module(body=[api_class], type_ignores=[]), "v2.1.4-update-methods", "exec"), namespace)
api = namespace["Api"]()
release = api.check_update()
assert release["status"] == "success"
assert release["data"]["version"] == "3.0.1"
with tempfile.TemporaryDirectory(prefix="classpush-update-check-") as temporary:
    original_expanduser = os.path.expanduser
    with patch.object(os.path, "expanduser", side_effect=lambda value: temporary if value == "~" else original_expanduser(value)):
        result = api.download_update()
    assert result["status"] == "success", result.get("message")
    downloaded = Path(result["data"]["file_path"])
    assert downloaded.is_relative_to(temporary)
    assert downloaded.stat().st_size == release["data"]["size_bytes"]
    assert hashlib.sha256(downloaded.read_bytes()).hexdigest() == release["data"]["sha256"]
print("Legacy v2.1.4 update methods passed: live 3.0.1 check, server installer download and SHA256. No app startup or installation.")
