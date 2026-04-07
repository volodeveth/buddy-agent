#!/usr/bin/env python3
"""
Skill: Exchange Rates from PrivatBank API
Отримує поточні курси USD та EUR від ПриватБанку
"""

import sys
import io
import json
from pathlib import Path
from urllib.request import urlopen
from urllib.parse import urlencode
from urllib.error import URLError, HTTPError

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

SKILL_DIR = Path(__file__).parent.resolve()
PRIVATBANK_API = "https://api.privatbank.ua/p24api/pubinfo"


def fetch_exchange_rates() -> dict:
    """
    Отримує курси валют від ПриватБанку API
    
    Returns:
        dict: словник з курсами USD та EUR
    """
    params = urlencode({
        "exchange": "",
        "coursid": 5
    })
    url = f"{PRIVATBANK_API}?{params}"
    
    try:
        with urlopen(url, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data
    except HTTPError as e:
        raise Exception(f"Помилка HTTP: {e.code} - {e.reason}")
    except URLError as e:
        raise Exception(f"Помилка з'єднання: {e.reason}")
    except json.JSONDecodeError as e:
        raise Exception(f"Помилка парсингу JSON: {e}")


def parse_rates(data: list[dict]) -> dict:
    """
    Парсить відповідь API та витягує курси USD та EUR
    
    Args:
        data: список валют з API
        
    Returns:
        dict: курси USD та EUR
    """
    result = {}
    currencies = {"USD": "Долар США", "EUR": "Євро"}
    
    for item in data:
        ccy = item.get("ccy", "")
        if ccy in currencies:
            result[ccy] = {
                "currency": currencies[ccy],
                "ccy": ccy,
                "buy": round(float(item.get("buy", 0)), 2),
                "sale": round(float(item.get("sale", 0)), 2)
            }
    
    return result


def format_response(rates: dict) -> str:
    """
    Форматує відповідь у зручному для читання вигляді
    
    Args:
        rates: словник з курсами
        
    Returns:
        str: відформатований рядок
    """
    lines = ["💱 Курси валют від ПриватБанку", "=" * 35]
    
    if "USD" in rates:
        usd = rates["USD"]
        lines.append(f"🇺🇸 {usd['currency']} (USD)")
        lines.append(f"   Купівля: {usd['buy']} грн")
        lines.append(f"   Продаж:  {usd['sale']} грн")
        lines.append("")
    
    if "EUR" in rates:
        eur = rates["EUR"]
        lines.append(f"🇪🇺 {eur['currency']} (EUR)")
        lines.append(f"   Купівля: {eur['buy']} грн")
        lines.append(f"   Продаж:  {eur['sale']} грн")
    
    return "\n".join(lines)


def main() -> None:
    """Головна функція: отримує курси та виводить результат"""
    try:
        # Отримуємо дані з API
        data = fetch_exchange_rates()
        
        # Парсимо курси
        rates = parse_rates(data)
        
        # Формуємо відповідь
        if not rates:
            result = {
                "status": "success",
                "message": "Курси валют тимчасово недоступні",
                "rates": {}
            }
        else:
            result = {
                "status": "success",
                "source": "ПриватБанк",
                "rates": rates,
                "formatted": format_response(rates)
            }
        
        print(json.dumps(result, ensure_ascii=True, indent=2))
        
    except Exception as e:
        error_result = {
            "status": "error",
            "error": str(e),
            "message": "Не вдалося отримати курси валют"
        }
        print(json.dumps(error_result, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
