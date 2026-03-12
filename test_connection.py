import gspread
from google.oauth2.service_account import Credentials
import json

# Your sheet ID
SHEET_ID = "1aQxsJlAR1fzEx_EOZ3-2VnQfEQpkGjKXb8yRiYcwPI8"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

# Load credentials from JSON file directly for testing
with open("credentials.json") as f:
    creds_dict = json.load(f)

credentials = Credentials.from_service_account_info(
    creds_dict,
    scopes=SCOPES
)

client = gspread.authorize(credentials)

try:
    spreadsheet = client.open_by_key(SHEET_ID)
    print("✅ Connection successful!")
    print(f"Spreadsheet name: {spreadsheet.title}")
    print(f"\nSheet tabs found:")
    for ws in spreadsheet.worksheets():
        print(f"  - {ws.title}")
    
    # Test reading your ISO sheet
    # Change this name to match your exact tab name
    ws = spreadsheet.worksheet("ISO27001_Compliance_Matrix")
    data = ws.get_all_values()
    print(f"\n✅ ISO sheet loaded: {len(data)} rows")
    print(f"Row 1: {data[0]}")
    print(f"Row 2: {data[1]}")
    print(f"Row 3 (likely headers): {data[2]}")

except Exception as e:
    print(f"❌ Error: {e}")