from backend.copyScripts.create_image import ImageType

TITLE_MIN_LEN = 75
TITLE_MAX_LEN = 80
TITLE_TARGET_LEN = 80
TITLE_MAX_ATTEMPTS = 3

ANGLE_VARIANTS = [
    "45 degree left",
    "45 degree right",
    "90 degree left",
    "90 degree right",
    "top",
]

PROMPT_TYPES = {"title", "description", "image"}

SKU_PREFIX = "AXIS_"
MANUAL_SKU_PREFIX = "MANUAL_"

SKIP_CATEGORIES = ["real_world_image", "edited_image"]

VALID_IMAGE_CATEGORIES = [
    "edited_image",
    "bad_image",
    "real_world_image",
    "professional_image",
]

CATEGORY_TO_IMAGE_TYPE = {
    "bad_image": ImageType.REAL_WORLD,
    "professional_image": ImageType.PROFESSIONAL,
}

EBAY_STATUS_NOT_FOUND = "not_found"
