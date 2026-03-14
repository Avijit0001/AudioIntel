import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

# The absolute path to the .env file that contains the Supabase credentials
ENV_PATH = r"c:\Code_EveryThing\Automate Scrape\.env"
load_dotenv(ENV_PATH)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY")

if not url or not key:
    print(f"❌ Supabase credentials not found in {ENV_PATH}")
    # Fallback to current directory .env just in case
    load_dotenv()
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY") or os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("❌ Still no credentials found.")
        exit(1)

supabase: Client = create_client(url, key)

print("🔄 Fetching data from Supabase 'Updated_product' table...")

all_data = []
offset = 0
limit = 1000

while True:
    try:
        # Fetching data using pagination
        response = supabase.table("Updated_product").select("*").range(offset, offset + limit - 1).execute()
        data = response.data
        
        if not data:
            break
            
        all_data.extend(data)
        
        # If the number of returned records is less than the limit, we're done
        if len(data) < limit:
            break
            
        offset += limit
    except Exception as e:
        print(f"❌ Error fetching data: {e}")
        break

print(f"✅ Downloaded {len(all_data)} products.")

# Removing the internal Supabase columns to match the 'products.json' schema exactly
for item in all_data:
    item.pop("id", None)
    item.pop("created_at", None)

# Output path for the data inside the `embeddding` folder
output_folder = r"c:\Code_EveryThing\github\AudioIntel\embeddding"
output_file = os.path.join(output_folder, "updated_products.json")

# Ensures the output directory physically exists
os.makedirs(output_folder, exist_ok=True)

print(f"💾 Saving data to {output_file}...")
try:
    with open(output_file, "w", encoding="utf-8") as f:
        # Saving with indent=4 and ensure_ascii=False to identically mirror the format of your original `products.json`
        json.dump(all_data, f, indent=4, ensure_ascii=False)
    print("🎉 Data successfully saved!")
except Exception as e:
    print(f"❌ Error saving file: {e}")
