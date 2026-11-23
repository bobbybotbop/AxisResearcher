SITE_TYPE_WHITELISTED = "whitelisted"
SITE_TYPE_BLACKLISTED = "blacklisted"
SITE_TYPE_NEUTRAL = "neutral"

WHITELISTED_SITES = [
    "makerworld.com",
    "printables.com",
    "yeggi.com",
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
# Includes every blacklisted domain plus yeggi: yeggi stays whitelisted as a
# result source (its aggregator links are valid), but its own pages tend to
# crowd out the source sites it aggregates, so it's excluded from the query.
QUERY_EXCLUDED_SITES = BLACKLISTED_SITES + ["yeggi.com"]
