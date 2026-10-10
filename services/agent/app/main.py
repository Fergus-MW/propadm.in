from propadmin_runtime import create_app

from .managed import router

app = create_app("agent")
app.include_router(router)
