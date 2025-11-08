"use client";

import { useState, useEffect } from "react";
import { API_ENDPOINTS } from "@/lib/api";

interface Paper {
  id: number;
  title: string;
  authors: string;
  year: number | null;
  filename: string;
  total_pages: number;
  chunk_count: number;
  upload_date: string;
}

export default function PapersPage() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [deleting, setDeleting] = useState<number | null>(null);

  const fetchPapers = async () => {
    console.log("📚 [Papers] Fetching papers list...");
    try {
      const response = await fetch(API_ENDPOINTS.listPapers);
      if (response.ok) {
        const data = await response.json();
        console.log(`✅ [Papers] Loaded ${data.length} papers`);
        setPapers(data);
      } else {
        console.error("❌ [Papers] Failed to fetch papers");
        setError("Failed to fetch papers");
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      console.error("❌ [Papers] Network error:", errorMsg);
      setError("Network error - is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (paperId: number) => {
    if (!confirm("Are you sure you want to delete this paper?")) return;

    console.log("🗑️  [Papers] Deleting paper:", paperId);
    setDeleting(paperId);
    try {
      const response = await fetch(API_ENDPOINTS.deletePaper(paperId), {
        method: "DELETE",
      });

      if (response.ok) {
        console.log("✅ [Papers] Paper deleted successfully");
        setPapers(papers.filter((p) => p.id !== paperId));
      } else {
        console.error("❌ [Papers] Failed to delete paper");
        alert("Failed to delete paper");
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      console.error("❌ [Papers] Network error:", errorMsg);
      alert("Network error");
    } finally {
      setDeleting(null);
    }
  };

  useEffect(() => {
    fetchPapers();
  }, []);

  if (loading) {
    return <div className="text-center py-8">Loading papers...</div>;
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg">
        <strong>Error:</strong> {error}
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold">All Papers</h1>
        <button
          onClick={fetchPapers}
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
        >
          Refresh
        </button>
      </div>

      {papers.length === 0 ? (
        <div className="bg-gray-50 border border-gray-200 rounded-lg p-8 text-center">
          <p className="text-gray-600 mb-4">No papers uploaded yet.</p>
          <a
            href="/upload"
            className="inline-block bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Upload Your First Paper
          </a>
        </div>
      ) : (
        <div className="grid gap-4">
          {papers.map((paper) => (
            <div
              key={paper.id}
              className="bg-white border border-gray-300 rounded-lg p-6 hover:shadow-md transition"
            >
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <h2 className="text-xl font-semibold text-gray-900 mb-2">
                    {paper.title}
                  </h2>

                  <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm text-gray-600 mb-3">
                    <div>
                      <strong>Authors:</strong> {paper.authors || "Unknown"}
                    </div>
                    <div>
                      <strong>Year:</strong> {paper.year || "N/A"}
                    </div>
                    <div>
                      <strong>Filename:</strong> {paper.filename}
                    </div>
                    <div>
                      <strong>Pages:</strong> {paper.total_pages}
                    </div>
                    <div>
                      <strong>Chunks:</strong> {paper.chunk_count}
                    </div>
                    <div>
                      <strong>Uploaded:</strong>{" "}
                      {new Date(paper.upload_date).toLocaleDateString()}
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => handleDelete(paper.id)}
                  disabled={deleting === paper.id}
                  className="ml-4 bg-red-600 text-white px-3 py-1 rounded text-sm hover:bg-red-700 disabled:bg-gray-400"
                >
                  {deleting === paper.id ? "Deleting..." : "Delete"}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-6 text-sm text-gray-600">
        Total: {papers.length} paper{papers.length !== 1 ? "s" : ""}
      </div>
    </div>
  );
}
