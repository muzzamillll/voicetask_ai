import { useEffect, useState } from 'react'
import { listPayments, updatePaymentStatus } from '../services/api'
import StatusBadge from '../components/StatusBadge'
import StatCard from '../components/StatCard'

const PAYMENT_STATUSES = ['pending', 'paid', 'overdue']

function Payments() {
  const [payments, setPayments] = useState([])
  const [loading, setLoading] = useState(true)

  const refresh = () => {
    listPayments().then((res) => setPayments(res.data)).finally(() => setLoading(false))
  }

  useEffect(refresh, [])

  const handleStatusChange = async (id, newStatus) => {
    await updatePaymentStatus(id, newStatus)
    refresh()
  }

  const totalFor = (statusValue) =>
    payments
      .filter((p) => p.status === statusValue)
      .reduce((sum, p) => sum + (p.amount || 0), 0)

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Payments</h1>
        <p className="text-gray-500 text-sm mt-1">Payments extracted from your voice notes.</p>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <StatCard label="Total Pending" value={`PKR ${totalFor('pending').toLocaleString()}`} accent="text-amber-600" />
        <StatCard label="Total Paid" value={`PKR ${totalFor('paid').toLocaleString()}`} accent="text-green-600" />
        <StatCard label="Total Overdue" value={`PKR ${totalFor('overdue').toLocaleString()}`} accent="text-red-600" />
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : payments.length === 0 ? (
        <p className="text-sm text-gray-500">No payments yet.</p>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-2">Customer</th>
                <th className="text-left px-4 py-2">Amount</th>
                <th className="text-left px-4 py-2">Due Date</th>
                <th className="text-left px-4 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {payments.map((payment) => (
                <tr key={payment.id}>
                  <td className="px-4 py-3 font-medium text-gray-800">{payment.contact_name || '—'}</td>
                  <td className="px-4 py-3">
                    {payment.amount ? `${payment.currency} ${payment.amount.toLocaleString()}` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {payment.due_date ? new Date(payment.due_date).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <StatusBadge status={payment.status} />
                      <select
                        value={payment.status}
                        onChange={(e) => handleStatusChange(payment.id, e.target.value)}
                        className="text-xs border border-gray-300 rounded px-1.5 py-0.5"
                      >
                        {PAYMENT_STATUSES.map((s) => (
                          <option key={s} value={s}>{s}</option>
                        ))}
                      </select>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export default Payments
