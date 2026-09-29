const COLOR_MAP = {
  uploaded: 'bg-gray-100 text-gray-600',
  transcribing: 'bg-blue-100 text-blue-700',
  extracting: 'bg-blue-100 text-blue-700',
  review: 'bg-amber-100 text-amber-700',
  completed: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-700',
  pending: 'bg-amber-100 text-amber-700',
  in_progress: 'bg-blue-100 text-blue-700',
  cancelled: 'bg-red-100 text-red-700',
  confirmed: 'bg-blue-100 text-blue-700',
  delivered: 'bg-green-100 text-green-700',
  paid: 'bg-green-100 text-green-700',
  overdue: 'bg-red-100 text-red-700',
  auto_create: 'bg-green-100 text-green-700',
  confirm_review: 'bg-amber-100 text-amber-700',
  manual_review: 'bg-red-100 text-red-700',
}

function StatusBadge({ status }) {
  const classes = COLOR_MAP[status] || 'bg-gray-100 text-gray-600'
  const label = (status || '').replace(/_/g, ' ')
  return (
    <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium capitalize ${classes}`}>
      {label}
    </span>
  )
}

export default StatusBadge
