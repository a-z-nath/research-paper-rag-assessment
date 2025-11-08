import API_BASE_URL from "@/lib/api";

export default function Home() {
  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-4xl font-bold mb-6">Research Paper RAG System</h1>

      <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
        <h2 className="text-2xl font-semibold mb-3">🚀 System Status</h2>
        <p className="text-gray-700">
          Backend API running at:{" "}
          <code className="bg-gray-200 px-2 py-1 rounded">{API_BASE_URL}</code>
        </p>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <div className="border border-gray-300 rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-3">📄 Upload Papers</h3>
          <p className="text-gray-600 mb-4">
            Upload PDF research papers to the system for indexing and querying.
          </p>
          <a
            href="/upload"
            className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Go to Upload
          </a>
        </div>

        <div className="border border-gray-300 rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-3">🔍 Query Papers</h3>
          <p className="text-gray-600 mb-4">
            Ask questions and get AI-powered answers with citations from your
            papers.
          </p>
          <a
            href="/query"
            className="inline-block bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
          >
            Start Querying
          </a>
        </div>

        <div className="border border-gray-300 rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-3">📚 View Papers</h3>
          <p className="text-gray-600 mb-4">
            Browse all uploaded papers and see their metadata and statistics.
          </p>
          <a
            href="/papers"
            className="inline-block bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
          >
            View All Papers
          </a>
        </div>

        <div className="border border-gray-300 rounded-lg p-6">
          <h3 className="text-xl font-semibold mb-3">📊 Query History</h3>
          <p className="text-gray-600 mb-4">
            Review past queries and their answers with confidence scores.
          </p>
          <a
            href="/history"
            className="inline-block bg-orange-600 text-white px-4 py-2 rounded hover:bg-orange-700"
          >
            View History
          </a>
        </div>
      </div>

      <div className="mt-8 bg-gray-50 border border-gray-200 rounded-lg p-6">
        <h3 className="text-lg font-semibold mb-2">Features</h3>
        <ul className="list-disc list-inside text-gray-700 space-y-1">
          <li>PDF upload with automatic text extraction and chunking</li>
          <li>Semantic search using Qdrant vector database</li>
          <li>AI-powered answer generation with Google Gemini</li>
          <li>Citation tracking with page numbers and sections</li>
          <li>Query history and analytics</li>
        </ul>
      </div>
    </div>
  );
}
