"""Cloudflare Workers entry point for the Tempo Flask application."""

import os
from urllib.parse import urlparse

os.environ["SPORTCENTER_CLOUDFLARE_WORKER"] = "1"

from jinja2 import DictLoader
from workers import WorkerEntrypoint, wsgi

from app import app
from worker_templates import TEMPLATES

app.jinja_loader = DictLoader(TEMPLATES)


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        app.config["CLOUDFLARE_D1"] = True
        app.config["SECRET_KEY"] = self.env.SESSION_SECRET
        if urlparse(request.url).path.startswith("/static/"):
            return await self.env.ASSETS.fetch(request)
        return await wsgi.fetch(app, request, self.env)
