import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Sidebar from './components/Sidebar'
import Dashboard from './pages/Dashboard'
import VoiceNotes from './pages/VoiceNotes'
import Tasks from './pages/Tasks'
import Orders from './pages/Orders'
import Payments from './pages/Payments'
import Contacts from './pages/Contacts'
import Analytics from './pages/Analytics'
import MeetingRoom from './pages/MeetingRoom'

function App() {
  return (
    <BrowserRouter>
      <div className="flex min-h-screen bg-gray-50">
        <Sidebar />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/voice-notes" element={<VoiceNotes />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/orders" element={<Orders />} />
            <Route path="/payments" element={<Payments />} />
            <Route path="/contacts" element={<Contacts />} />
            <Route path="/analytics" element={<Analytics />} />
            <Route path="/meeting/:taskId" element={<MeetingRoom />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App
