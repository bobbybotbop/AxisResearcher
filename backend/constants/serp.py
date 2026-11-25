SITE_TYPE_WHITELISTED = "whitelisted"
SITE_TYPE_BLACKLISTED = "blacklisted"
SITE_TYPE_NEUTRAL = "neutral"

WHITELISTED_SITES = [
    "makerworld.com",
    "printables.com",
    "cults3d.com",
    "thingiverse.com",
    "thangs.com",
]

BLACKLISTED_SITES = [
    "ebay.com",
    "amazon.com",
    "walmart.com",
    "etsy.com",
    "aliexpress.com",
    "temu.com",
    "mercari.com",
    "poshmark.com",
    "reddit.com",
]

# Domains excluded from the text-search query itself via -site: clauses.
# Includes every blacklisted domain plus yeggi: yeggi is an aggregator whose
# pages crowd out the source sites it aggregates and have no downloader, so
# it's excluded from the query entirely.
QUERY_EXCLUDED_SITES = BLACKLISTED_SITES + ["yeggi.com"]
