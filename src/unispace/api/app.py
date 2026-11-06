"""Фабрика FastAPI-приложения.

Запуск: uvicorn unispace.api.app:create_app --factory --reload
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .. import __version__
from ..ai.llm import LLMError, build_llm
from ..ai.tutor import Tutor
from ..config import Settings
from ..storage import NotFoundError, Store
from .deps import Container
from .routers import dashboard, deadlines, flashcards, materials, plans, progress, quizzes, tutor

API_PREFIX = "/api/v1"


def build_container(settings: Settings) -> Container:
    store = Store.load(settings.data_file) if settings.data_file else Store()
    llm = build_llm(settings)
    return Container(store=store, llm=llm, tutor=Tutor(llm), data_file=settings.data_file)


def create_app(settings: Settings | None = None, container: Container | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    app = FastAPI(
        title="UniSpace AI",
        version=__version__,
        description="Образовательная платформа: AI Tutor, планы, тесты, карточки, аналитика.",
    )
    app.state.container = container or build_container(settings)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(NotFoundError)
    async def _not_found(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": str(exc)})

    @app.exception_handler(LLMError)
    async def _llm_error(_: Request, exc: LLMError) -> JSONResponse:
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str | bool]:
        llm = app.state.container.llm
        return {"status": "ok", "version": __version__, "llm": llm.name, "offline": llm.offline}

    for module in (materials, tutor, plans, quizzes, flashcards, progress, deadlines, dashboard):
        app.include_router(module.router, prefix=API_PREFIX)
    return app
