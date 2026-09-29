import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend,
} from 'recharts'
import api from '../services/api'
import StatCard from '../components/StatCard'

const COLORS = ['#4F46E5', '#059669', '#D97706', '#DC2626', '#7C3AED', '#0891B2', '#DB2777']

function Analytics() {
  const [summary, setSummary] = useState(null)
  const [intents, setIntents] = useState([])
  const [languages, setLanguages] = useState([])
  const [perDay, setPerDay] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get('/api/analytics/summary'),
      api.get('/api/analytics/intents'),
      api.get('/api/analytics/languages'),
      api.get('/api/analytics/voice-notes-per-day'),
    ])
      .then(([s, i, l, p]) => {
        setSummary(s.data)
        setIntents(i.data)
        setLanguages(l.data)
        setPerDay(p.data)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return <div className="p-8 text-gray-500">Loading analytics...</div>
  }

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
        <p className="text-gray-500 text-sm mt-1">How your voice notes are turning into action.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <StatCard label="Voice Notes" value={summary.total_voice_notes} />
        <StatCard label="Tasks" value={summary.total_tasks} />
        <StatCard label="Completed Tasks" value={summary.completed_tasks} accent="text-green-600" />
        <StatCard label="Orders" value={summary.total_orders} />
        <StatCard label="Payments" value={summary.total_payments} />
      </div>

      <StatCard
        label="Average AI Confidence"
        value={summary.average_confidence != null ? `${Math.round(summary.average_confidence * 100)}%` : '—'}
        accent="text-indigo-600"
      />

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Intent Distribution</h2>
          {intents.length === 0 ? (
            <p className="text-sm text-gray-500">No data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={intents}
                  dataKey="count"
                  nameKey="intent"
                  cx="50%"
                  cy="50%"
                  outerRadius={90}
                  label={({ intent, count }) => `${intent} (${count})`}
                >
                  {intents.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h2 className="font-semibold text-gray-800 mb-4">Language Distribution</h2>
          {languages.length === 0 ? (
            <p className="text-sm text-gray-500">No data yet.</p>
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={languages}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="language" tick={{ fontSize: 12 }} />
                <YAxis allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="count" fill="#4F46E5" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h2 className="font-semibold text-gray-800 mb-4">Voice Notes Per Day (last 14 days)</h2>
        {perDay.length === 0 ? (
          <p className="text-sm text-gray-500">No data yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={perDay}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="date" tick={{ fontSize: 12 }} />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="count" name="Voice Notes" stroke="#4F46E5" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  )
}

export default Analytics
