/**
 * Initial state for the Test Workflow tab (mock data path).
 * Single object replaces many parallel useState hooks in App.jsx.
 */
export function createTestWorkflowState() {
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
    customPrompt: '',
    selectedImagesForRegen: [],
    isRegenerating: false,
    isTrimming: false,
    isAddingNewVersions: false,
    useRealEbayUpload: false,
    isCreatingListing: false,
    listingData: null,
    uploadResult: null,
    currentSku: null,
    skippedPhotos: new Set(),
    useOriginalPhotos: new Set(),
    promptModifier: '',
    isEditorOpen: false,
    editableTitle: '',
    isTrimmingTitle: false,
    isSavingTitle: false,
    editableDescription: '',
    isSavingDescription: false,
    lightboxOpen: false,
    lightboxIndex: 0,
    fetchProgress: {
      isActive: false,
      currentStep: null,
      completedSteps: [],
      totalSteps: [],
    },
    imageGenProgress: {
      isActive: false,
      taskId: null,
      total: 0,
      completed: 0,
      currentGenerating: [],
    },
    createListingProgress: {
      isActive: false,
      currentStep: null,
      completedSteps: [],
      totalSteps: [],
    },
    uploadProgress: {
      isActive: false,
      currentStep: null,
      completedSteps: [],
      totalSteps: [],
    },
    uploadingSkus: new Set(),
  }
}
