from propadmin_runtime import create_app

from app.routes import router

app = create_app("rules")
app.include_router(router)
