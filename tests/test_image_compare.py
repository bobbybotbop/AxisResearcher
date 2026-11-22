import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from PIL import Image

from backend.image_compare import find_matching_pairs


def _solid(color, size=(64, 64)):
    return Image.new("RGB", size, color)


def _gradient(size=(64, 64)):
    img = Image.new("RGB", size)
    for x in range(size[0]):
        for y in range(size[1]):
            img.putpixel((x, y), (x * 4 % 256, y * 4 % 256, (x + y) * 2 % 256))
    return img


def test_identical_images_match_with_zero_distance():
    pairs = find_matching_pairs([_gradient()], [_gradient()], threshold=10)
    assert pairs == [{"ebay_index": 0, "site_index": 0, "distance": 0}]


def test_different_images_do_not_match():
    pairs = find_matching_pairs([_solid((0, 0, 0))], [_gradient()], threshold=10)
    assert pairs == []


def test_compares_all_pairs_and_reports_indices():
    ebay = [_solid((0, 0, 0)), _gradient()]
    site = [_gradient(), _solid((0, 0, 0))]
    pairs = find_matching_pairs(ebay, site, threshold=10)
    assert pairs == [
        {"ebay_index": 0, "site_index": 1, "distance": 0},
        {"ebay_index": 1, "site_index": 0, "distance": 0},
    ]


def test_threshold_controls_matching():
    ebay = [_solid((0, 0, 0))]
    site = [_gradient()]
    assert find_matching_pairs(ebay, site, threshold=64) != []
    assert find_matching_pairs(ebay, site, threshold=0) == []
