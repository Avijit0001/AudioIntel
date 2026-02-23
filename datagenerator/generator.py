"""
generator.py
------------
Reads an existing product CSV (columns: name, description, price, URL),
calls the Groq LLM for each row via a structured function/tool call to
classify the product, then writes three new columns back to the same CSV:

  • type        : Headphone | TWS | Neckband | Earphone
  • Connectivity: Wired | Wireless
  • Use Cases   : General | Music | Gaming | Studio | Travel
"""

import csv
import json
import os
import sys

import dotenv
from groq import Groq

# --------------------------------------------------------------------------- #
# Config                                                                       #
# --------------------------------------------------------------------------- #
dotenv.load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    sys.exit("[ERROR] GROQ_API_KEY not found in environment / .env file.")

client = Groq(api_key=GROQ_API_KEY)

MODEL = "llama3-70b-8192"          # fast & capable Groq model; change if needed

# Allowed option sets (used both in the tool schema and for validation)
VALID_TYPE         = {"Headphone", "TWS", "Neckband", "Earphone"}
VALID_CONNECTIVITY = {"Wired", "Wireless"}
VALID_USE_CASES    = {"General", "Music", "Gaming", "Studio", "Travel"}

# --------------------------------------------------------------------------- #
# Tool definition                                                              #
# --------------------------------------------------------------------------- #
tools = [
    {
        "type": "function",
        "function": {
            "name": "enrich_product",
            "description": (
                "Classify an audio product into its type, connectivity, and "
                "primary use-case based on its name, description, and price."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": sorted(VALID_TYPE),
                        "description": "Category of the audio product."
                    },
                    "Connectivity": {
                        "type": "string",
                        "enum": sorted(VALID_CONNECTIVITY),
                        "description": "How the product connects to a device."
                    },
                    "Use Cases": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": sorted(VALID_USE_CASES)
                        },
                        "minItems": 1,
                        "uniqueItems": True,
                        "description": "One or more use-cases that apply to this product."
                    }
                },
                "required": ["type", "Connectivity", "Use Cases"]
            }
        }
    }
]

# --------------------------------------------------------------------------- #
# Core classifier                                                              #
# --------------------------------------------------------------------------- #
def classify_product(name: str, description: str, price: str) -> dict:
    """
    Sends one product to the LLM via a forced tool call and returns a dict:
    {"type": ..., "Connectivity": ..., "Use Cases": ...}
    Falls back to empty strings on any error.
    """
    user_prompt = (
        f"Product Name   : {name}\n"
        f"Description    : {description}\n"
        f"Price          : {price}\n\n"
        "Based on the information above, call the `enrich_product` tool to "
        "classify this audio product."
    )

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": user_prompt}],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "enrich_product"}},
        )

        message = response.choices[0].message

        if not message.tool_calls:
            print(f"  [WARN] No tool call returned for '{name}'. Skipping.")
            return {"type": "", "Connectivity": "", "Use Cases": ""}

        args = json.loads(message.tool_calls[0].function.arguments)

        # Validate each field; fall back to empty string if unexpected value
        product_type   = args.get("type", "")
        connectivity   = args.get("Connectivity", "")
        use_cases_raw  = args.get("Use Cases", [])

        # Normalise: the LLM might occasionally return a plain string instead of a list
        if isinstance(use_cases_raw, str):
            use_cases_raw = [use_cases_raw]

        if product_type not in VALID_TYPE:
            print(f"  [WARN] Unexpected type '{product_type}' for '{name}'. Keeping as-is.")
        if connectivity not in VALID_CONNECTIVITY:
            print(f"  [WARN] Unexpected connectivity '{connectivity}' for '{name}'. Keeping as-is.")
        for uc in use_cases_raw:
            if uc not in VALID_USE_CASES:
                print(f"  [WARN] Unexpected use-case '{uc}' for '{name}'. Keeping as-is.")

        # Store as pipe-separated string so the CSV cell stays clean
        use_cases = "|".join(use_cases_raw)

        return {
            "type"        : product_type,
            "Connectivity": connectivity,
            "Use Cases"   : use_cases,   # pipe-separated, e.g. "Music|Gaming"
        }

    except Exception as exc:
        print(f"  [ERROR] LLM call failed for '{name}': {exc}")
        return {"type": "", "Connectivity": "", "Use Cases": ""}


# --------------------------------------------------------------------------- #
# CSV I/O                                                                      #
# --------------------------------------------------------------------------- #
def enrich_csv(input_path: str, output_path: str | None = None) -> None:
    """
    Read the CSV at `input_path`, classify every row, and write the enriched
    CSV to `output_path` (defaults to overwriting `input_path`).

    Expected input columns : name, description, price, URL
    Added output columns   : type, Connectivity, Use Cases
    """
    if output_path is None:
        output_path = input_path

    # ---------- read ----------
    with open(input_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        rows = list(reader)

    if not rows:
        print("[INFO] CSV is empty – nothing to process.")
        return

    # Ensure required columns exist
    for required_col in ("name", "description", "price", "URL"):
        if required_col not in fieldnames:
            sys.exit(f"[ERROR] Required column '{required_col}' not found in CSV.")

    # Build output fieldnames (keep originals, add new cols if not already present)
    new_cols = ["type", "Connectivity", "Use Cases"]
    output_fieldnames = list(fieldnames)
    for col in new_cols:
        if col not in output_fieldnames:
            output_fieldnames.append(col)

    print(f"[INFO] Processing {len(rows)} product(s) from '{input_path}' …\n")

    # ---------- classify each row ----------
    for idx, row in enumerate(rows, start=1):
        name        = row.get("name", "").strip()
        description = row.get("description", "").strip()
        price       = row.get("price", "").strip()

        print(f"  [{idx}/{len(rows)}] Classifying: {name}")

        classification = classify_product(name, description, price)
        row.update(classification)

        print(
            f"         → type={classification['type']} | "
            f"Connectivity={classification['Connectivity']} | "
            f"Use Cases={classification['Use Cases']}"
        )

    # ---------- write ----------
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=output_fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    print(f"\n[DONE] Enriched CSV written to '{output_path}'.")


# --------------------------------------------------------------------------- #
# Entry point                                                                  #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Accept an optional CSV path as a command-line argument
    # Usage:  python generator.py [path/to/products.csv] [optional/output.csv]
    if len(sys.argv) < 2:
        sys.exit(
            "Usage: python generator.py <input_csv> [output_csv]\n"
            "  input_csv  – CSV with columns: name, description, price, URL\n"
            "  output_csv – (optional) path to save enriched CSV; "
            "defaults to overwriting input_csv"
        )

    input_csv  = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) >= 3 else None

    if not os.path.isfile(input_csv):
        sys.exit(f"[ERROR] File not found: {input_csv}")

    enrich_csv(input_csv, output_csv)
