from propadmin_runtime import create_app

from app.voice import internal, webhooks

app = create_app("voice")
app.include_router(internal)
app.include_router(webhooks)
