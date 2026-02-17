/**
 * Mock data for the Test Workflow tab.
 * Matches the shapes used throughout the Create Listing workflow.
 */

// Placeholder image URLs - use picsum.photos for reliable placeholders
const MOCK_PHOTOS = [
  'https://picsum.photos/seed/axis1/400/400',
  'https://picsum.photos/seed/axis2/400/400',
  'https://picsum.photos/seed/axis3/400/400',
  'https://picsum.photos/seed/axis4/400/400',
  'https://picsum.photos/seed/axis5/400/400',
]

// Categories for each photo URL
const MOCK_CATEGORIES = Object.fromEntries(
  MOCK_PHOTOS.map((url, i) => {
    const cats = ['bad_image', 'professional_image', 'real_world_image', 'edited_image']
    return [url, cats[i % cats.length]]
  })
)

// Original eBay listing shape (from fetch)
export const MOCK_LISTING = {
  title: 'Test Product - Mock Listing for Workflow Testing',
  itemId: '123456789012',
  price: 12.99,
  currency: 'USD',
  categoryId: '177906',
  description: 'This is a mock description for testing the workflow. It includes placeholder text to verify the listing details display correctly.',
  itemCreationDate: '2026-02-16T12:00:00.000Z',
  estimatedSoldQuantity: 42,
}

// Mock generated images (AI-generated output simulation)
export const MOCK_GENERATED_IMAGES = [
  'https://picsum.photos/seed/gen1/400/400',
  'https://picsum.photos/seed/gen2/400/400',
  'https://picsum.photos/seed/gen3/400/400',
  'https://picsum.photos/seed/gen4/400/400',
]

// Full listing data shape (JSON file structure)
export const MOCK_LISTING_DATA = {
  sku: 'AXIS_TEST_001',
  createdDateTime: new Date().toISOString().slice(0, 19),
  inventoryItem: {
    availability: {
      shipToLocationAvailability: { quantity: 10 },
    },
    condition: 'NEW',
    packageWeightAndSize: {
      weight: { value: '0.5', unit: 'POUND' },
      dimensions: { length: '8', width: '6', height: '2', unit: 'INCH' },
    },
    product: {
      title: 'Test Product - Mock Listing for Workflow Testing',
      description:
        '<p>This is a mock description for testing the workflow. It includes placeholder text to verify the listing details display correctly.</p>',
      aspects: {
        Brand: ['Test Brand'],
        Color: ['Black'],
        Type: ['Test Type'],
      },
      imageUrls: MOCK_GENERATED_IMAGES,
    },
  },
  offer: {
    marketplaceId: 'EBAY_US',
    format: 'FIXED_PRICE',
    quantity: 10,
    pricingSummary: {
      price: { value: '12.99', currency: 'USD' },
    },
    listingDuration: 'GTC',
    categoryId: '177906',
    merchantLocationKey: 'TestLocation',
    listingPolicies: {
      fulfillmentPolicyId: '123456789',
      paymentPolicyId: '123456789',
      returnPolicyId: '123456789',
    },
  },
}

// Upload result shape
export const MOCK_UPLOAD_RESULT = {
  listingId: '110123456789',
  ebayId: '110123456789',
  href: 'https://www.ebay.com/itm/110123456789',
}

// Export a combined object for convenience
export const MOCK_DATA = {
  photos: MOCK_PHOTOS,
  categories: MOCK_CATEGORIES,
  listing: MOCK_LISTING,
  generatedImages: MOCK_GENERATED_IMAGES,
  listingData: MOCK_LISTING_DATA,
  uploadResult: MOCK_UPLOAD_RESULT,
  sku: 'AXIS_TEST_001',
}

export { MOCK_PHOTOS, MOCK_CATEGORIES }
