import json
import os
import tkinter as tk
from tkinter import messagebox, ttk

import requests

APP_TITLE = "Currency Converter"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE_DIR, "history.json")
API_KEY_ENV = "EXCHANGE_API_KEY"
API_KEY_FILE = os.path.join(BASE_DIR, "api_key.txt")
API_URL_TEMPLATE = "https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}"

SUPPORTED_CURRENCIES = [
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "AUD",
    "CAD",
    "CHF",
    "CNY",
    "RUB",
    "UAH",
]


def load_api_key():
    api_key = os.getenv(API_KEY_ENV)
    if api_key:
        return api_key.strip()
    if os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, "r", encoding="utf-8") as fp:
            return fp.read().strip()
    return None


def fetch_conversion_rate(base_currency):
    api_key = load_api_key()
    if not api_key:
        raise RuntimeError(
            "API key not found. Установите переменную окружения EXCHANGE_API_KEY или создайте api_key.txt"
        )
    url = API_URL_TEMPLATE.format(api_key=api_key, base=base_currency)
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    data = response.json()
    if data.get("result") != "success":
        raise RuntimeError(data.get("error-type", "API error"))
    return data["conversion_rates"]


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as fp:
                return json.load(fp)
        except (json.JSONDecodeError, IOError):
            return []
    return []


def save_history(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as fp:
        json.dump(history, fp, ensure_ascii=False, indent=2)


class CurrencyConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.resizable(False, False)
        self.history = load_history()
        self.create_widgets()
        self.build_history_table()
        self.load_history_table()

    def create_widgets(self):
        frame = ttk.Frame(self.root, padding=12)
        frame.grid(row=0, column=0, sticky="NSEW")

        ttk.Label(frame, text="Из валюты:").grid(row=0, column=0, sticky="W")
        self.from_currency = ttk.Combobox(frame, values=SUPPORTED_CURRENCIES, state="readonly")
        self.from_currency.set("USD")
        self.from_currency.grid(row=0, column=1, sticky="EW", padx=6, pady=4)

        ttk.Label(frame, text="В валюту:").grid(row=1, column=0, sticky="W")
        self.to_currency = ttk.Combobox(frame, values=SUPPORTED_CURRENCIES, state="readonly")
        self.to_currency.set("EUR")
        self.to_currency.grid(row=1, column=1, sticky="EW", padx=6, pady=4)

        ttk.Label(frame, text="Сумма:").grid(row=2, column=0, sticky="W")
        self.amount_entry = ttk.Entry(frame)
        self.amount_entry.grid(row=2, column=1, sticky="EW", padx=6, pady=4)

        self.convert_button = ttk.Button(frame, text="Конвертировать", command=self.convert_currency)
        self.convert_button.grid(row=3, column=0, columnspan=2, pady=10)

        self.result_label = ttk.Label(frame, text="Результат: ")
        self.result_label.grid(row=4, column=0, columnspan=2, sticky="W", pady=4)

        self.load_button = ttk.Button(frame, text="Загрузить историю", command=self.reload_history)
        self.load_button.grid(row=5, column=0, columnspan=2, pady=4)

        table_frame = ttk.LabelFrame(frame, text="История конвертаций", padding=8)
        table_frame.grid(row=6, column=0, columnspan=2, sticky="NSEW", pady=8)

        self.history_table = ttk.Treeview(
            table_frame,
            columns=("from", "to", "amount", "rate", "result"),
            show="headings",
            height=8,
        )
        self.history_table.heading("from", text="Из")
        self.history_table.heading("to", text="В")
        self.history_table.heading("amount", text="Сумма")
        self.history_table.heading("rate", text="Курс")
        self.history_table.heading("result", text="Результат")
        self.history_table.column("from", width=50, anchor="center")
        self.history_table.column("to", width=50, anchor="center")
        self.history_table.column("amount", width=90, anchor="center")
        self.history_table.column("rate", width=90, anchor="center")
        self.history_table.column("result", width=110, anchor="center")
        self.history_table.grid(row=0, column=0, sticky="NSEW")

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.history_table.yview)
        self.history_table.configure(yscroll=scrollbar.set)
        scrollbar.grid(row=0, column=1, sticky="NS")

        for child in frame.winfo_children():
            child.grid_configure(padx=2, pady=2)

    def build_history_table(self):
        for item in self.history_table.get_children():
            self.history_table.delete(item)

    def load_history_table(self):
        self.build_history_table()
        for item in self.history:
            self.history_table.insert(
                "",
                "end",
                values=(
                    item["from"],
                    item["to"],
                    item["amount"],
                    item["rate"],
                    item["result"],
                ),
            )

    def convert_currency(self):
        amount_text = self.amount_entry.get().strip()
        try:
            amount = float(amount_text.replace(",", "."))
            if amount <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Ошибка ввода", "Введите положительное число для суммы.")
            return

        from_currency = self.from_currency.get()
        to_currency = self.to_currency.get()
        if from_currency == to_currency:
            messagebox.showinfo("Информация", "Выбраны одинаковые валюты. Результат равен сумме.")
            rate = 1.0
            result = amount
        else:
            try:
                rates = fetch_conversion_rate(from_currency)
                rate = rates.get(to_currency)
                if rate is None:
                    raise RuntimeError(f"Курс для {to_currency} не найден")
                result = amount * rate
            except Exception as exc:
                messagebox.showerror("Ошибка API", f"Не удалось получить курс: {exc}")
                return

        result_text = f"{amount:.2f} {from_currency} = {result:.2f} {to_currency}"
        self.result_label.configure(text=f"Результат: {result_text}")

        record = {
            "from": from_currency,
            "to": to_currency,
            "amount": f"{amount:.2f}",
            "rate": f"{rate:.6f}",
            "result": f"{result:.2f}",
        }
        self.history.insert(0, record)
        save_history(self.history)
        self.load_history_table()

    def reload_history(self):
        self.history = load_history()
        self.load_history_table()
        messagebox.showinfo("История", "История загружена из файла.")


if __name__ == "__main__":
    root = tk.Tk()
    app = CurrencyConverterApp(root)
    root.mainloop()
