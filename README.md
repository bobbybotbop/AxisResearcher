## eBay Result Count Script

This simple Python script searches eBay using the Finding API and prints the total number of results for a given keyword.

### Setup

1. Install Python 3.9+.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set your eBay App ID (Application Key):
   - Option A: Create a `.env` file in this folder with:

```
EBAY_APP_ID=your_ebay_app_id_here
# Optional: force environment; one of: sandbox | prod
EBAY_ENV=sandbox
```

- Option B: Set environment variable directly (PowerShell):

```powershell
setx EBAY_APP_ID "your_ebay_app_id_here"
# Optional: force environment; one of: sandbox | prod
setx EBAY_ENV sandbox
```

### Sandbox vs Production

- The script auto-detects sandbox if your App ID contains `-SBX-`.
- You can override by setting `EBAY_ENV` to `sandbox` or `prod`, or via `--env`.
- Default is production endpoint if no hint is found.

### Usage

Run the script with a keyword:

```bash
python ebay_search.py --q "nvidia rtx 4090"
```

Optional flags:

- `--env sandbox|prod` to force environment
- `--site EBAY-US|EBAY-GB|EBAY-DE` etc. to select GLOBAL-ID
- `--debug` to print endpoint, ack, and raw response on error

### Troubleshooting zero results

- If using a sandbox App ID, the sandbox often has little or no live data.
  - Try known generic keywords: `iphone`, `laptop`, `camera`.
  - Or force production (with a production App ID): `--env prod`.
- Switch site: `--site EBAY-GB` or `--site EBAY-DE` may produce different counts.
- Use `--debug` to confirm which endpoint and site are being used and to see the API ack.

### Notes

- This uses the eBay Finding API endpoint and only retrieves the total count, not item details.
- Ensure your App ID has access to the Finding API (and that you're hitting the correct environment).
