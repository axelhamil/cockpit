import json
import sys
from pathlib import Path

manifest_path = Path(".claude-plugin/plugin.json")
manifest = json.loads(manifest_path.read_text())
manifest["version"] = sys.argv[1]
manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
