# AxisResearcher

eBay Research and Listing Tool

## Overview

AxisResearcher is a Python tool for researching eBay listings, analyzing sales data, and creating optimized listings using the eBay Browse API, Trading API, and AI providers (OpenRouter, AWS Bedrock).

## Installation

Requirements: Python 3.x, pip

1. Install packages: `pip install -r requirements.txt`
2. Create `.env` file from `env_template.txt`
3. Add eBay API credentials from https://developer.ebay.com/my/keys
4. Add OpenRouter API key (optional, for AI optimization)
5. Complete OAuth setup (see Authentication section below)

## Authentication (eBay OAuth)

AxisResearcher uses two types of eBay OAuth tokens:

| Token                 | Purpose                                            | Lifetime   | How to get                         |
| --------------------- | -------------------------------------------------- | ---------- | ---------------------------------- |
| **Application token** | Browse API, Commerce Taxonomy (read-only)          | 2 hours    | Auto-minted via client credentials |
| **User token**        | Sell Inventory API, Trading API (write operations) | 2 hours    | Refreshed from refresh_token       |
| **Refresh token**     | Used to mint new user tokens                       | ~18 months | Obtained via user consent flow     |

### Normal operation: refreshing the user token

The user token expires every 2 hours. To get a fresh one:

```
python -m backend.ebay_cli refresh
```

Or programmatically:

```
python testing/test_update_tokens.py refresh-user
```

This uses your long-lived `refresh_token` (in `.env`) to mint a new short-lived `user_token`.

### When refresh stops working: full re-consent

The refresh token becomes **invalid** if you:

- Change your eBay password
- Revoke app consent in eBay account settings
- Let the refresh token expire (~18 months)

When this happens, you must redo the consent flow to get a new refresh token:

```bash
# Step 1: Generate consent URL and open in browser
python -m backend.refreshToken open-consent

# Step 2: Log into eBay, approve the consent
# You'll be redirected to your RuName URL with ?code=... in the query string

# Step 3: Copy the code value and exchange it (no quotes)
python testing/test_update_tokens.py exchange <paste_code_here>
```

This writes both a fresh `user_token` and `refresh_token` to `.env`.

### Verify token status

```
python testing/test_update_tokens.py verify
```

### Mint a fresh application token only

```
python testing/test_update_tokens.py mint-app
```

## Core Features

### Item Collection

<img width="1061" height="522" alt="image" src="https://github.com/user-attachments/assets/9f53fb9d-e637-4f83-8940-b72abcfa4d10" />

Collect all item IDs from a seller's inventory with automatic pagination.

```
python -m backend.ebay_cli collect <seller_username> [query] [limit]
```

Example: `python -m backend.ebay_cli collect ebaySeller "phone" 200`

Saves to: `Collected-Data/<seller_username>/<seller_username>_YYYYMMDD_HHMMSS.json`

### Sales Data Processing

<img width="1031" height="591" alt="image" src="https://github.com/user-attachments/assets/76f6f505-62eb-43f9-a792-6e8c51ab36af" />
<img width="1051" height="645" alt="image" src="https://github.com/user-attachments/assets/9332faa7-2048-4745-99ef-8bab0d127965" />

Process collected items to fetch sales data, extract sold quantities, and sort by performance.

```
python -m backend.ebay_cli process <seller_username> [limit] [output_filename]
```

Generates: Items sorted by estimated sold quantity, sales statistics, top 10 preview.

Saves to: `Collected-Data/<seller_username>/processed-sales-data/PROCESSED_*.json`

### AI Powered Listing Copy

Copy and optimize listings using AI. Generates SEO optimized titles (80 chars) and keyword rich descriptions.

```
python -m backend.ebay_cli copy <item_id_or_url>
```

Optimizations include: keyword rich SEO titles, material and color specifications, clean HTML formatting, removed manufacturer references.

## Additional Commands

| Command                                                             | Description                             |
| ------------------------------------------------------------------- | --------------------------------------- |
| `python -m backend.ebay_cli search <query>`                         | Search eBay items                       |
| `python -m backend.ebay_cli seller <username> [query] [limit]`      | Browse seller inventory                 |
| `python -m backend.ebay_cli item <item_id>`                         | Get complete item information           |
| `python -m backend.ebay_cli top [input_file] [top_n] [output_file]` | Extract top sellers from processed data |
| `python -m backend.ebay_cli refresh`                                | Refresh application + user tokens       |

## Quick Start Workflow

```bash
# 1. Collect competitor inventory
python -m backend.ebay_cli collect competitor_username

# 2. Process sales data
python -m backend.ebay_cli process competitor_username 100

# 3. Get top performers
python -m backend.ebay_cli top SalesExport.json 20

# 4. Optimize a listing
python -m backend.ebay_cli copy 123456789012
```

## Web App

The web frontend provides a UI for the copy → generate → create → upload workflow:

```
npm run dev          # starts both backend (port 5000) and frontend (port 4000)
```

## Configuration

### Required Environment Variables (.env)

| Variable            | Purpose                                          |
| ------------------- | ------------------------------------------------ |
| `client_id`         | eBay App Client ID                               |
| `client_secret`     | eBay App Client Secret                           |
| `redirect_uri`      | eBay App RuName (redirect URI for OAuth consent) |
| `application_token` | OAuth application token (auto-refreshed)         |
| `user_token`        | OAuth user token (refreshed from refresh_token)  |
| `refresh_token`     | Long-lived OAuth refresh token (~18 months)      |

### Optional

| Variable             | Purpose                                    |
| -------------------- | ------------------------------------------ |
| `openrouter_api_key` | For AI listing optimization via OpenRouter |
| `bedrock_api_key`    | For AWS Bedrock AI provider (alternate)    |

## Troubleshooting

### Authentication Errors (401)

1. First try refreshing: `python -m backend.ebay_cli refresh`
2. If that fails, your refresh token is likely revoked — redo the consent flow (see Authentication section above)

### Rate Limiting

Wait between retries (built-in delays included).

### Missing Sales Data

Normal for some items; appears in "without sales data" section.

### File Not Found

Ensure you run `collect` before `process`. Verify seller username matches folder names.

## Limitations

- Cannot do currency conversions yet
- Images do not generate square formats (will fix by cropping input to square)

## Things to prompt:

- need to fix selection mode after photos are generated
