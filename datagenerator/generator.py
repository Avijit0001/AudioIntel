"""
json_enricher.py
----------------
Reads  : datagenerator/pickaboo_structured_products.json
         (fields: product_name, description, price, url)

Calls  : a local Ollama model once per product using a custom
         'enrich_product' tool/function-call to predict:

           • type        : Earphone | Headphone | Neckband | TWS
           • Connectivity: Wired | Wireless
           • Use Cases   : one or more of Gaming | General | Music | Studio | Travel

Writes : datagenerator/pickaboo_enriched_products.json
         (original fields + 3 new fields per product)

Usage  : python datagenerator/json_enricher.py
"""

import json
import os
import sys
import time

import ollama

# --------------------------------------------------------------------------- #
# Config                                                                       #
# --------------------------------------------------------------------------- #
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE  = os.path.join(BASE_DIR, "pickaboo_structured_products.json")
OUTPUT_FILE = os.path.join(BASE_DIR, "pickaboo_enriched_products.json")

MODEL = "qwen3:0.6b"   # change to any Ollama model that supports tool-calls
                     # e.g. "mistral", "qwen2.5", "llama3.1"

RETRY_LIMIT = 3      # retries per product on transient errors
RETRY_DELAY = 2      # seconds between retries

# Allowed value sets — single source of truth for schema + validation
VALID_TYPE         = {"Earphone", "Headphone", "Neckband", "TWS"}
VALID_CONNECTIVITY = {"Wired", "Wireless"}
VALID_USE_CASES    = {"Gaming", "General", "Music", "Studio", "Travel"}

# --------------------------------------------------------------------------- #
# Tool definition (JSON Schema)                                                #
# --------------------------------------------------------------------------- #
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "enrich_product",
            "description": (
                "Classify an audio product based on its name, description, and "
                "price. Return its category type, connectivity method, and all "
                "applicable use-cases."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": sorted(VALID_TYPE),
                        "description": (
                            "The product category. "
                            "Earphone=wired in-ear, TWS=true-wireless stereo buds, "
                            "Neckband=wireless neckband style, Headphone=over/on-ear."
                        ),
                    },
                    "Connectivity": {
                        "type": "string",
                        "enum": sorted(VALID_CONNECTIVITY),
                        "description": (
                            "How the product connects to a source device. "
                            "Wired=3.5mm jack or USB, Wireless=Bluetooth."
                        ),
                    },
                    "Use Cases": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": sorted(VALID_USE_CASES),
                        },
                        "minItems": 1,
                        "uniqueItems": True,
                        "description": (
                            "All use-cases that apply to this product. "
                            "Pick every relevant option: "
                            "General=everyday use, Music=audiophile/hi-fi, "
                            "Gaming=low-latency/mic focus, Studio=monitoring/flat response, "
                            "Travel=portability/noise isolation."
                        ),
                    },
                },
                "required": ["type", "Connectivity", "Use Cases"],
            },
        },
    }
]

