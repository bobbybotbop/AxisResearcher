/**
 * Initial state for the Test Workflow tab (mock data path).
 * Single object replaces many parallel useState hooks in App.jsx.
 */

import type { TestWorkflowState } from "./types/workflow";

export function createTestWorkflowState(): TestWorkflowState {
  return {
    listingId: '',
    photos: [],
    categories: {},
    editableCategories: {},
    listing: null,
    loading: false,
    isConfirming: false,
    error: null,
    generatedImages: [],
    isRegenerating: false,
    useRealEbayUpload: false,
    isCreatingListing: false,
    listingData: null,
    uploadResult: null,
    currentSku: null,
    skippedPhotos: new Set(),
    pendingImagePromptModifier: "",
    pendingPhotoPrompt: "",
    isEditorOpen: false,
    editableTitle: '',
    isTrimmingTitle: false,
    isSavingTitle: false,
    editableDescription: '',
    isSavingDescription: false,
    isGeneratingText: false,
    textGenStatus: 'writing',
    textGenComplete: false,
    lightboxOpen: false,
    lightboxIndex: 0,
    uploadingSkus: new Set(),
    bgRemovedPhotos: {},
    customPrompt: "",
    selectedImagesForRegen: [],
    isTrimming: false,
    isAddingNewVersions: false,
    promptModifier: "",
  }
}
