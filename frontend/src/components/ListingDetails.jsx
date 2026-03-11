function ListingDetails({ listing }) {
  if (!listing) {
    return null
  }

  const formatPrice = () => {
    const price = listing.price
    const currency = listing.currency || 'USD'
    if (price === 'N/A' || price === null || price === undefined) {
      return 'N/A'
    }
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: currency,
    }).format(price)
  }

  const formatDate = (dateString) => {
    if (!dateString || dateString === 'N/A') {
      return 'N/A'
    }
    try {
      const date = new Date(dateString)
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      })
    } catch {
      return dateString
    }
  }

  return (
    <div className="mb-8 rounded-xl bg-white p-6 shadow-sm sm:p-8">
      <h2 className="mb-6 text-2xl font-semibold leading-snug text-gray-800 sm:text-[1.8rem]">
        {listing.title || 'N/A'}
      </h2>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div className="flex flex-col gap-1">
          <span className="text-sm font-semibold text-gray-600">Item ID:</span>
          <span className="text-base text-gray-800">{listing.itemId || 'N/A'}</span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-sm font-semibold text-gray-600">Price:</span>
          <span className="text-base font-bold text-success">{formatPrice()}</span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-sm font-semibold text-gray-600">Category ID:</span>
          <span className="text-base text-gray-800">{listing.categoryId || 'N/A'}</span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-sm font-semibold text-gray-600">Created:</span>
          <span className="text-base text-gray-800">{formatDate(listing.itemCreationDate)}</span>
        </div>

        {listing.estimatedSoldQuantity !== null && listing.estimatedSoldQuantity !== undefined && (
          <div className="flex flex-col gap-1">
            <span className="text-sm font-semibold text-gray-600">Estimated Sold:</span>
            <span className="text-base text-gray-800">{listing.estimatedSoldQuantity}</span>
          </div>
        )}
      </div>

      {listing.description && listing.description !== 'No description available' && (
        <div className="mt-6 border-t border-gray-200 pt-6">
          <h3 className="mb-2 text-lg text-gray-800">Description</h3>
          <p className="leading-relaxed text-gray-600">{listing.description}</p>
        </div>
      )}
    </div>
  )
}

export default ListingDetails
