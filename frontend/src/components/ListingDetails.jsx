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
    <div className="listing-details">
      <h2 className="listing-title">{listing.title || 'N/A'}</h2>
      
      <div className="listing-info-grid">
        <div className="info-item">
          <span className="info-label">Item ID:</span>
          <span className="info-value">{listing.itemId || 'N/A'}</span>
        </div>
        
        <div className="info-item">
          <span className="info-label">Price:</span>
          <span className="info-value price">{formatPrice()}</span>
        </div>
        
        <div className="info-item">
          <span className="info-label">Category ID:</span>
          <span className="info-value">{listing.categoryId || 'N/A'}</span>
        </div>
        
        <div className="info-item">
          <span className="info-label">Created:</span>
          <span className="info-value">{formatDate(listing.itemCreationDate)}</span>
        </div>
        
        {listing.estimatedSoldQuantity !== null && listing.estimatedSoldQuantity !== undefined && (
          <div className="info-item">
            <span className="info-label">Estimated Sold:</span>
            <span className="info-value">{listing.estimatedSoldQuantity}</span>
          </div>
        )}
      </div>

      {listing.description && listing.description !== 'No description available' && (
        <div className="listing-description">
          <h3>Description</h3>
          <p>{listing.description}</p>
        </div>
      )}
    </div>
  )
}

export default ListingDetails
