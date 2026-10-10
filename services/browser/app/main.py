from propadmin_runtime import create_app

from .browser import router

app = create_app("browser")
app.include_router(router)
