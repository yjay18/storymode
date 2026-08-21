import React, { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { defaultApiClient } from "../../api/client";
import { BuilderNav } from "./BuilderNav";

export function BookImportDropzone(): React.JSX.Element {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [genre, setGenre] = useState<string>("fantasy");
  const [tone, setTone] = useState<string>("grounded, atmospheric");
  const [loading, setLoading] = useState<boolean>(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0 && e.dataTransfer.files[0]) {
      processFileSelection(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0 && e.target.files[0]) {
      processFileSelection(e.target.files[0]);
    }
  };

  const processFileSelection = (file: File) => {
    setError(null);
    const validExtensions = [".epub", ".txt", ".md", ".markdown"];
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    if (!validExtensions.includes(ext)) {
      setError(`Unsupported file format: '${file.name}'. Please drop an .epub, .txt, or .md file.`);
      return;
    }
    setSelectedFile(file);
  };

  const handleImportSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setError("Please select or drop an EPUB or book file first.");
      return;
    }

    setLoading(true);
    setError(null);
    setStatusMessage("Reading and parsing book archive...");

    try {
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          const result = (reader.result as string) || "";
          const base64Content = result.includes(",") ? result.split(",")[1] || "" : result;
          setStatusMessage("Running two-pass World Compactor (culture, taboos, factions, NPCs)...");

          const draft = await defaultApiClient.importBook({
            filename: selectedFile.name,
            content_base64: base64Content,
            genre: genre.trim() || "fantasy",
            tone: tone.trim() || "grounded, atmospheric",
          });

          setStatusMessage("Draft created! Redirecting to workspace...");
          navigate(`/builder/drafts/${draft.draft_id}`);
        } catch (err) {
          setError(err instanceof Error ? err.message : "Failed to import and compact book.");
          setLoading(false);
          setStatusMessage(null);
        }
      };

      reader.onerror = () => {
        setError("Failed to read local file.");
        setLoading(false);
        setStatusMessage(null);
      };

      reader.readAsDataURL(selectedFile);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
      setLoading(false);
      setStatusMessage(null);
    }
  };

  return (
    <form
      onSubmit={handleImportSubmit}
      aria-label="Import EPUB or Novel"
      style={{
        backgroundColor: "var(--color-bg-surface)",
        padding: "var(--space-6)",
        borderRadius: "var(--radius-lg)",
        border: "1px solid var(--color-border-subtle)",
        maxWidth: "680px",
        margin: "0 auto",
      }}
    >
      <BuilderNav />
      <h2 style={{ marginBottom: "0.5rem" }}>Drop in an EPUB or Book</h2>
      <p style={{ color: "var(--color-text-secondary)", marginBottom: "1.5rem" }}>
        Import any digital book or novel. The engine will parse chapters, extract regional culture,
        taboos, factions, and landmarks, and synthesize a compact World Codex ready for campaign generation.
      </p>

      {error && (
        <div
          role="alert"
          style={{
            padding: "var(--space-3)",
            backgroundColor: "rgba(239, 68, 68, 0.15)",
            border: "1px solid var(--color-danger)",
            borderRadius: "var(--radius-md)",
            color: "var(--color-danger)",
            marginBottom: "1rem",
          }}
        >
          {error}
        </div>
      )}

      {/* Drag & Drop Box */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        role="button"
        tabIndex={0}
        aria-label="File upload dropzone"
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            fileInputRef.current?.click();
          }
        }}
        style={{
          border: isDragging
            ? "2px dashed var(--color-primary)"
            : "2px dashed var(--color-border-subtle)",
          backgroundColor: isDragging
            ? "rgba(59, 130, 246, 0.08)"
            : "var(--color-bg-elevated)",
          borderRadius: "var(--radius-lg)",
          padding: "2.5rem 1.5rem",
          textAlign: "center",
          cursor: "pointer",
          marginBottom: "1.5rem",
          transition: "border-color 0.2s, background-color 0.2s",
        }}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".epub,.txt,.md,.markdown"
          onChange={handleFileChange}
          style={{ display: "none" }}
          aria-label="Upload EPUB or Book file"
        />
        <div style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>📖</div>
        {selectedFile ? (
          <div>
            <strong style={{ color: "var(--color-text-primary)", fontSize: "var(--font-size-md)" }}>
              {selectedFile.name}
            </strong>
            <p style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-sm)", marginTop: "0.25rem" }}>
              {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Click or drop another to replace
            </p>
          </div>
        ) : (
          <div>
            <strong style={{ color: "var(--color-text-primary)" }}>
              Drag & Drop your .epub, .txt, or .md file here
            </strong>
            <p style={{ color: "var(--color-text-muted)", fontSize: "var(--font-size-sm)", marginTop: "0.25rem" }}>
              or click to browse local files (max 100 MB)
            </p>
          </div>
        )}
      </div>

      {/* Genre & Tone Customization */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1rem", marginBottom: "1.5rem" }}>
        <div>
          <label htmlFor="import-genre" style={{ display: "block", marginBottom: "0.25rem", fontSize: "var(--font-size-sm)" }}>
            Campaign Genre
          </label>
          <input
            id="import-genre"
            type="text"
            value={genre}
            onChange={(e) => setGenre(e.target.value)}
            disabled={loading}
            placeholder="e.g. dark fantasy, sci-fi, gothic horror"
            style={{ width: "100%", padding: "var(--space-2)", borderRadius: "var(--radius-md)" }}
          />
        </div>
        <div>
          <label htmlFor="import-tone" style={{ display: "block", marginBottom: "0.25rem", fontSize: "var(--font-size-sm)" }}>
            Atmospheric Tone
          </label>
          <input
            id="import-tone"
            type="text"
            value={tone}
            onChange={(e) => setTone(e.target.value)}
            disabled={loading}
            placeholder="e.g. grounded, mysterious, gritty"
            style={{ width: "100%", padding: "var(--space-2)", borderRadius: "var(--radius-md)" }}
          />
        </div>
      </div>

      {statusMessage && (
        <div style={{ padding: "0.75rem", backgroundColor: "rgba(59, 130, 246, 0.1)", borderRadius: "var(--radius-md)", color: "var(--color-primary)", marginBottom: "1rem", fontSize: "var(--font-size-sm)" }}>
          ⏳ {statusMessage}
        </div>
      )}

      <button
        type="submit"
        disabled={!selectedFile || loading}
        style={{
          width: "100%",
          padding: "var(--space-3)",
          fontWeight: 600,
          cursor: selectedFile && !loading ? "pointer" : "not-allowed",
          opacity: selectedFile && !loading ? 1 : 0.6,
        }}
      >
        {loading ? "Compacting & Creating Draft..." : "Import & Synthesize World Codex"}
      </button>
    </form>
  );
}
