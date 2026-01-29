"""
CLI интерфейс для расчёта длины патч-кордов.
Использование: python cli_interface.py
"""

import argparse
import sys
from cable_calculator import (
    ServerLocation,
    DataCenterCableConfig,
    calculate_patch_cord_length_m,
)


def main():
    parser = argparse.ArgumentParser(
        description="Расчёт длины патч-корда для коммутации серверов в дата-центре",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Примеры использования:
  # Одна стойка, разные юниты
  python cli_interface.py --rack1 1 --unit1 10 --rack2 1 --unit2 30
  
  # Соседние стойки
  python cli_interface.py --rack1 1 --unit1 10 --rack2 2 --unit2 40
  
  # С настройками
  python cli_interface.py --rack1 1 --unit1 5 --rack2 5 --unit2 45 --slack 1.15
        """
    )

    # Параметры первого сервера
    parser.add_argument("--rack1", type=int, required=True, help="Номер стойки первого сервера")
    parser.add_argument("--unit1", type=int, required=True, help="Номер юнита первого сервера (1-50)")

    # Параметры второго сервера
    parser.add_argument("--rack2", type=int, required=True, help="Номер стойки второго сервера")
    parser.add_argument("--unit2", type=int, required=True, help="Номер юнита второго сервера (1-50)")

    # Опциональные параметры конфигурации
    parser.add_argument("--slack", type=float, help="Коэффициент запаса (по умолчанию 1.10)")
    parser.add_argument("--rounding", type=float, help="Шаг округления в метрах (по умолчанию 0.5)")
    parser.add_argument("--unit-height", type=float, help="Высота одного юнита в метрах (по умолчанию 0.044)")

    args = parser.parse_args()

    # Создаём конфигурацию
    config_kwargs = {}
    if args.slack:
        config_kwargs["slack_factor"] = args.slack
    if args.rounding:
        config_kwargs["rounding_step_m"] = args.rounding
    if args.unit_height:
        config_kwargs["unit_height_m"] = args.unit_height

    cfg = DataCenterCableConfig(**config_kwargs)

    # Создаём объекты серверов
    try:
        server_a = ServerLocation(rack=args.rack1, unit=args.unit1)
        server_b = ServerLocation(rack=args.rack2, unit=args.unit2)
    except Exception as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)

    # Рассчитываем длину
    try:
        length = calculate_patch_cord_length_m(server_a, server_b, cfg)
        
        # Выводим результат
        print(f"\n{'='*60}")
        print(f"Расчёт длины патч-корда")
        print(f"{'='*60}")
        print(f"Сервер A: Стойка {server_a.rack}, Юнит {server_a.unit}")
        print(f"Сервер B: Стойка {server_b.rack}, Юнит {server_b.unit}")
        print(f"{'='*60}")
        print(f"Необходимая длина патч-корда: {length:.2f} м")
        print(f"{'='*60}\n")
        
    except ValueError as e:
        print(f"Ошибка валидации: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Неожиданная ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
