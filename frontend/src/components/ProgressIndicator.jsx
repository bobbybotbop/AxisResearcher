function ProgressIndicator({ steps, currentStep, completedSteps = [], showProgressBar = true }) {
  if (!steps || steps.length === 0) {
    return null
  }

  const getStepStatus = (step) => {
    if (completedSteps.includes(step)) {
      return 'completed'
    } else if (currentStep === step) {
      return 'current'
    } else {
      return 'pending'
    }
  }

  const getStepIcon = (step) => {
    const status = getStepStatus(step)
    switch (status) {
      case 'completed':
        return <span className="progress-icon completed">✓</span>
      case 'current':
        return <span className="progress-icon current">
          <div className="spinner-small"></div>
        </span>
      default:
        return <span className="progress-icon pending">○</span>
    }
  }

  const completedCount = completedSteps.length
  const totalCount = steps.length
  const progressPercent = totalCount > 0 ? (completedCount / totalCount) * 100 : 0

  return (
    <div className="progress-indicator">
      {showProgressBar && (
        <div className="progress-bar-container">
          <div className="progress-bar" style={{ width: `${progressPercent}%` }}></div>
          <div className="progress-text">{completedCount} of {totalCount} complete</div>
        </div>
      )}
      <div className="progress-steps">
        {steps.map((step, index) => {
          const status = getStepStatus(step)
          return (
            <div key={index} className={`progress-step progress-step-${status}`}>
              {getStepIcon(step)}
              <span className="progress-step-label">{step}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ProgressIndicator
