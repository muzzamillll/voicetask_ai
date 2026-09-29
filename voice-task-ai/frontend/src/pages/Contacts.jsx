import { useEffect, useState } from 'react'
import { listContacts, createContact, updateContact, deleteContact } from '../services/api'

function Contacts() {
  const [contacts, setContacts] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({ name: '', phone: '', notes: '' })
  const [editingId, setEditingId] = useState(null)

  const refresh = () => {
    listContacts().then((res) => setContacts(res.data)).finally(() => setLoading(false))
  }

  useEffect(refresh, [])

  const resetForm = () => {
    setForm({ name: '', phone: '', notes: '' })
    setEditingId(null)
    setShowForm(false)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return
    if (editingId) {
      await updateContact(editingId, form)
    } else {
      await createContact(form)
    }
    resetForm()
    refresh()
  }

  const startEdit = (contact) => {
    setForm({ name: contact.name, phone: contact.phone || '', notes: contact.notes || '' })
    setEditingId(contact.id)
    setShowForm(true)
  }

  const handleDelete = async (id) => {
    await deleteContact(id)
    refresh()
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Contacts</h1>
          <p className="text-gray-500 text-sm mt-1">
            People mentioned in your voice notes are saved here automatically — you can also add them manually.
          </p>
        </div>
        <button
          onClick={() => (showForm ? resetForm() : setShowForm(true))}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
        >
          {showForm ? 'Cancel' : 'Add contact'}
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-5 mb-6 space-y-3">
          <div className="grid grid-cols-2 gap-4">
            <input
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
              placeholder="Name"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
            <input
              className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
              placeholder="Phone"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
            />
          </div>
          <textarea
            className="w-full rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
            placeholder="Notes (optional)"
            rows={2}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
          <button
            type="submit"
            className="bg-green-600 hover:bg-green-700 text-white text-sm font-medium px-4 py-1.5 rounded-lg"
          >
            {editingId ? 'Save changes' : 'Add contact'}
          </button>
        </form>
      )}

      {loading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : contacts.length === 0 ? (
        <p className="text-sm text-gray-500">No contacts yet.</p>
      ) : (
        <div className="bg-white rounded-xl border border-gray-200 divide-y divide-gray-100">
          {contacts.map((contact) => (
            <div key={contact.id} className="px-5 py-3 flex items-center justify-between">
              <div>
                <p className="font-medium text-gray-800">{contact.name}</p>
                <p className="text-xs text-gray-400 mt-0.5">
                  {contact.phone || 'No phone on file'}
                  {contact.notes ? ` · ${contact.notes}` : ''}
                </p>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => startEdit(contact)}
                  className="text-xs font-medium text-indigo-600 hover:underline"
                >
                  Edit
                </button>
                <button
                  onClick={() => handleDelete(contact.id)}
                  className="text-xs font-medium text-red-600 hover:underline"
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default Contacts
