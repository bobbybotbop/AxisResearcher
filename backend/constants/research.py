# Constants for the Copy Seller research pipeline (Testing tab).

DAILY_API_BUDGET = 5000
# Seller setup = one getItemIds page (conservative: sellers can need several).
SELLER_SETUP_CALLS = 5

# Title-simplification defaults (ticket 07). Editable in the Testing tab via
# /api/research/title-simplification; persisted in listingPreferences.json.
DEFAULT_TITLE_MAX_WORDS = 6
# Common eBay sales filler: quantity/pack terms, colors, condition, and brand
# filler that make a search phrase too specific to return results.
DEFAULT_TITLE_STOPWORDS = [
    # quantity / pack / lot
    "lot", "pack", "set", "pair", "bundle", "bulk", "wholesale", "case",
    "qty", "quantity", "pcs", "pc", "piece", "pieces", "count", "ct",
    # condition
    "new", "used", "like", "mint", "condition", "brand", "sealed", "open",
    "box", "oem", "genuine", "original", "authentic", "refurbished", "renewed",
    # colors
    "red", "orange", "yellow", "green", "blue", "purple", "pink", "black",
    "white", "gray", "grey", "brown", "gold", "silver", "beige", "multicolor",
    # sales filler
    "free", "shipping", "sale", "hot", "best", "top", "deal", "cheap",
    "premium", "quality", "gift", "men", "women", "kids", "adult",
    "for", "with", "and", "the", "of", "a", "an",
]
