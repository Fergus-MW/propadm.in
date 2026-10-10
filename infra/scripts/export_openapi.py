"""Export the gateway schema offline for deterministic client generation in CI."""

import json
import os
import sys
from pathlib import Path

os.environ["EMBEDDING_PROVIDER"] = "local"
os.environ["EXTRACTION_PROVIDER"] = "local"


def main():
    from propadmin_core import Store
    from propadmin_runtime import create_app
    from propadmin_runtime.config import Settings

    app = create_app("api", store=Store(), settings=Settings(mode="local"), seed=False)
    output = Path(sys.argv[1] if len(sys.argv) > 1 else ".artifacts/openapi.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), sort_keys=True) + "\n")
    print(f"Exported API contract to {output}")


if __name__ == "__main__":
    main()
