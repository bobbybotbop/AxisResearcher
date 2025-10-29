AxisResearcher
eBay Research and Listing Tool

Overview

AxisResearcher is a Python tool for researching eBay listings, analyzing sales data, and creating optimized listings using the eBay Browse API, Trading API, and OpenRouter AI.

[SCREENSHOT: Main interface or command examples]

Installation

Requirements: Python 3.x, python-dotenv, requests

1. Install packages: pip install python-dotenv requests
2. Create .env file from env_template.txt
3. Add eBay API credentials from https://developer.ebay.com/my/keys
4. Add OpenRouter API key (optional, for AI optimization)
5. Authenticate: e.bat refresh

Core Features

Item Collection
Collect all item IDs from a seller's inventory with automatic pagination.

Usage: e.bat collect <seller_username> [query] [limit]
Example: e.bat collect ebaySeller "phone" 200

Saves to: <seller_username>/<seller_username>_YYYYMMDD_HHMMSS.json

[SCREENSHOT: Collection process output]

Sales Data Processing
Process collected items to fetch sales data, extract sold quantities, and sort by performance.

Usage: e.bat process <seller_username> [limit] [output_filename]
Example: e.bat process ebaySeller 100

Generates:
  Items sorted by estimated sold quantity
  Sales statistics (total, average, highest)
  Top 10 preview

Saves to: <seller_username>/processed-sales-data/PROCESSED_*.json

[SCREENSHOT: Sales processing output and statistics]

Top Selling Items
Extract the top N selling items from processed data.

Usage: e.bat top [input_file] [top_n] [output_file]
Example: e.bat top SalesExport.json 50

[SCREENSHOT: Top items output]

AI Powered Listing Copy
Copy and optimize listings using AI. Generates SEO optimized titles (80 chars) and keyword rich descriptions.

Usage: e.bat copy <item_id_or_url>
Example: e.bat copy 123456789012

Optimizations include:
  Keyword rich SEO titles
  Material and color specifications
  Clean HTML formatting
  Removed manufacturer references

[SCREENSHOT: Listing copy and optimization output]

Additional Features

Search
  e.bat search <query> - Search eBay items

Seller Search
  e.bat seller <username> [query] [limit] - Browse seller inventory

Item Details
  e.bat item <item_id> - Get complete item information

Token Management
  e.bat refresh - Refresh OAuth tokens

[SCREENSHOT: Additional features examples]

Quick Start Workflow

1. Collect competitor inventory:
   e.bat collect competitor_username

2. Process sales data:
   e.bat process competitor_username 100

3. Get top performers:
   e.bat top SalesExport.json 20

4. Optimize a listing:
   e.bat copy 123456789012

[SCREENSHOT: Complete workflow example]

Configuration

Required Environment Variables (.env file):
  client_id - eBay Client ID
  client_secret - eBay Client Secret
  api_key - eBay API Key
  user_token - OAuth user token
  refresh_token - OAuth refresh token

Optional:
  openrouter_api_key - For AI listing optimization

Command Reference

collect <seller_username> [query] [limit]
  Collect item IDs from seller inventory

process <seller_username> [limit] [output_filename]
  Process collected items and generate sales data

top [input_file] [top_n] [output_file]
  Extract top selling items

copy <item_id_or_url>
  Copy and optimize listing with AI

search <query>
  Search eBay for items

seller <username> [query] [limit]
  Search items from specific seller

item <item_id>
  Get detailed item information

refresh
  Refresh OAuth tokens

Troubleshooting

Authentication Errors (401)
  Run: e.bat refresh and update .env with new tokens

Rate Limiting
  Wait between retries (built in delays included)

Missing Sales Data
  Normal for some items, appears in "without sales data" section

File Not Found
  Ensure you run "collect" before "process"
  Verify seller username matches folder names

[SCREENSHOT: Error handling examples]

Technical Notes

  Automatic pagination and rate limiting
  JSON exports with timestamped filenames
  Token refresh on expiration
  Progress tracking for batch operations

File Structure

<seller_username>/
  <seller_username>_YYYYMMDD_HHMMSS.json
  processed-sales-data/
    PROCESSED_<seller_username>_YYYYMMDD_HHMMSS.json

[SCREENSHOT: File structure diagram]
