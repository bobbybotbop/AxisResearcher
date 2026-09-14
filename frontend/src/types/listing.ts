export interface Listing {
  title: string;
  itemId: string;
  price: number | string;
  currency?: string;
  categoryId: string;
  description: string;
  imageUrls?: string[];
  ebayListingId?: string;
  sku?: string;
  quantity?: number;
  createdAt?: string;
  updatedAt?: string;
  imageModel?: string;
  textModel?: string;
  sourceUrl?: string;
  [key: string]: unknown;
}

export interface ModelOption {
  value: string;
  label: string;
  provider?: string;
  inputCostPer1M?: number;
  outputCostPer1M?: number;
  costPerImage?: number;
}

export interface ProgressState {
  isActive: boolean;
  currentStep: string | null;
  completedSteps: string[];
  totalSteps: string[];
}

export interface ImageGenProgress {
  isActive: boolean;
  taskId: string | null;
  total: number;
  completed: number;
  currentGenerating: string[];
}
