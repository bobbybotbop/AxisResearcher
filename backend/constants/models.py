DEFAULT_TEXT_MODEL = "deepseek/deepseek-v4-flash"
DEFAULT_IMAGE_MODEL = "bytedance-seed/seedream-5-0-lite"
DEFAULT_CLASSIFIER_MODEL = "bytedance-seed/seed-1.6-flash"

# Per-model minimum output sizes. When the requested resolution is smaller than
# a model's minimum, the model's default is used instead.
MODEL_DEFAULT_SIZES = {
    "bytedance-seed/seedream-5-0-lite": "2048x2048",
}

# Maps ImageType.value string -> prompt filename under prompts/image/
DEFAULT_IMAGE_PROMPTS = {
    "PROFESSIONAL": "generateImageFromProfessional.txt",
    "REAL_WORLD": "generateImageFromWorld.txt",
    "ANGLE_VARIANT": "generateImageAngleVariant.txt",
    "EXPERIMENTAL": "experimental.txt",
}
