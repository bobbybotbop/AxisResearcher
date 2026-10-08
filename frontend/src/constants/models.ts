import type { ModelOption } from "../types/listing";

export type ImageModelOption = ModelOption & { defaultSize?: string };

export const DEFAULT_TEXT_MODEL_OPTIONS: ModelOption[] = [
  {
    value: "deepseek/deepseek-v4-flash",
    label: "DeepSeek V4 Flash",
    provider: "openrouter",
    inputCostPer1M: 0.13,
    outputCostPer1M: 0.4,
  },
];

export const PROVIDER_LABELS: Record<string, string> = {
  openrouter: "OpenRouter",
  bedrock: "Bedrock",
};

export const IMAGE_MODEL_OPTIONS: ImageModelOption[] = [
  {
    value: "sourceful/riverflow-v2-fast",
    label: "Riverflow V2 Fast",
    costPerImage: 0.019,
  },
  {
    value: "sourceful/riverflow-v2.5-fast",
    label: "Riverflow V2.5 Fast",
    costPerImage: 0.019,
  },
  {
    value: "google/gemini-3.1-flash-image",
    label: "Gemini 3.1 Flash Image",
    inputCostPer1M: 0.5,
    outputCostPer1M: 3.0,
  },
  {
    value: "google/gemini-3.1-flash-lite-image",
    label: "Gemini 3.1 Flash Lite Image",
    inputCostPer1M: 0.25,
    outputCostPer1M: 1.5,
  },
  {
    value: "bytedance-seed/seedream-5-0-lite",
    label: "Seedream 5.0 Lite",
    costPerImage: 0.035,
    defaultSize: "2048x2048",
  },
  {
    value: "bytedance-seed/seedream-4.5",
    label: "Seedream 4.5",
    costPerImage: 0.04,
  },
];

export const CLASSIFIER_MODEL_OPTIONS: ModelOption[] = [
  {
    value: "bytedance-seed/seed-1.6-flash",
    label: "ByteDance Seed 1.6 Flash",
    inputCostPer1M: 0.1,
    outputCostPer1M: 0.1,
  },
];
