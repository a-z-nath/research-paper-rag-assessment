"use client";

import { useState } from "react";
import { API_ENDPOINTS } from "@/lib/api";

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string>("");

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;

    console.log("📤 [Upload] Starting file upload:", file.name);
    console.log("   File size:", (file.size / (1024 * 1024)).toFixed(2), "MB");

    setUploading(true);
    setError("");
    setResult(null);

    const formData = new FormData();
    formData.append("file", file);

    const startTime = performance.now();

    try {
      console.log("   → Sending POST request to", API_ENDPOINTS.uploadPaper);
      const response = await fetch(API_ENDPOINTS.uploadPaper, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      const uploadTime = ((performance.now() - startTime) / 1000).toFixed(2);

      if (response.ok) {
        console.log(
          `✅ [Upload] Paper uploaded successfully in ${uploadTime}s`
        );
        console.log(`   Paper ID: ${data.paper_id}`);
        console.log(`   Title: ${data.title}`);
        console.log(`   Chunks: ${data.chunk_count}`);
        setResult(data);
        setFile(null);
        // Reset file input
        const fileInput = document.querySelector(
          'input[type="file"]'
        ) as HTMLInputElement;
        if (fileInput) fileInput.value = "";
      } else {
        console.error("❌ [Upload] Error:", data.detail || "Upload failed");
        setError(data.detail || "Upload failed");
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      console.error("❌ [Upload] Network error:", errorMsg);
      setError("Network error - is the backend running?");
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-3xl font-bold mb-6">Upload Research Papers</h1>

      <form
        onSubmit={handleUpload}
        className="bg-white border border-gray-300 rounded-lg p-6 mb-6"
      >
        <div className="mb-4">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select PDF File
          </label>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
            className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            disabled={uploading}
          />
        </div>

        <button
          type="submit"
          disabled={!file || uploading}
          className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
        >
          {uploading ? "Uploading..." : "Upload Paper"}
        </button>
      </form>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-4">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-6">
          <h2 className="text-xl font-semibold text-green-800 mb-3">
            ✅ Upload Successful
          </h2>
          <div className="space-y-2 text-sm">
            <p>
              <strong>Paper ID:</strong> {result.paper_id}
            </p>
            <p>
              <strong>Title:</strong> {result.title}
            </p>
            <p>
              <strong>Filename:</strong> {result.filename}
            </p>
            <p>
              <strong>Total Pages:</strong> {result.total_pages}
            </p>
            <p>
              <strong>Chunks Created:</strong> {result.chunk_count}
            </p>
            <p className="text-green-600">{result.message}</p>
          </div>
        </div>
      )}

      <div className="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
        <h3 className="font-semibold mb-2">ℹ️ Info</h3>
        <ul className="text-sm text-gray-700 space-y-1">
          <li>• Only PDF files are supported</li>
          <li>• The system will extract text and create semantic chunks</li>
          <li>• First upload may take longer as models are loaded</li>
          <li>• You can query the paper immediately after upload</li>
        </ul>
      </div>
    </div>
  );
}
