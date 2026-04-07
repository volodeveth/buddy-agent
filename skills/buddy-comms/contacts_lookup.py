#!/usr/bin/env python3
"""Contact lookup and management for buddy-comms."""

import sys
import io
import json
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

CONTACTS_PATH = Path(__file__).parent / "contacts.json"


def load_contacts() -> list[dict]:
    if not CONTACTS_PATH.exists():
        return []
    with open(CONTACTS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("contacts", [])


def save_contacts(contacts: list[dict]) -> None:
    with open(CONTACTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"contacts": contacts}, f, ensure_ascii=True, indent=2)


def _normalize_ukrainian(text: str) -> str:
    """Strip common Ukrainian suffixes for fuzzy stem matching.

    Ukrainian nouns/names change endings by case:
      Ірина → Ірині, Ірину, Іриною, Ірино
      Олег → Олегу, Олегові, Олегом
    This strips typical suffixes so declined forms match the base name.
    """
    text = text.lower().strip()
    # Common Ukrainian noun/name suffixes (longest first)
    suffixes = [
        "ові", "ою", "ою", "ям", "ях", "ів", "ам",
        "ні", "ну", "но", "ні", "на",
        "ом", "ів", "ці", "ку", "ко", "ка", "ки",
        "ої", "ій", "ою",
        "ем", "єм",
        "у", "і", "о", "е", "и", "ю", "я", "й",
    ]
    # Only strip if remaining stem is at least 3 chars
    for suffix in suffixes:
        if text.endswith(suffix) and len(text) - len(suffix) >= 3:
            return text[:-len(suffix)]
    return text


def search(query: str) -> list[dict]:
    """Search contacts by name or nickname (case-insensitive, Ukrainian-aware fuzzy match)."""
    contacts = load_contacts()
    query_lower = query.lower().strip()
    query_stem = _normalize_ukrainian(query_lower)
    results = []
    for c in contacts:
        name = c.get("name", "").lower()
        nicknames = [n.lower() for n in c.get("nickname", [])]
        role = c.get("role", "").lower()
        all_names = [name] + nicknames + ([role] if role else [])

        # Direct substring match (original behavior)
        if any(query_lower in n for n in all_names):
            results.append(c)
            continue

        # Ukrainian stem match: compare stems
        for n in all_names:
            name_stem = _normalize_ukrainian(n)
            if query_stem == name_stem or query_stem in name_stem or name_stem in query_stem:
                results.append(c)
                break

    return results


def add_contact(name: str, email: str = "", role: str = "",
                telegram: str = "", viber: str = "", notes: str = "") -> dict:
    """Add a new contact."""
    contacts = load_contacts()

    # Check for duplicates
    for c in contacts:
        if c.get("name", "").lower() == name.lower():
            return {"status": "exists", "contact": c}

    new_contact = {
        "name": name,
        "nickname": [name.split()[0]] if " " in name else [name],
        "email": email,
        "telegram": telegram,
        "viber": viber,
        "role": role,
        "notes": notes
    }
    contacts.append(new_contact)
    save_contacts(contacts)
    return {"status": "added", "contact": new_contact}


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "Usage: contacts_lookup.py <name> | --add <name> <email> [role]"}))
        sys.exit(1)

    if sys.argv[1] == "--add":
        if len(sys.argv) < 4:
            print(json.dumps({"error": "Usage: contacts_lookup.py --add <name> <email> [role]"}))
            sys.exit(1)
        name = sys.argv[2]
        email = sys.argv[3]
        role = sys.argv[4] if len(sys.argv) > 4 else ""
        result = add_contact(name, email, role)
        print(json.dumps(result, ensure_ascii=True))
    else:
        query = sys.argv[1]
        results = search(query)
        if results:
            print(json.dumps({"status": "found", "count": len(results), "contacts": results}, ensure_ascii=True))
        else:
            print(json.dumps({"status": "not_found", "query": query}, ensure_ascii=True))


if __name__ == "__main__":
    main()
