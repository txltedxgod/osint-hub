"""Single shared Jinja2 templates instance."""
from __future__ import annotations

from fastapi.templating import Jinja2Templates

from app import __version__

templates = Jinja2Templates(directory="app/templates")
templates.env.globals["app_name"] = "OSINT Hub"
templates.env.globals["app_version"] = __version__
