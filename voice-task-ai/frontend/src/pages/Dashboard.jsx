import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { listVoiceNotes, listTasks, listOrders, listPayments } from '../services/api'
import StatCard from '../components/StatCard'
import StatusBadge from '../components/StatusBadge'

function Dashboard() {
  const [voiceNotes, setVoiceNotes] = useState([])
  const [tasks, setTasks] = useState([])
  const [orders, setOrders] = useState([])
  const [payments, setPayments] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([listVoiceNotes(), listTasks(), listOrders(), listPayments()])
      .then(([vn, t, o, p]) => {
        setVoiceNotes(vn.data)
        setTasks(t.data)
        setOrders(o.data)
        setPayments(p.data)
      })
      .catch(() => setError('Could not reach the backend. Is uvicorn running?'))
      .finally(() => setLoading(false))
  }, [])

  const pendingPaymentsTotal = payments
    .filter((p) => p.status === 'pending')
    .reduce((sum, p) => sum + (p.amount || 0), 0)

  const completedTasksCount = tasks.filter((t) => t.status === 'completed').length

  if (loading) {
    return <div className="p-8 text-gray-500">Loading dashboard...</div>
  }

  if (error) {
    return (
      <div className="p-8">
        <div className="bg-red-50 border border-red-200 text-red-700 rounded-lg p-4 text-sm">
          {error}
        </div>
      </div>
    )
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-500 text-sm mt-1">Overview of your voice-driven tasks, orders, and payments.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="Total Voice Notes" value={voiceNotes.length} />
        <StatCard label="Tasks" value={tasks.length} />
        <StatCard label="Completed Tasks" value={completedTasksCount} accent="text-green-600" />
        <StatCard label="Orders" value={orders.length} />
        <StatCard
          label="Pending Payments"
          value={`PKR ${pendingPaymentsTotal.toLocaleString()}`}
          accent="text-amber-600"
        />
      </div>

      <div className="bg-white rounded-xl border border-gray-200">
        <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between">
          <h2 className="font-semibold text-gray-800">Recent Voice Notes</h2>
          <Link to="/voice-notes" className="text-sm text-indigo-600 hover:underline">
            View all
          </Link>
        </div>
        {voiceNotes.length === 0 ? (
          <p className="p-5 text-sm text-gray-500">
            No voice notes yet. Go to Voice Notes to upload your first one.
          </p>
        ) : (
          <div className="divide-y divide-gray-100">
            {voiceNotes.slice(0, 8).map((note) => (
              <div key={note.id} className="px-5 py-3 flex items-center justify-between text-sm">
                <div>
                  <p className="text-gray-800 font-medium">Voice note #{note.id}</p>
                  <p className="text-gray-400 text-xs mt-0.5">
                    {new Date(note.created_at).toLocaleString()}
                  </p>
                </div>
                <StatusBadge status={note.processing_status} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default Dashboard
