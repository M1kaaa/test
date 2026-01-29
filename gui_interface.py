"""
GUI интерфейс на tkinter для расчёта длины патч-кордов.
Использование: python gui_interface.py
"""

import tkinter as tk
from tkinter import ttk, messagebox
from cable_calculator import (
    ServerLocation,
    DataCenterCableConfig,
    calculate_patch_cord_length_m,
)


class CableCalculatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Калькулятор длины патч-кордов")
        self.root.geometry("500x600")
        self.root.resizable(False, False)

        # Стиль
        style = ttk.Style()
        style.theme_use("clam")

        self.create_widgets()

    def create_widgets(self):
        # Заголовок
        title_frame = tk.Frame(self.root, bg="#667eea", height=80)
        title_frame.pack(fill=tk.X)
        title_frame.pack_propagate(False)

        title_label = tk.Label(
            title_frame,
            text="🔌 Калькулятор патч-кордов",
            font=("Arial", 20, "bold"),
            bg="#667eea",
            fg="white"
        )
        title_label.pack(pady=20)

        # Основной контейнер
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Сервер A
        server_a_frame = tk.LabelFrame(
            main_frame,
            text="Сервер A",
            font=("Arial", 12, "bold"),
            padx=15,
            pady=15
        )
        server_a_frame.pack(fill=tk.X, pady=10)

        tk.Label(server_a_frame, text="Номер стойки:", font=("Arial", 10)).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.rack1_var = tk.StringVar(value="1")
        tk.Entry(server_a_frame, textvariable=self.rack1_var, width=15).grid(
            row=0, column=1, padx=10, pady=5
        )

        tk.Label(server_a_frame, text="Номер юнита (1-50):", font=("Arial", 10)).grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.unit1_var = tk.StringVar(value="10")
        tk.Entry(server_a_frame, textvariable=self.unit1_var, width=15).grid(
            row=1, column=1, padx=10, pady=5
        )

        # Сервер B
        server_b_frame = tk.LabelFrame(
            main_frame,
            text="Сервер B",
            font=("Arial", 12, "bold"),
            padx=15,
            pady=15
        )
        server_b_frame.pack(fill=tk.X, pady=10)

        tk.Label(server_b_frame, text="Номер стойки:", font=("Arial", 10)).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.rack2_var = tk.StringVar(value="1")
        tk.Entry(server_b_frame, textvariable=self.rack2_var, width=15).grid(
            row=0, column=1, padx=10, pady=5
        )

        tk.Label(server_b_frame, text="Номер юнита (1-50):", font=("Arial", 10)).grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.unit2_var = tk.StringVar(value="30")
        tk.Entry(server_b_frame, textvariable=self.unit2_var, width=15).grid(
            row=1, column=1, padx=10, pady=5
        )

        # Дополнительные настройки
        config_frame = tk.LabelFrame(
            main_frame,
            text="⚙️ Дополнительные настройки",
            font=("Arial", 10, "bold"),
            padx=15,
            pady=15
        )
        config_frame.pack(fill=tk.X, pady=10)

        tk.Label(config_frame, text="Коэффициент запаса:", font=("Arial", 9)).grid(
            row=0, column=0, sticky=tk.W, pady=5
        )
        self.slack_var = tk.StringVar(value="1.10")
        tk.Entry(config_frame, textvariable=self.slack_var, width=15).grid(
            row=0, column=1, padx=10, pady=5
        )

        tk.Label(config_frame, text="Шаг округления (м):", font=("Arial", 9)).grid(
            row=1, column=0, sticky=tk.W, pady=5
        )
        self.rounding_var = tk.StringVar(value="0.5")
        tk.Entry(config_frame, textvariable=self.rounding_var, width=15).grid(
            row=1, column=1, padx=10, pady=5
        )

        # Кнопка расчёта
        calculate_btn = tk.Button(
            main_frame,
            text="Рассчитать длину",
            font=("Arial", 12, "bold"),
            bg="#667eea",
            fg="white",
            padx=20,
            pady=10,
            command=self.calculate,
            cursor="hand2"
        )
        calculate_btn.pack(pady=20)

        # Результат
        self.result_frame = tk.Frame(main_frame, bg="#38ef7d", relief=tk.RAISED, bd=2)
        self.result_frame.pack(fill=tk.X, pady=10)

        self.result_label = tk.Label(
            self.result_frame,
            text="",
            font=("Arial", 16, "bold"),
            bg="#38ef7d",
            fg="white"
        )
        self.result_label.pack(pady=15)

        self.details_label = tk.Label(
            self.result_frame,
            text="",
            font=("Arial", 10),
            bg="#38ef7d",
            fg="white"
        )
        self.details_label.pack(pady=5)

        self.result_frame.pack_forget()  # Скрываем до расчёта

    def calculate(self):
        try:
            # Получаем значения
            rack1 = int(self.rack1_var.get())
            unit1 = int(self.unit1_var.get())
            rack2 = int(self.rack2_var.get())
            unit2 = int(self.unit2_var.get())

            # Валидация
            if rack1 < 1 or rack2 < 1:
                messagebox.showerror("Ошибка", "Номер стойки должен быть положительным")
                return

            if not (1 <= unit1 <= 50) or not (1 <= unit2 <= 50):
                messagebox.showerror("Ошибка", "Номер юнита должен быть от 1 до 50")
                return

            # Создаём серверы
            server_a = ServerLocation(rack=rack1, unit=unit1)
            server_b = ServerLocation(rack=rack2, unit=unit2)

            # Создаём конфигурацию
            config_kwargs = {}
            try:
                slack = float(self.slack_var.get())
                if slack > 0:
                    config_kwargs["slack_factor"] = slack
            except ValueError:
                pass

            try:
                rounding = float(self.rounding_var.get())
                if rounding > 0:
                    config_kwargs["rounding_step_m"] = rounding
            except ValueError:
                pass

            cfg = DataCenterCableConfig(**config_kwargs)

            # Рассчитываем
            length = calculate_patch_cord_length_m(server_a, server_b, cfg)

            # Показываем результат
            self.result_label.config(text=f"Длина патч-корда: {length:.2f} м")
            self.details_label.config(
                text=f"Стойка {rack1}, Юнит {unit1} → Стойка {rack2}, Юнит {unit2}"
            )
            self.result_frame.pack(fill=tk.X, pady=10)

        except ValueError as e:
            messagebox.showerror("Ошибка валидации", str(e))
        except Exception as e:
            messagebox.showerror("Ошибка", f"Неожиданная ошибка: {str(e)}")


def main():
    root = tk.Tk()
    app = CableCalculatorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
