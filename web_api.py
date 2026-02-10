"""
REST API для расчёта длины патч-кордов.
Запуск: uvicorn web_api:app --reload
Или: python web_api.py
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, List

from cable_calculator import (
    ServerLocation,
    DataCenterCableConfig,
    calculate_patch_cord_breakdown,
)
from rack_plan import (
    RackInfo,
    load_rack_plan,
    get_rack_index_by_code,
    generate_default_rack_plan,
)

app = FastAPI(
    title="Калькулятор патч-кордов",
    description="API для расчёта длины патч-кордов в дата-центре",
    version="1.0.0"
)

# Разрешаем CORS для веб-интерфейса
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретные домены
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ServerRequest(BaseModel):
    """Запрос с параметрами сервера."""
    rack_code: str = Field(..., description="Код стойки (например, '02b05')")
    unit: int = Field(..., ge=1, le=50, description="Номер юнита (1-50)")
    hostname: Optional[str] = Field(None, description="Опциональный хостнейм сервера")


class CalculationRequest(BaseModel):
    """Запрос на расчёт длины патч-корда."""
    server_a: ServerRequest
    server_b: ServerRequest
    config: Optional[dict] = Field(None, description="Опциональные параметры конфигурации")


class CalculationResponse(BaseModel):
    """Ответ с результатом расчёта с детализацией."""

    length_m: float = Field(..., description="Расчётная длина по формулам, м (до округления)")
    recommended_patch_cord_m: float = Field(..., description="Рекомендуемый патч-корд из списка (1, 1.5, 2, 3, 5, 7.5, 10, 15, 20 м)")
    same_rack: bool = Field(..., description="Находятся ли серверы в одной стойке")

    # Детализация по сегментам
    vertical_a_m: float = Field(..., description="Вертикальный участок от сервера A до кабель-канала, м")
    vertical_b_m: float = Field(..., description="Вертикальный участок от сервера B до кабель-канала, м")
    horizontal_m: float = Field(..., description="Горизонтальный участок по кабель-каналу, м")
    raw_total_m: float = Field(..., description="Суммарная расчётная длина до округления, м")
    slack_added_m: float = Field(..., description="Добавленный запас по длине (м) для разных стоек")

    server_a: ServerRequest
    server_b: ServerRequest


class RackInfoResponse(BaseModel):
    """Информация о стойке для фронтенда."""

    code: str = Field(..., description="Код стойки из плана (например, '02b05')")
    index: int = Field(..., description="Порядковый индекс стойки в ряду (для расчёта расстояний)")


class RacksListResponse(BaseModel):
    """Ответ со списком доступных стоек."""

    racks: List[RackInfoResponse]


# Загружаем план стоек при старте приложения.
# Если Excel-файл отсутствует или его структура непредвиденная,
# используем дефолтный диапазон 02b03–02b18.
try:
    RACK_INFOS, RACK_CODE_TO_INFO = load_rack_plan()
except Exception as e:
    # В боевом коде можно логировать причину в файл/лог-систему.
    print(f"[rack_plan] Не удалось загрузить план стоек из Excel: {e}")
    print("[rack_plan] Используется дефолтный диапазон стоек 02b03–02b18.")
    RACK_INFOS, RACK_CODE_TO_INFO = generate_default_rack_plan()


@app.get("/")
async def root():
    """Корневой endpoint с информацией об API."""
    return {
        "message": "API калькулятора патч-кордов",
        "version": "1.0.0",
        "endpoints": {
            "/calculate": "POST - расчёт длины патч-корда",
            "/health": "GET - проверка работоспособности",
            "/racks": "GET - список доступных стоек"
        }
    }


@app.get("/health")
async def health():
    """Проверка работоспособности API."""
    return {"status": "ok"}


@app.get("/racks", response_model=RacksListResponse)
async def get_racks():
    """Вернуть список доступных стоек (02b03–02b18) для фронтенда."""
    racks = [RackInfoResponse(code=info.code, index=info.index) for info in RACK_INFOS]
    return RacksListResponse(racks=racks)


@app.post("/calculate", response_model=CalculationResponse)
async def calculate_cable_length(request: CalculationRequest):
    """
    Рассчитать длину патч-корда для коммутации двух серверов.
    
    Пример запроса:
    ```json
    {
        "server_a": {"rack_code": "02b03", "unit": 10},
        "server_b": {"rack_code": "02b07", "unit": 40},
        "config": {
            "safety_slack_cm": 40
        }
    }
    ```
    """
    try:
        # Получаем индексы стоек по их кодам
        try:
            rack_a_index = get_rack_index_by_code(request.server_a.rack_code, RACK_CODE_TO_INFO)
            rack_b_index = get_rack_index_by_code(request.server_b.rack_code, RACK_CODE_TO_INFO)
        except KeyError as e:
            raise HTTPException(status_code=400, detail=str(e))

        # Создаём объекты серверов с числовыми индексами стоек
        server_a = ServerLocation(rack=rack_a_index, unit=request.server_a.unit)
        server_b = ServerLocation(rack=rack_b_index, unit=request.server_b.unit)

        # Читаем настраиваемый страховочный запас (см) из запроса.
        # Поддерживаем старый ключ cross_rack_slack_m для совместимости.
        cfg_dict = request.config or {}
        safety_slack_cm_raw = cfg_dict.get("safety_slack_cm")
        if safety_slack_cm_raw is None:
            cross_rack_slack_m_raw = cfg_dict.get("cross_rack_slack_m")
            if cross_rack_slack_m_raw is not None:
                try:
                    safety_slack_cm_raw = float(cross_rack_slack_m_raw) * 100.0
                except (TypeError, ValueError):
                    raise HTTPException(
                        status_code=400,
                        detail="Параметр cross_rack_slack_m должен быть числом.",
                    )

        if safety_slack_cm_raw is None:
            safety_slack_cm = 40.0
        else:
            try:
                safety_slack_cm = float(safety_slack_cm_raw)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail="Параметр safety_slack_cm должен быть числом.",
                )
            if safety_slack_cm < 0:
                raise HTTPException(
                    status_code=400,
                    detail="Параметр safety_slack_cm не может быть отрицательным.",
                )

        cfg = DataCenterCableConfig(safety_slack_m=safety_slack_cm / 100.0)
        breakdown = calculate_patch_cord_breakdown(server_a, server_b, cfg)

        return CalculationResponse(
            length_m=breakdown.raw_total_m,
            recommended_patch_cord_m=breakdown.recommended_patch_cord_m,
            same_rack=breakdown.same_rack,
            vertical_a_m=breakdown.vertical_a_m,
            vertical_b_m=breakdown.vertical_b_m,
            horizontal_m=breakdown.horizontal_m,
            raw_total_m=breakdown.raw_total_m,
            slack_added_m=breakdown.slack_added_m,
            server_a=request.server_a,
            server_b=request.server_b,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Внутренняя ошибка: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
