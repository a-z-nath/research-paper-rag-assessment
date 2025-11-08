"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { API_ENDPOINTS } from "@/lib/api";
import jsPDF from "jspdf";

interface Citation {
  paper_title: string;
  section: string | null;
  page: number;
  relevance_score: number;
  chunk_text?: string;
}

interface QueryResponse {
  answer: string;
  citations: Citation[];
  sources_used: string[];
  confidence: number;
  response_time: number;
  cached?: boolean;
}

export default function QueryPage() {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<QueryResponse | null>(null);
  const [error, setError] = useState("");

  const handleQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    console.log("🔍 [Query] Submitting query:", question.trim());
    console.log("   Parameters: top_k=" + topK);

    setLoading(true);
    setError("");
    setResult(null);

    const startTime = performance.now();

    try {
      console.log("   → Sending POST request to", API_ENDPOINTS.query);
      const response = await fetch(API_ENDPOINTS.query, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question: question.trim(),
          top_k: topK,
        }),
      });

      const data = await response.json();
      const responseTime = ((performance.now() - startTime) / 1000).toFixed(2);

      if (response.ok) {
        console.log(`✅ [Query] Response received in ${responseTime}s`);
        console.log(`   Cached: ${data.cached || false}`);
        console.log(`   Confidence: ${(data.confidence * 100).toFixed(1)}%`);
        console.log(`   Sources: ${data.sources_used?.length || 0} papers`);
        setResult(data);
      } else {
        console.error("❌ [Query] Error:", data.detail || "Query failed");
        setError(data.detail || "Query failed");
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      console.error("❌ [Query] Network error:", errorMsg);
      setError("Network error - is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const exportToPDF = () => {
    if (!result) return;

    console.log("📄 [Export] Generating PDF...");

    try {
      const pdf = new jsPDF();
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const margin = 20;
      const maxWidth = pageWidth - 2 * margin;
      let yPosition = margin;

      // Helper function to add text with word wrapping
      const addText = (text: string, fontSize: number = 10, isBold: boolean = false) => {
        pdf.setFontSize(fontSize);
        pdf.setFont("helvetica", isBold ? "bold" : "normal");
        const lines = pdf.splitTextToSize(text, maxWidth);
        
        // Check if we need a new page
        if (yPosition + (lines.length * fontSize * 0.5) > pageHeight - margin) {
          pdf.addPage();
          yPosition = margin;
        }
        
        pdf.text(lines, margin, yPosition);
        yPosition += lines.length * fontSize * 0.5 + 5;
      };

      // Title
      pdf.setFontSize(18);
      pdf.setFont("helvetica", "bold");
      pdf.text("Research Paper Query Results", pageWidth / 2, yPosition, { align: "center" });
      yPosition += 15;

      // Add horizontal line
      pdf.setDrawColor(0, 0, 0);
      pdf.line(margin, yPosition, pageWidth - margin, yPosition);
      yPosition += 10;

      // Question
      addText("Question:", 12, true);
      addText(question, 10, false);
      yPosition += 5;

      // Metadata
      pdf.setFontSize(10);
      pdf.setFont("helvetica", "normal");
      pdf.text(`Confidence: ${(result.confidence * 100).toFixed(1)}%`, margin, yPosition);
      pdf.text(`Response Time: ${result.cached ? "< 0.01s (Cached)" : `${result.response_time.toFixed(2)}s`}`, pageWidth / 2, yPosition);
      yPosition += 10;

      // Line separator
      pdf.line(margin, yPosition, pageWidth - margin, yPosition);
      yPosition += 10;

      // Answer
      addText("Answer:", 14, true);
      // Remove markdown formatting for PDF
      const plainAnswer = result.answer
        .replace(/\*\*(.*?)\*\*/g, "$1") // Remove bold
        .replace(/\*(.*?)\*/g, "$1") // Remove italic
        .replace(/#{1,6}\s/g, "") // Remove headers
        .replace(/`(.*?)`/g, "$1"); // Remove code blocks
      addText(plainAnswer, 10, false);
      yPosition += 5;

      // Sources
      if (result.sources_used.length > 0) {
        addText(`Sources (${result.sources_used.length}):`, 12, true);
        result.sources_used.forEach((source, idx) => {
          addText(`${idx + 1}. ${source}`, 10, false);
        });
        yPosition += 5;
      }

      // Citations
      if (result.citations.length > 0) {
        // Check if we need a new page for citations
        if (yPosition > pageHeight - 100) {
          pdf.addPage();
          yPosition = margin;
        }

        addText(`Citations (${result.citations.length}):`, 12, true);
        
        result.citations.forEach((citation, idx) => {
          // Check if we need a new page
          if (yPosition > pageHeight - 60) {
            pdf.addPage();
            yPosition = margin;
          }

          addText(`[${idx + 1}] ${citation.paper_title}`, 10, true);
          pdf.setFontSize(9);
          pdf.setFont("helvetica", "normal");
          
          const citationInfo = `Section: ${citation.section || "N/A"} | Page: ${citation.page} | Relevance: ${(citation.relevance_score * 100).toFixed(0)}%`;
          pdf.text(citationInfo, margin + 5, yPosition);
          yPosition += 5;
          
          if (citation.chunk_text) {
            const chunkLines = pdf.splitTextToSize(`"${citation.chunk_text}"`, maxWidth - 10);
            pdf.setFont("helvetica", "italic");
            pdf.text(chunkLines, margin + 5, yPosition);
            yPosition += chunkLines.length * 4.5 + 5;
          }
          
          yPosition += 3;
        });
      }

      // Footer
      const timestamp = new Date().toLocaleString();
      pdf.setFontSize(8);
      pdf.setFont("helvetica", "normal");
      pdf.setTextColor(128, 128, 128);
      pdf.text(`Generated on ${timestamp}`, pageWidth / 2, pageHeight - 10, { align: "center" });

      // Save the PDF
      const fileName = `query-results-${Date.now()}.pdf`;
      pdf.save(fileName);
      
      console.log(`✅ [Export] PDF saved as ${fileName}`);
    } catch (error) {
      console.error("❌ [Export] Error generating PDF:", error);
      alert("Failed to generate PDF. Please try again.");
    }
  };

  return (
    <div className="max-w-6xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Query Papers</h1>

      <form
        onSubmit={handleQuery}
        className="bg-white border border-gray-300 rounded-lg p-6 mb-6"
      >
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Your Question
          </label>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="E.g., What methodology was used in the transformer paper?"
            rows={3}
            className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            disabled={loading}
          />
        </div>

        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Top K Results: {topK}
          </label>
          <input
            type="range"
            min="1"
            max="20"
            value={topK}
            onChange={(e) => setTopK(parseInt(e.target.value))}
            className="w-full"
            disabled={loading}
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>1</span>
            <span>20</span>
          </div>
        </div>

        <button
          type="submit"
          disabled={!question.trim() || loading}
          className="w-full bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {loading ? "Searching..." : "Ask Question"}
        </button>
      </form>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-4">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="space-y-6">
          {/* Export Button */}
          <div className="flex justify-end">
            <button
              onClick={exportToPDF}
              className="bg-red-600 text-white px-6 py-2 rounded-lg hover:bg-red-700 flex items-center gap-2 shadow-md transition-all"
            >
              <svg
                xmlns="http://www.w3.org/2000/svg"
                className="h-5 w-5"
                viewBox="0 0 20 20"
                fill="currentColor"
              >
                <path
                  fillRule="evenodd"
                  d="M6 2a2 2 0 00-2 2v12a2 2 0 002 2h8a2 2 0 002-2V7.414A2 2 0 0015.414 6L12 2.586A2 2 0 0010.586 2H6zm5 6a1 1 0 10-2 0v3.586l-1.293-1.293a1 1 0 10-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 11.586V8z"
                  clipRule="evenodd"
                />
              </svg>
              📝 Export as PDF
            </button>
          </div>

          {/* Answer */}
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
            <div className="flex justify-between items-start mb-3">
              <h2 className="text-xl font-semibold text-blue-900">Answer</h2>
              {result.cached && (
                <span className="bg-green-100 text-green-800 text-xs font-semibold px-2.5 py-0.5 rounded flex items-center gap-1">
                  ⚡ Cached
                </span>
              )}
            </div>
            <div className="text-gray-800 leading-relaxed prose prose-blue max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {result.answer}
              </ReactMarkdown>
            </div>
            <div className="mt-4 flex gap-4 text-sm text-gray-600">
              <span>
                <strong>Confidence:</strong>{" "}
                {(result.confidence * 100).toFixed(1)}%
              </span>
              <span>
                <strong>Response Time:</strong>{" "}
                {result.cached
                  ? "< 0.01s"
                  : `${result.response_time.toFixed(2)}s`}
              </span>
            </div>
          </div>

          {/* Sources */}
          <div className="bg-purple-50 border border-purple-200 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-purple-900 mb-3">
              Sources ({result.sources_used.length})
            </h2>
            <ul className="list-disc list-inside space-y-1">
              {result.sources_used.map((source, idx) => (
                <li key={idx} className="text-gray-700">
                  {source}
                </li>
              ))}
            </ul>
          </div>

          {/* Citations */}
          <div className="bg-white border border-gray-300 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Citations ({result.citations.length})
            </h2>
            <div className="space-y-4">
              {result.citations.map((citation, idx) => (
                <div
                  key={idx}
                  className="border-l-4 border-green-500 pl-4 py-2 bg-gray-50"
                >
                  <div className="flex justify-between items-start mb-2">
                    <h3 className="font-semibold text-gray-900">
                      {citation.paper_title}
                    </h3>
                    <span className="text-sm bg-green-100 text-green-800 px-2 py-1 rounded">
                      {(citation.relevance_score * 100).toFixed(0)}% relevant
                    </span>
                  </div>
                  <div className="text-sm text-gray-600 mb-2">
                    <strong>Section:</strong> {citation.section || "N/A"} •{" "}
                    <strong>Page:</strong> {citation.page}
                  </div>
                  {citation.chunk_text && (
                    <p className="text-sm text-gray-700 italic">
                      "{citation.chunk_text}"
                    </p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      <div className="mt-6 bg-gray-50 border border-gray-200 rounded-lg p-4">
        <h3 className="font-semibold mb-2">💡 Example Questions</h3>
        <ul className="text-sm text-gray-700 space-y-1">
          <li>• What methodology was used in the transformer paper?</li>
          <li>
            • Which activation functions are commonly used in neural networks?
          </li>
          <li>• Compare the performance of CNNs and Transformers.</li>
          <li>• What datasets are used to evaluate computer vision models?</li>
        </ul>
      </div>
    </div>
  );
}
