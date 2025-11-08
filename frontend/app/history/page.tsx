'use client'

import { useState, useEffect } from 'react'
import { API_ENDPOINTS } from '@/lib/api'

interface QueryHistory {
  id: number
  question: string
  answer: string
  confidence: number
  response_time: number
  query_date: string
  sources_used: string[]
}

export default function HistoryPage() {
  const [history, setHistory] = useState<QueryHistory[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchHistory = async () => {
    console.log('📊 [History] Fetching query history...');
    setLoading(true)
    try {
      const response = await fetch(`${API_ENDPOINTS.queryHistory}?limit=50`)
      if (response.ok) {
        const data = await response.json()
        console.log(`✅ [History] Loaded ${data.length} queries`);
        setHistory(data)
      } else {
        console.error('❌ [History] Failed to fetch history');
        setError('Failed to fetch history')
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : 'Unknown error';
      console.error('❌ [History] Network error:', errorMsg);
      setError('Network error - is the backend running?')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchHistory()
  }, [])

  if (loading) {
    return <div className="text-center py-8">Loading query history...</div>
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg">
        <strong>Error:</strong> {error}
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">Query History</h1>
        <button
          onClick={fetchHistory}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {history.length === 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-600 mb-4">No queries yet.</p>
          <a
            href="/query"
            className="inline-block bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          >
            Ask Your First Question
          </a>
        </div>
      ) : (
        <div className="space-y-4">
          {history.map((item) => (
            <div
              key={item.id}
              className="bg-white border border-gray-300 rounded-lg p-6"
            >
              <div className="flex justify-between items-start mb-3">
                <h2 className="text-lg font-semibold text-gray-900 flex-1">
                  {item.question}
                </h2>
                <span className="text-xs text-gray-500 ml-4">
                  {new Date(item.query_date).toLocaleString()}
                </span>
              </div>

              <div className="bg-blue-50 border-l-4 border-blue-500 p-3 mb-3">
                <p className="text-sm text-gray-800">
                  {item.answer.length > 300
                    ? item.answer.substring(0, 300) + '...'
                    : item.answer}
                </p>
              </div>

              <div className="flex gap-4 text-sm text-gray-600">
                <span>
                  <strong>Confidence:</strong> {(item.confidence * 100).toFixed(1)}%
                </span>
                <span>
                  <strong>Time:</strong> {item.response_time.toFixed(2)}s
                </span>
                {item.sources_used && item.sources_used.length > 0 && (
                  <span>
                    <strong>Sources:</strong> {item.sources_used.length}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-6 text-sm text-gray-600">
        Total: {history.length} quer{history.length !== 1 ? 'ies' : 'y'}
      </div>
    </div>
  )
}
