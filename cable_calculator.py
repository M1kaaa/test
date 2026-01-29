"""
Модуль для расчёта длины патч-кордов в дата-центре.

Логика:
- Одна стойка: длина по таблице в зависимости от расстояния в юнитах.
- Разные стойки: формула (стойка A + кабель-канал + стойка B + 40 см).
Итог округляется вверх до ближайшего патч-корда из списка: 1, 1.5, 2, 3, 5, 7.5, 10, 15, 20 м.
Если разница между рекомендуемым патч-кордом и расчётной длиной ≥ 40 см, от рекомендуемого
отнимаем 40 см и округляем до ближайшего размера; если результат ≥ расчётной длины — берём его.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, NamedTuple, Optional

# Доступные длины патч-кордов (м), по возрастанию
PATCH_CORD_OPTIONS_M: List[float] = [1.0, 1.5, 2.0, 3.0, 5.0, 7.5, 10.0, 15.0, 20.0]

MAX_UNIT = 50  # последний юнит в стойке
EXCESS_THRESHOLD_M = 0.4  # если запас ≥ 40 см, пробуем укоротить рекомендацию


class ServerLocation(NamedTuple):
    """
    Положение сервера в стойке.

    rack: порядковый индекс стойки (1, 2, 3, ...)
    unit: номер юнита (1..50), 1 — нижний, 50 — верхний.
    """
    rack: int
    unit: int


@dataclass(frozen=True)
class DataCenterCableConfig:
    """
    Конфигурация (оставлена для совместимости API).
    Расчёт использует фиксированные формулы из ТЗ.
    """
    pass


def _same_rack_length_m(unit_a: int, unit_b: int) -> float:
    """
    Длина кабеля внутри одной стойки по таблице (м).

    Расстояние в юнитах (разница между юнитами):
    1–2   → 0.5 м
    3–8   → 1 м
    9–15  → 1.5 м
    16–23 → 2 м
    24–37 → 2.5 м
    38–50 → 3 м
    """
    delta = abs(unit_a - unit_b)
    if not (1 <= unit_a <= MAX_UNIT and 1 <= unit_b <= MAX_UNIT):
        raise ValueError(f"Юнит должен быть в диапазоне 1..{MAX_UNIT}")

    if delta <= 2:
        return 0.5
    if delta <= 8:
        return 1.0
    if delta <= 15:
        return 1.5
    if delta <= 23:
        return 2.0
    if delta <= 37:
        return 2.5
    return 3.0


def _round_up_to_patch_cord(length_m: float) -> float:
    """Округлить длину вверх до ближайшего доступного патч-корда."""
    for opt in PATCH_CORD_OPTIONS_M:
        if opt >= length_m:
            return opt
    return PATCH_CORD_OPTIONS_M[-1]


def _round_to_nearest_patch_cord(length_m: float) -> float:
    """Округлить длину до ближайшего доступного патч-корда. При равенстве — вверх."""
    best = PATCH_CORD_OPTIONS_M[0]
    best_dist = abs(best - length_m)
    for opt in PATCH_CORD_OPTIONS_M:
        d = abs(opt - length_m)
        if d < best_dist or (d == best_dist and opt > best):
            best, best_dist = opt, d
    return best


def _vertical_in_rack_a_m(unit_a: int) -> float:
    """Длина в стойке A: 4 см на каждый юнит от сервера до верха (50). В метрах."""
    if not (1 <= unit_a <= MAX_UNIT):
        raise ValueError(f"Юнит должен быть в диапазоне 1..{MAX_UNIT}")
    return 0.04 * (MAX_UNIT - unit_a)


def _cable_channel_m(rack_a: int, rack_b: int) -> float:
    """
    Длина в кабель-канале: (число стоек между A и B) * 50 см + 100 см. В метрах.
    Пример: из 1 в 2 стойку → 1; из 1 в 5 → 4.
    """
    rack_delta = abs(rack_b - rack_a)
    if rack_delta == 0:
        return 0.0
    return (rack_delta * 50 + 100) / 100.0  # см → м


def _vertical_in_rack_b_m(unit_b: int) -> float:
    """
    Длина во второй стойке (от кабель-канала до сервера).
    Если 1–2 юнита от верха (50 - unit_b <= 2) → 0.5 м.
    Иначе: 4*(50 - unit_b) + 70 + 30 см = 4*(50 - unit_b) + 100 см. В метрах.
    """
    if not (1 <= unit_b <= MAX_UNIT):
        raise ValueError(f"Юнит должен быть в диапазоне 1..{MAX_UNIT}")
    units_from_top = MAX_UNIT - unit_b
    if units_from_top <= 2:
        return 0.5
    return (4 * units_from_top + 70 + 30) / 100.0  # см → м


@dataclass(frozen=True)
class CableLengthBreakdown:
    """
    Детализация длины патч-корда по компонентам и рекомендуемый патч-корд.
    """

    same_rack: bool
    vertical_a_m: float
    vertical_b_m: float
    horizontal_m: float
    raw_total_m: float
    slack_added_m: float
    rounded_total_m: float
    recommended_patch_cord_m: float


def calculate_patch_cord_breakdown(
    server_a: ServerLocation,
    server_b: ServerLocation,
    cfg: Optional[DataCenterCableConfig] = None,
) -> CableLengthBreakdown:
    """
    Рассчитать длину патч-корда по ТЗ:
    - одна стойка: таблица по расстоянию в юнитах;
    - разные стойки: стойка A + кабель-канал + стойка B + 40 см.
    Округление вверх до патч-корда из списка; если запас ≥ 40 см — пробуем (рекоменд − 40 см)
    с округлением до ближайшего, без уменьшения ниже расчётной длины.
    """
    same_rack = server_a.rack == server_b.rack

    if same_rack:
        raw_total = _same_rack_length_m(server_a.unit, server_b.unit)
        vertical_a = raw_total  # для визуализации показываем как один вертикальный отрезок
        vertical_b = 0.0
        horizontal = 0.0
        slack_added = 0.0
    else:
        vertical_a = _vertical_in_rack_a_m(server_a.unit)
        horizontal = _cable_channel_m(server_a.rack, server_b.rack)
        vertical_b = _vertical_in_rack_b_m(server_b.unit)
        raw_total = vertical_a + horizontal + vertical_b + 0.4  # +40 см
        slack_added = 0.4

    recommended = _round_up_to_patch_cord(raw_total)
    gap = recommended - raw_total
    if gap >= EXCESS_THRESHOLD_M:
        candidate = recommended - EXCESS_THRESHOLD_M
        shorter = _round_to_nearest_patch_cord(candidate)
        if shorter >= raw_total:
            recommended = shorter

    return CableLengthBreakdown(
        same_rack=same_rack,
        vertical_a_m=vertical_a,
        vertical_b_m=vertical_b,
        horizontal_m=horizontal,
        raw_total_m=raw_total,
        slack_added_m=slack_added,
        rounded_total_m=recommended,
        recommended_patch_cord_m=recommended,
    )


def calculate_patch_cord_length_m(
    server_a: ServerLocation,
    server_b: ServerLocation,
    cfg: Optional[DataCenterCableConfig] = None,
) -> float:
    """Вернуть рекомендуемую длину патч-корда (м)."""
    breakdown = calculate_patch_cord_breakdown(server_a, server_b, cfg)
    return breakdown.recommended_patch_cord_m
