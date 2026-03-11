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
        return (
          <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-green-500 text-sm font-bold text-white">
            ✓
          </span>
        )
      case 'current':
        return (
          <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-primary text-sm font-bold text-white">
            <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
          </span>
        )
      default:
        return (
          <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full border-2 border-gray-300 bg-gray-200 text-sm font-bold text-gray-500">
            ○
          </span>
        )
    }
  }

  const completedCount = completedSteps.length
  const totalCount = steps.length
  const progressPercent = totalCount > 0 ? (completedCount / totalCount) * 100 : 0

  return (
    <div className="my-5 rounded-lg border border-gray-200 bg-gray-50 p-4">
      {showProgressBar && (
        <div className="relative mb-4 h-6 w-full overflow-hidden rounded-xl bg-gray-200">
          <div
            className="h-full min-w-[2%] rounded-xl bg-gradient-to-r from-green-500 to-green-600 transition-[width] duration-300"
            style={{ width: `${progressPercent}%` }}
          />
          <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-sm font-semibold text-gray-800">
            {completedCount} of {totalCount} complete
          </div>
        </div>
      )}
      <div className="flex flex-col gap-2.5">
        {steps.map((step, index) => {
          const status = getStepStatus(step)
          const statusColors = {
            completed: 'text-green-600',
            current: 'font-semibold text-primary',
            pending: 'text-gray-500',
          }
          return (
            <div
              key={index}
              className={`flex items-center gap-3 py-2 text-[0.95rem] ${statusColors[status]}`}
            >
              {getStepIcon(step)}
              <span className="flex-1">{step}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default ProgressIndicator
