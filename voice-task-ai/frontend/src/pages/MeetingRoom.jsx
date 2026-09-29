import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getTask, uploadVoiceNote, processVoiceNote, extractVoiceNote, confirmVoiceNote } from '../services/api'
import { ArrowLeft, Mic, Square } from 'lucide-react'

function loadJitsiScript() {
  return new Promise((resolve, reject) => {
    if (window.JitsiMeetExternalAPI) {
      resolve()
      return
    }
    const script = document.createElement('script')
    script.src = 'https://meet.jit.si/external_api.js'
    script.onload = resolve
    script.onerror = reject
    document.body.appendChild(script)
  })
}

function MeetingRoom() {
  const { taskId } = useParams()
  const [task, setTask] = useState(null)
  const [recording, setRecording] = useState(false)
  const [transcribing, setTranscribing] = useState(false)
  const [lastTranscript, setLastTranscript] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')

  const containerRef = useRef(null)
  const mediaRecorderRef = useRef(null)
  const chunksRef = useRef([])

  useEffect(() => {
    getTask(taskId).then((res) => setTask(res.data))
  }, [taskId])

  useEffect(() => {
    if (!task?.meeting_link || !containerRef.current) return

    const roomName = task.meeting_link.split('/').pop()

    loadJitsiScript().then(() => {
      // eslint-disable-next-line no-undef
      new JitsiMeetExternalAPI('meet.jit.si', {
        roomName,
        parentNode: containerRef.current,
        width: '100%',
        height: 500,
      })
    })
  }, [task])

  const startRecording = async () => {
    setErrorMsg('')
    setLastTranscript(null)
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []
      recorder.ondataavailable = (e) => chunksRef.current.push(e.data)
      recorder.onstop = handleRecordingStopped
      recorder.start()
      mediaRecorderRef.current = recorder
      setRecording(true)
    } catch (err) {
      setErrorMsg('Could not access your microphone. Check browser permissions.')
    }
  }

  const stopRecording = () => {
    mediaRecorderRef.current?.stop()
    mediaRecorderRef.current?.stream.getTracks().forEach((t) => t.stop())
    setRecording(false)
  }

  const handleRecordingStopped = async () => {
    setTranscribing(true)
    try {
      const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
      const file = new File([blob], `meeting-note-${Date.now()}.webm`, { type: 'audio/webm' })

      const uploadRes = await uploadVoiceNote(file)
      const noteId = uploadRes.data.id

      await processVoiceNote(noteId)
      const extractRes = await extractVoiceNote(noteId)
      const { extraction, recommended_action } = extractRes.data

      if (recommended_action === 'auto_create') {
        await confirmVoiceNote(noteId, extraction)
      }

      setLastTranscript(extraction)
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Recording could not be transcribed.')
    } finally {
      setTranscribing(false)
    }
  }

  return (
    <div className="p-8">
      <Link to="/tasks" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-gray-800 mb-4">
        <ArrowLeft size={16} /> Back to Tasks
      </Link>

      {task && <h1 className="text-2xl font-bold text-gray-900 mb-1">{task.title}</h1>}
      <p className="text-gray-500 text-sm mb-4">
        Recording captures YOUR microphone only, not other participants' audio.
      </p>

      <div ref={containerRef} className="rounded-xl overflow-hidden border border-gray-200 mb-4" />

      <div className="flex items-center gap-3">
        {!recording ? (
          <button
            onClick={startRecording}
            disabled={transcribing}
            className="flex items-center gap-2 bg-red-600 hover:bg-red-700 text-white text-sm font-medium px-4 py-2 rounded-lg disabled:opacity-50"
          >
            <Mic size={16} /> Start recording my mic
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="flex items-center gap-2 bg-gray-800 hover:bg-gray-900 text-white text-sm font-medium px-4 py-2 rounded-lg"
          >
            <Square size={16} /> Stop and transcribe
          </button>
        )}
        {transcribing && <span className="text-sm text-indigo-500 animate-pulse">Transcribing...</span>}
      </div>

      {errorMsg && (
        <div className="mt-4 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">{errorMsg}</div>
      )}

      {lastTranscript && (
        <div className="mt-4 bg-green-50 border border-green-200 text-green-800 text-sm rounded-lg p-3">
          <p className="font-medium mb-1">Captured and saved:</p>
          <p>{lastTranscript.title}</p>
          {lastTranscript.description && <p className="text-xs mt-1">{lastTranscript.description}</p>}
        </div>
      )}
    </div>
  )
}

export default MeetingRoom
