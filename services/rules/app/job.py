"""Cloud Run Job entrypoint: `python -m app.job` runs a full recompute and layout."""

import json

from app.main import app
from app.routes import full_recompute

if __name__ == "__main__":
    print(json.dumps(full_recompute(app.state.store)))
