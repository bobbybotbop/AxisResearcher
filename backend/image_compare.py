"""Perceptual-hash image comparison for Image Confirmation.

Compares eBay listing photos against a 3D file site's gallery images using
pHash (64-bit). A pair matches when its hash distance is below the threshold.
"""

import imagehash

DEFAULT_THRESHOLD = 10


def find_matching_pairs(ebay_images, site_images, threshold=DEFAULT_THRESHOLD):
    """Compare every eBay × site image pair by pHash distance.

    Args:
        ebay_images: list of PIL.Image from the eBay listing.
        site_images: list of PIL.Image from the 3D file site page.
        threshold: maximum pHash distance (inclusive) for a pair to match.

    Returns:
        list of {"ebay_index", "site_index", "distance"} for each pair at or
        below the threshold, ordered by eBay index then site index.
    """
    ebay_hashes = [imagehash.phash(img) for img in ebay_images]
    site_hashes = [imagehash.phash(img) for img in site_images]

    pairs = []
    for ebay_index, ebay_hash in enumerate(ebay_hashes):
        for site_index, site_hash in enumerate(site_hashes):
            distance = ebay_hash - site_hash
            if distance <= threshold:
                pairs.append({
                    "ebay_index": ebay_index,
                    "site_index": site_index,
                    "distance": distance,
                })
    return pairs
