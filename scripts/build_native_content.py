"""Build the own native Lua content catalog; no game or engine assets are copied."""
from pathlib import Path
import argparse
import json

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/native-content.json"
TARGET = ROOT / "mod/scripts/halveth/content_catalog.lua"


def validate(data):
    if data.get("schema") != 1 or data.get("license") != "MIT":
        raise ValueError("Unknown content contract")
    books, spells = data["books"], data["spells"]
    if len(books) != 6 or sum(len(b["pages"]) for b in books) != 15 or len(spells) != 3:
        raise ValueError("Expected six books, fifteen authored passages, three spells")
    keys = [x["key"] for x in books + spells]
    if len(set(keys)) != len(keys):
        raise ValueError("Duplicate content identity")
    for book in books:
        if not book["title"].startswith("HALVETH: ") or not book["author"]:
            raise ValueError("Book needs own attribution")
        for page in book["pages"]:
            if len(page["answers"]) != 3 or page["correct"] not in (1, 2, 3) or not page["text"]:
                raise ValueError("Invalid recall page")
    for spell in spells:
        if not 1 <= spell["cost"] <= 100:
            raise ValueError("Invalid magicka cost")
        for effect in spell["effects"]:
            if effect["id"] not in {"restorehealth", "shockdamage", "shield"}:
                raise ValueError("Unexpected engine effect")
            if effect["range"] not in {"Self", "Touch", "Target"}:
                raise ValueError("Invalid spell range")
            if not 0 <= effect["magnitudeMin"] <= effect["magnitudeMax"] <= 100:
                raise ValueError("Invalid spell magnitude")
    return data


def lua(value, indent=0):
    if isinstance(value, str):
        # JSON quoted ASCII strings are Lua-compatible for this original catalog.
        # Unicode stays literal; Lua does not recognize JSON's \\uXXXX syntax.
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, (list, dict)):
        entries = list(value.items()) if isinstance(value, dict) else [(None, v) for v in value]
        prefix = "    " * (indent + 1)
        lines = [prefix + (f"[{lua(k)}] = " if k is not None else "") + lua(v, indent + 1) + "," for k, v in entries]
        return "{\n" + "\n".join(lines) + "\n" + "    " * indent + "}"
    raise TypeError(f"Unsupported content value: {type(value).__name__}")


def render(data):
    return "-- Generated from data/native-content.json; own original texts, MIT.\n-- Native Morrowind/OpenMW content: no browser, web view or separate game.\nreturn " + lua(validate(data)) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = render(json.loads(SOURCE.read_text(encoding="utf-8")))
    if args.check:
        if TARGET.read_text(encoding="utf-8") != generated:
            raise SystemExit("Native content catalog is stale")
    else:
        TARGET.write_text(generated, encoding="utf-8", newline="\n")
    print("NATIVE_CONTENT_CATALOG_PASS: 6 books / 15 passages / 3 native spells")


if __name__ == "__main__":
    main()
