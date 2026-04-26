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
    <div className="mb-8 rounded-xl border border-border-default bg-surface-panel p-6 shadow-sm sm:p-8">
      <h2 className="mb-6 text-2xl font-semibold leading-snug text-text-primary sm:text-[1.8rem]">
        {listing.title || 'N/A'}
      </h2>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        <div className="flex flex-col gap-1">
          <span className="text-sm font-semibold text-text-muted">Item ID:</span>
          <span className="text-base text-text-primary">{listing.itemId || 'N/A'}</span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-sm font-semibold text-text-muted">Price:</span>
          <span className="text-base font-bold text-success">{formatPrice()}</span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-sm font-semibold text-text-muted">Category ID:</span>
          <span className="text-base text-text-primary">{listing.categoryId || 'N/A'}</span>
        </div>

        <div className="flex flex-col gap-1">
          <span className="text-sm font-semibold text-text-muted">Created:</span>
          <span className="text-base text-text-primary">{formatDate(listing.itemCreationDate)}</span>
        </div>

        {listing.estimatedSoldQuantity !== null && listing.estimatedSoldQuantity !== undefined && (
          <div className="flex flex-col gap-1">
            <span className="text-sm font-semibold text-text-muted">Estimated Sold:</span>
            <span className="text-base text-text-primary">{listing.estimatedSoldQuantity}</span>
          </div>
        )}
      </div>

      {listing.description && listing.description !== 'No description available' && (
        <div className="mt-6 border-t border-border-default pt-6">
          <h3 className="mb-2 text-lg text-text-primary">Description</h3>
          <p className="leading-relaxed text-text-muted">{listing.description}</p>
        </div>
      )}
    </div>
  )
}

export default ListingDetails
