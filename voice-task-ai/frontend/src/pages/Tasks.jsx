import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listTasks, completeTask } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import { Video } from 'lucide-react'

const FILTERS = [
  { value: '', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'completed', label: 'Completed' },
]

function TaskCard({ task, onComplete }) {
  const isOverdue =
    task.deadline && new Date(task.deadline) < new Date() && task.status === 'pending'

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-4 flex items-start justify-between">
      <div>
        <div className="flex items-center gap-2">
          <p className="font-medium text-gray-800">{task.title}</p>
          <StatusBadge status={isOverdue ? 'overdue' : task.status} />
        </div>
        {task.description && <p className="text-sm text-gray-500 mt-1">{task.description}</p>}
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-2 text-xs text-gray-400">
          {task.contact_name && <span>Contact: {task.contact_name}</span>}
          {task.deadline && <span>Deadline: {new Date(task.deadline).toLocaleString()}</span>}
          <span className="capitalize">Priority: {task.priority}</span>
        </div>
        {task.meeting_link && (
          <Link
            to={`/meeting/${task.id}`}
            className="inline-flex items-center gap-1.5 mt-2 text-xs font-medium text-indigo-600 hover:underline"
          >
            <Video size={14} />
            Join video meeting
          </Link>
        )}
      </div>
      {task.status !== 'completed' && (
        <button
          onClick={() => onComplete(task.id)}
          className="shrink-0 text-sm font-medium text-green-700 border border-green-300 hover:bg-green-50 px-3 py-1 rounded-lg"
        >
          Complete
        </button>
      )}
    </div>
  )
}

function Tasks() {
  const [tasks, setTasks] = useState([])
  const [filter, setFilter] = useState('')
  const [loading, setLoading] = useState(true)

  const refresh = (statusFilter = filter) => {
    setLoading(true)
    listTasks(statusFilter || undefined)
      .then((res) => setTasks(res.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => refresh(), []) // eslint-disable-line react-hooks/exhaustive-deps

  const handleFilterChange = (value) => {
    setFilter(value)
    refresh(value)
  }

  const handleComplete = async (id) => {
    await completeTask(id)
    refresh()
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Tasks</h1>
        <p className="text-gray-500 text-sm mt-1">Everything extracted from your voice notes as tasks.</p>
      </div>

      <div className="flex gap-2 mb-4">
        {FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => handleFilterChange(f.value)}
            className={`text-sm font-medium px-3 py-1.5 rounded-lg ${
              filter === f.value ? 'bg-indigo-600 text-white' : 'bg-white border border-gray-300 text-gray-600'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : tasks.length === 0 ? (
        <p className="text-sm text-gray-500">No tasks yet.</p>
      ) : (
        <div className="space-y-3">
          {tasks.map((task) => (
            <TaskCard key={task.id} task={task} onComplete={handleComplete} />
          ))}
        </div>
      )}
    </div>
  )
}

export default Tasks