# --------------------------------------------------------------------------- #
# Core classifier                                                              #
# --------------------------------------------------------------------------- #
def classify_product(product_name: str, description: str, price: str) -> dict | None:
    """
    Calls the local Ollama model with a forced tool-call and returns:
        {"type": str, "Connectivity": str, "Use Cases": list[str]}
    Returns None on unrecoverable failure.
    """
    prompt = (
        f"Product Name : {product_name}\n"
        f"Description  : {description}\n"
        f"Price (BDT)  : {price}\n\n"
        "Using only the information above, call the `enrich_product` tool to "
        "classify this audio product."
    )

    for attempt in range(1, RETRY_LIMIT + 1):
        try:
            response = ollama.chat(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                tools=TOOLS,
            )

            message = response.message

            # Check the tool was actually called
            if not message.tool_calls:
                print(f"    [WARN] Attempt {attempt}: no tool call returned. Retrying…")
                time.sleep(RETRY_DELAY)
                continue

            # Parse the arguments from the first tool call
            raw = message.tool_calls[0].function.arguments

            # ollama SDK may return a dict directly or a JSON string
            args = raw if isinstance(raw, dict) else json.loads(raw)

            product_type  = args.get("type", "")
            connectivity  = args.get("Connectivity", "")
            use_cases_raw = args.get("Use Cases", [])

            # Normalise: guard against LLM returning a string instead of list
            if isinstance(use_cases_raw, str):
                use_cases_raw = [u.strip() for u in use_cases_raw.split("|") if u.strip()]

            # Validate — warn but keep value (enum in schema already constrains the LLM)
            if product_type not in VALID_TYPE:
                print(f"    [WARN] Unexpected type '{product_type}' — keeping as-is.")
            if connectivity not in VALID_CONNECTIVITY:
                print(f"    [WARN] Unexpected connectivity '{connectivity}' — keeping as-is.")
            for uc in use_cases_raw:
                if uc not in VALID_USE_CASES:
                    print(f"    [WARN] Unexpected use-case '{uc}' — keeping as-is.")

            return {
                "type":         product_type,
                "Connectivity": connectivity,
                "Use Cases":    use_cases_raw,   # kept as list in JSON output
            }

        except Exception as exc:
            print(f"    [ERROR] Attempt {attempt} failed: {exc}")
            if attempt < RETRY_LIMIT:
                time.sleep(RETRY_DELAY)

    # All retries exhausted
    return None


# --------------------------------------------------------------------------- #
# Main enrichment pipeline                                                     #
# --------------------------------------------------------------------------- #
def enrich_json(input_path: str, output_path: str) -> None:
    """Read input JSON, classify each product, write enriched JSON."""

    # ----- load -----
    with open(input_path, encoding="utf-8") as f:
        products: list[dict] = json.load(f)

    if not products:
        print("[INFO] Input JSON is empty — nothing to do.")
        return

    print(f"[INFO] Loaded {len(products)} product(s) from '{input_path}'")
    print(f"[INFO] Model : {MODEL}")
    print(f"[INFO] Output: {output_path}\n")

    enriched: list[dict] = []
    success_count = 0
    skip_count    = 0

    for idx, product in enumerate(products, start=1):
        name  = product.get("product_name", "").strip()
        desc  = product.get("description",  "").strip()
        price = product.get("price",        "").strip()

        print(f"  [{idx:>2}/{len(products)}] {name}")

        # ----- resume safety: skip already-enriched rows -----
        if all(k in product for k in ("type", "Connectivity", "Use Cases")):
            print(f"         ↳ already enriched, skipping.")
            enriched.append(product)
            skip_count += 1
            continue

        result = classify_product(name, desc, price)

        if result is None:
            print(f"         ↳ [FAIL] Could not classify after {RETRY_LIMIT} attempts. Nulls inserted.")
            product.update({"type": None, "Connectivity": None, "Use Cases": None})
        else:
            product.update(result)
            success_count += 1
            print(
                f"         ↳ type={result['type']} | "
                f"Connectivity={result['Connectivity']} | "
                f"Use Cases={result['Use Cases']}"
            )

        enriched.append(product)

    # ----- write -----
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(enriched, f, ensure_ascii=False, indent=4)

    # ----- summary -----
    print(f"\n{'='*55}")
    print(f"  Done!")
    print(f"  Products processed : {len(products)}")
    print(f"  Newly classified   : {success_count}")
    print(f"  Already had data   : {skip_count}")
    print(f"  Output written to  : {output_path}")
    print(f"{'='*55}")


# --------------------------------------------------------------------------- #
# Entry point                                                                  #
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    # Optional CLI overrides:  python json_enricher.py [input.json] [output.json]
    input_path  = sys.argv[1] if len(sys.argv) > 1 else INPUT_FILE
    output_path = sys.argv[2] if len(sys.argv) > 2 else OUTPUT_FILE

    if not os.path.isfile(input_path):
        sys.exit(f"[ERROR] Input file not found: {input_path}")

    enrich_json(input_path, output_path)
