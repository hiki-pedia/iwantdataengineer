"""ChartMaster FastAPI application."""

from __future__ import annotations

import os
import subprocess

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from chartmaster.api.schemas import DashboardResponse, HealthResponse, PriceCandleResponse
from chartmaster.api.service import DashboardService, VALID_RANGES


def create_app(service: DashboardService | None = None) -> FastAPI:
    application = FastAPI(title="ChartMaster API", version="0.1.0")
    application.state.dashboard_service = service or DashboardService()
    origins = [
        origin.strip()
        for origin in os.getenv(
            "CHARTMASTER_API_CORS_ORIGINS",
            "http://127.0.0.1:5173,http://localhost:5173,null",
        ).split(",")
        if origin.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @application.get("/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return application.state.dashboard_service.health()

    @application.get("/api/v1/dashboard", response_model=DashboardResponse)
    def dashboard() -> DashboardResponse:
        return application.state.dashboard_service.dashboard()

    @application.get("/api/v1/assets/{symbol}/prices", response_model=list[PriceCandleResponse])
    def prices(symbol: str, range_name: str = Query("5Y", alias="range")) -> list[PriceCandleResponse]:
        if range_name not in VALID_RANGES:
            raise HTTPException(status_code=422, detail=f"range must be one of {sorted(VALID_RANGES)}")
        try:
            return application.state.dashboard_service.prices(symbol, range_name)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=f"Unknown asset: {symbol}") from error
        except subprocess.CalledProcessError as error:
            raise HTTPException(status_code=503, detail="Server 2 storage is unavailable") from error
        except (OSError, ValueError, pd.errors.ParserError) as error:
            raise HTTPException(status_code=503, detail=str(error)) from error

    return application


app = create_app()
