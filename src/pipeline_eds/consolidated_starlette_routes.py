from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

from pipeline_eds.server.trend_server_eds import routes as trend_routes
from pipeline_eds.interface.web_gui.server import routes as gui_routes

routes = [
    *trend_routes,
    *gui_routes,
]

middleware = [
    Middleware(CORSMiddleware, allow_origins=["*"])
]

app = Starlette(
    routes=routes,
    middleware=middleware,
    debug=True,
)
