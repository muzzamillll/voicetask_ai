import { useEffect, useState } from 'react'
import {
  listVoiceNotes,
  uploadVoiceNote,
  processVoiceNote,
  extractVoiceNote,
  confirmVoiceNote,
  translateVoiceNote,
} from '../services/api'
import StatusBadge from '../components/StatusBadge'
import ExtractionForm from '../components/ExtractionForm'

const LANGUAGE_OPTIONS = [
  { value: '', label: 'Auto-detect' },
  { value: 'Urdu', label: 'Urdu' },
  { value: 'Sindhi', label: 'Sindhi' },
  { value: 'Siraiki', label: 'Siraiki' },
  { value: 'English', label: 'English' },
]

function buildConfirmPayload(extraction) {
  const payload = structuredClone(extraction)
  const { date, time } = payload.deadline
  if (date && time) {
    payload.deadline.datetime = `${date}T${time}:00`
    payload.deadline.is_specific = true
  } else if (date) {
    payload.deadline.datetime = `${date}T00:00:00`
    payload.deadline.is_specific = false
  } else {
    payload.deadline.datetime = ''
    payload.deadline.is_specific = false
  }
  return payload
}

function VoiceNotes() {
  const [notes, setNotes] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [selectedId, setSelectedId] = useState(null)
  const [language, setLanguage] = useState('')
  const [busyAction, setBusyAction] = useState('')
  const [extraction, setExtraction] = useState(null)
  const [recommendedAction, setRecommendedAction] = useState(null)
  const [confirmedRecord, setConfirmedRecord] = useState(null)
  const [errorMsg, setErrorMsg] = useState('')
  const [autoProcessingId, setAutoProcessingId] = useState(null)

  const refresh = () => {
    setLoading(true)
    return listVoiceNotes()
      .then((res) => setNotes(res.data))
      .finally(() => setLoading(false))
  }

  useEffect(() => { refresh() }, [])

  const selectedNote = notes.find((n) => n.id === selectedId)

  /**
   * Runs the ENTIRE pipeline automatically for one voice note:
   * transcribe -> extract -> auto-save if confidence is high enough.
   * If the result needs human review instead (confirm_review /
   * manual_review), it stops there and opens that note for editing
   * rather than guessing on the user's behalf.
   */
  const autoProcessNote = async (noteId, languageHint) => {
    setAutoProcessingId(noteId)
    try {
      await processVoiceNote(noteId, languageHint || undefined)
      const extractRes = await extractVoiceNote(noteId)
      const { extraction: result, recommended_action } = extractRes.data

      if (recommended_action === 'auto_create') {
        const payload = buildConfirmPayload(result)
        await confirmVoiceNote(noteId, payload)
      } else {
        // Needs a human look — open it for review instead of guessing.
        setSelectedId(noteId)
        setExtraction(result)
        setRecommendedAction(recommended_action)
      }
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || `Auto-processing failed for voice note #${noteId}.`)
    } finally {
      setAutoProcessingId(null)
      refresh()
    }
  }

  const handleUpload = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploading(true)
    setErrorMsg('')
    try {
      const res = await uploadVoiceNote(file)
      await refresh()
      await autoProcessNote(res.data.id, language)
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Upload failed.')
    } finally {
      setUploading(false)
      e.target.value = ''
    }
  }

  const selectNote = (note) => {
    setSelectedId(note.id)
    setExtraction(null)
    setRecommendedAction(null)
    setConfirmedRecord(null)
    setErrorMsg('')
  }

  const handleTranscribe = async () => {
    setBusyAction('transcribe')
    setErrorMsg('')
    try {
      await processVoiceNote(selectedId, language || undefined)
      refresh()
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Transcription failed.')
    } finally {
      setBusyAction('')
    }
  }

  const handleTranslate = async () => {
    setBusyAction('translate')
    setErrorMsg('')
    try {
      await translateVoiceNote(selectedId)
      refresh()
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Translation failed.')
    } finally {
      setBusyAction('')
    }
  }

  const handleExtract = async () => {
    setBusyAction('extract')
    setErrorMsg('')
    try {
      const res = await extractVoiceNote(selectedId)
      setExtraction(res.data.extraction)
      setRecommendedAction(res.data.recommended_action)
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Extraction failed.')
    } finally {
      setBusyAction('')
    }
  }

  const handleConfirm = async () => {
    setBusyAction('confirm')
    setErrorMsg('')
    try {
      const payload = buildConfirmPayload(extraction)
      const res = await confirmVoiceNote(selectedId, payload)
      setConfirmedRecord(res.data)
      refresh()
    } catch (err) {
      setErrorMsg(err.response?.data?.detail || 'Confirm failed.')
    } finally {
      setBusyAction('')
    }
  }

  return (
    <div className="p-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Voice Notes</h1>
          <p className="text-gray-500 text-sm mt-1">Upload a recording, then transcribe, extract, and confirm.</p>
        </div>
        <label className="cursor-pointer bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-2 rounded-lg">
          {uploading ? 'Uploading...' : 'Upload voice note'}
          <input
            type="file"
            accept=".mp3,.wav,.m4a,.webm"
            className="hidden"
            onChange={handleUpload}
            disabled={uploading}
          />
        </label>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* List */}
        <div className="col-span-1 bg-white rounded-xl border border-gray-200 divide-y divide-gray-100 max-h-[70vh] overflow-y-auto">
          {loading ? (
            <p className="p-4 text-sm text-gray-500">Loading...</p>
          ) : notes.length === 0 ? (
            <p className="p-4 text-sm text-gray-500">No voice notes yet — upload one to get started.</p>
          ) : (
            notes.map((note) => (
              <button
                key={note.id}
                onClick={() => selectNote(note)}
                className={`w-full text-left px-4 py-3 text-sm hover:bg-gray-50 ${
                  selectedId === note.id ? 'bg-indigo-50' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-gray-800">#{note.id}</span>
                  {autoProcessingId === note.id ? (
                    <span className="text-xs text-indigo-500 animate-pulse">Processing...</span>
                  ) : (
                    <StatusBadge status={note.processing_status} />
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-1">
                  {new Date(note.created_at).toLocaleString()}
                </p>
              </button>
            ))
          )}
        </div>

        {/* Detail */}
        <div className="col-span-2 bg-white rounded-xl border border-gray-200 p-6">
          {!selectedNote ? (
            <p className="text-sm text-gray-500">Select a voice note on the left to work with it.</p>
          ) : (
            <div className="space-y-5">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-gray-800">Voice note #{selectedNote.id}</h2>
                <StatusBadge status={selectedNote.processing_status} />
              </div>

              {errorMsg && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg p-3">
                  {errorMsg}
                </div>
              )}

              {/* Step 1: Transcribe */}
              {selectedNote.processing_status === 'uploaded' && (
                <div className="space-y-3">
                  <p className="text-sm text-gray-600">This voice note hasn't been transcribed yet.</p>
                  <div className="flex items-center gap-3">
                    <select
                      className="rounded-lg border border-gray-300 px-3 py-1.5 text-sm"
                      value={language}
                      onChange={(e) => setLanguage(e.target.value)}
                    >
                      {LANGUAGE_OPTIONS.map((opt) => (
                        <option key={opt.value} value={opt.value}>{opt.label}</option>
                      ))}
                    </select>
                    <button
                      onClick={() => autoProcessNote(selectedNote.id, language)}
                      disabled={autoProcessingId === selectedNote.id}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-1.5 rounded-lg disabled:opacity-50"
                    >
                      {autoProcessingId === selectedNote.id ? 'Processing...' : 'Auto-process (transcribe + extract + save)'}
                    </button>
                    <button
                      onClick={handleTranscribe}
                      disabled={busyAction === 'transcribe'}
                      className="text-sm font-medium text-gray-600 border border-gray-300 hover:bg-gray-50 px-3 py-1.5 rounded-lg disabled:opacity-50"
                    >
                      {busyAction === 'transcribe' ? '...' : 'Just transcribe'}
                    </button>
                  </div>
                </div>
              )}

              {/* Step 2: Show transcript + Extract */}
              {selectedNote.transcript && !extraction && (
                <div className="space-y-3">
                  <div>
                    <p className="text-xs font-medium text-gray-500 mb-1">Transcript</p>
                    <p className="text-sm text-gray-800 bg-gray-50 rounded-lg p-3" dir="auto">
                      {selectedNote.transcript.cleaned_transcript || selectedNote.transcript.raw_transcript}
                    </p>
                    <p className="text-xs text-gray-400 mt-1">
                      Language: {selectedNote.transcript.language || 'Unknown'}
                    </p>
                  </div>

                  {selectedNote.transcript.translation_english || selectedNote.transcript.translation_urdu ? (
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <p className="text-xs font-medium text-gray-500 mb-1">English</p>
                        <p className="text-sm text-gray-800 bg-blue-50 rounded-lg p-3">
                          {selectedNote.transcript.translation_english}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs font-medium text-gray-500 mb-1">Urdu</p>
                        <p className="text-sm text-gray-800 bg-blue-50 rounded-lg p-3" dir="rtl">
                          {selectedNote.transcript.translation_urdu}
                        </p>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={handleTranslate}
                      disabled={busyAction === 'translate'}
                      className="text-sm font-medium text-indigo-700 border border-indigo-300 hover:bg-indigo-50 px-4 py-1.5 rounded-lg disabled:opacity-50"
                    >
                      {busyAction === 'translate' ? 'Translating...' : 'Show in Urdu & English'}
                    </button>
                  )}

                  {selectedNote.processing_status === 'completed' && (
                    <div className="bg-green-50 border border-green-200 text-green-800 text-sm rounded-lg p-3">
                      This voice note was automatically transcribed, extracted, and saved — no action
                      needed. Check the Tasks, Orders, or Payments page for the resulting record.
                    </div>
                  )}

                  {selectedNote.processing_status !== 'completed' && (
                    <button
                      onClick={handleExtract}
                      disabled={busyAction === 'extract'}
                      className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium px-4 py-1.5 rounded-lg disabled:opacity-50"
                    >
                      {busyAction === 'extract' ? 'Extracting...' : 'Extract information'}
                    </button>
                  )}
                </div>
              )}

              {/* Step 3: Review/edit extraction + Confirm */}
              {extraction && !confirmedRecord && (
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium text-gray-500">Recommendation:</span>
                    <StatusBadge status={recommendedAction} />
                  </div>
                  <ExtractionForm extraction={extraction} onChange={setExtraction} />
                  <div className="flex gap-3">
                    <button
                      onClick={handleConfirm}
                      disabled={busyAction === 'confirm'}
                      className="bg-green-600 hover:bg-green-700 text-white text-sm font-medium px-4 py-1.5 rounded-lg disabled:opacity-50"
                    >
                      {busyAction === 'confirm' ? 'Saving...' : 'Confirm & Save'}
                    </button>
                    <button
                      onClick={() => setExtraction(null)}
                      className="text-gray-600 hover:text-gray-800 text-sm font-medium px-4 py-1.5 rounded-lg border border-gray-300"
                    >
                      Discard
                    </button>
                  </div>
                </div>
              )}

              {/* Step 4: Confirmed */}
              {confirmedRecord && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-sm text-green-800">
                  <p className="font-medium mb-1">Saved successfully.</p>
                  <pre className="text-xs whitespace-pre-wrap break-words">
                    {JSON.stringify(confirmedRecord, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default VoiceNotes
