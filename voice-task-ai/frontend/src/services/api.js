import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// --- Voice notes ---
export const uploadVoiceNote = (file) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post('/api/voice-notes/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export const listVoiceNotes = () => api.get('/api/voice-notes')
export const getVoiceNote = (id) => api.get(`/api/voice-notes/${id}`)
export const deleteVoiceNote = (id) => api.delete(`/api/voice-notes/${id}`)
export const processVoiceNote = (id, language) =>
  api.post(`/api/voice-notes/process/${id}`, null, { params: language ? { language } : {} })
export const extractVoiceNote = (id) => api.post(`/api/voice-notes/extract/${id}`)
export const translateVoiceNote = (id) => api.post(`/api/voice-notes/translate/${id}`)
export const confirmVoiceNote = (id, extraction) =>
  api.post(`/api/voice-notes/confirm/${id}`, extraction)

// --- Tasks ---
export const listTasks = (statusFilter) =>
  api.get('/api/tasks', { params: statusFilter ? { status_filter: statusFilter } : {} })
export const getTask = (id) => api.get(`/api/tasks/${id}`)
export const completeTask = (id) => api.post(`/api/tasks/${id}/complete`)
export const deleteTask = (id) => api.delete(`/api/tasks/${id}`)

// --- Orders ---
export const listOrders = () => api.get('/api/orders')
export const updateOrderStatus = (id, status) => api.put(`/api/orders/${id}/status`, { status })

// --- Payments ---
export const listPayments = () => api.get('/api/payments')
export const updatePaymentStatus = (id, status) => api.put(`/api/payments/${id}/status`, { status })

// --- Contacts ---
export const listContacts = () => api.get('/api/contacts')
export const createContact = (data) => api.post('/api/contacts', data)
export const updateContact = (id, data) => api.put(`/api/contacts/${id}`, data)
export const deleteContact = (id) => api.delete(`/api/contacts/${id}`)

export default api
