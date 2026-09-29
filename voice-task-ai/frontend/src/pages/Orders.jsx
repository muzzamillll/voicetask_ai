import { useEffect, useState } from 'react'
import { listOrders, updateOrderStatus } from '../services/api'
import StatusBadge from '../components/StatusBadge'

const ORDER_STATUSES = ['pending', 'confirmed', 'delivered', 'cancelled']

function Orders() {
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)

  const refresh = () => {
    listOrders().then((res) => setOrders(res.data)).finally(() => setLoading(false))
  }

  useEffect(refresh, [])

  const handleStatusChange = async (id, newStatus) => {
    await updateOrderStatus(id, newStatus)
    refresh()
  }

  return (
    <div className="p-8">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Orders</h1>
        <p className="text-gray-500 text-sm mt-1">Orders extracted from your voice notes.</p>
      </div>

      {loading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : orders.length === 0 ? (
        <p className="text-sm text-gray-500">No orders yet.</p>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-gray-500 text-xs uppercase">
              <tr>
                <th className="text-left px-4 py-2">Order</th>
                <th className="text-left px-4 py-2">Customer</th>
                <th className="text-left px-4 py-2">Qty</th>
                <th className="text-left px-4 py-2">Amount</th>
                <th className="text-left px-4 py-2">Delivery</th>
                <th className="text-left px-4 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {orders.map((order) => (
                <tr key={order.id}>
                  <td className="px-4 py-3 font-medium text-gray-800">#{order.id}</td>
                  <td className="px-4 py-3">{order.customer_name || '—'}</td>
                  <td className="px-4 py-3">{order.quantity ?? '—'}</td>
                  <td className="px-4 py-3">
                    {order.amount ? `${order.currency} ${order.amount.toLocaleString()}` : '—'}
                  </td>
                  <td className="px-4 py-3">
                    {order.delivery_date ? new Date(order.delivery_date).toLocaleDateString() : '—'}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex items-center gap-2">
                      <StatusBadge status={order.status} />
                      <select
                        value={order.status}
                        onChange={(e) => handleStatusChange(order.id, e.target.value)}
                        className="text-xs border border-gray-300 rounded px-1.5 py-0.5"
                      >
                        {ORDER_STATUSES.map((s) => (
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

export default Orders
