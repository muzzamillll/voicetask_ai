const INTENT_OPTIONS = [
  'task', 'reminder', 'order', 'payment', 'meeting',
  'appointment', 'follow_up', 'note', 'unknown',
]
const PRIORITY_OPTIONS = ['low', 'medium', 'high']

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="text-xs font-medium text-gray-500">{label}</span>
      {children}
    </label>
  )
}

const inputClass =
  'mt-1 w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500'

function ExtractionForm({ extraction, onChange }) {
  const update = (path, value) => {
    const next = structuredClone(extraction)
    let obj = next
    for (let i = 0; i < path.length - 1; i++) obj = obj[path[i]]
    obj[path[path.length - 1]] = value
    onChange(next)
  }

  return (
    <div className="space-y-4">
      {extraction.needs_clarification && (
        <div className="bg-amber-50 border border-amber-200 text-amber-800 text-sm rounded-lg p-3">
          <strong>AI needs clarification:</strong> {extraction.clarification_question || 'Some information is missing.'}
        </div>
      )}

      <div className="grid grid-cols-2 gap-4">
        <Field label="Intent">
          <select
            className={inputClass}
            value={extraction.intent}
            onChange={(e) => update(['intent'], e.target.value)}
          >
            {INTENT_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt.replace('_', ' ')}</option>
            ))}
          </select>
        </Field>
        <Field label="Priority">
          <select
            className={inputClass}
            value={extraction.priority}
            onChange={(e) => update(['priority'], e.target.value)}
          >
            {PRIORITY_OPTIONS.map((opt) => (
              <option key={opt} value={opt}>{opt}</option>
            ))}
          </select>
        </Field>
      </div>

      <Field label="Title">
        <input
          className={inputClass}
          value={extraction.title}
          onChange={(e) => update(['title'], e.target.value)}
        />
      </Field>

      <Field label="Description">
        <textarea
          className={inputClass}
          rows={2}
          value={extraction.description}
          onChange={(e) => update(['description'], e.target.value)}
        />
      </Field>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Contact name">
          <input
            className={inputClass}
            value={extraction.contact.name}
            onChange={(e) => update(['contact', 'name'], e.target.value)}
          />
        </Field>
        <Field label="Contact phone">
          <input
            className={inputClass}
            value={extraction.contact.phone}
            onChange={(e) => update(['contact', 'phone'], e.target.value)}
          />
        </Field>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Field label="Deadline date">
          <input
            type="date"
            className={inputClass}
            value={extraction.deadline.date}
            onChange={(e) => update(['deadline', 'date'], e.target.value)}
          />
        </Field>
        <Field label="Deadline time">
          <input
            type="time"
            className={inputClass}
            value={extraction.deadline.time}
            onChange={(e) => update(['deadline', 'time'], e.target.value)}
          />
        </Field>
        <Field label="Quantity">
          <input
            type="number"
            className={inputClass}
            value={extraction.quantity ?? ''}
            onChange={(e) => update(['quantity'], e.target.value === '' ? null : Number(e.target.value))}
          />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Amount (PKR)">
          <input
            type="number"
            className={inputClass}
            value={extraction.amount.value ?? ''}
            onChange={(e) =>
              update(['amount', 'value'], e.target.value === '' ? null : Number(e.target.value))
            }
          />
        </Field>
        <Field label="Location">
          <input
            className={inputClass}
            value={extraction.location}
            onChange={(e) => update(['location'], e.target.value)}
          />
        </Field>
      </div>

      <div className="grid grid-cols-2 gap-4 text-xs text-gray-400">
        <div>Language: <span className="text-gray-600">{extraction.language}</span></div>
        <div>Confidence: <span className="text-gray-600">{Math.round(extraction.confidence * 100)}%</span></div>
      </div>
    </div>
  )
}

export default ExtractionForm
