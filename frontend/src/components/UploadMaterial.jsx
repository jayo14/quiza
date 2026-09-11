import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, X, Sparkles, CheckCircle, Loader2, RotateCcw, Hash, FileText } from "lucide-react";
import { toast } from "sonner";
import { uploadMaterial, generateQuizBackground, deleteMaterial, getQuiz } from "../services/apiClient";
import "./UploadMaterial.css";

function UploadMaterial() {
  const [fileList, setFileList] = useState([]);
  const [error, setError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [generatedQuizId, setGeneratedQuizId] = useState(null);
  const [numQuestions, setNumQuestions] = useState(10);
  const navigate = useNavigate();
  const pollersRef = useRef({});

  useEffect(() => {
    return () => {
      Object.values(pollersRef.current).forEach((timerId) => clearTimeout(timerId));
      pollersRef.current = {};
    };
  }, []);

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files);
    setError("");

    const rejectedFiles = [];
    const newItems = [];

    selectedFiles.forEach((file) => {
      const fileSizeMB = file.size / (1024 * 1024);
      if (fileSizeMB > 20) {
        rejectedFiles.push(`${file.name} is larger than 20 MB`);
      } else {
        const formatSize = (bytes) => {
          if (bytes < 1024) return `${bytes} B`;
          if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(2)} KB`;
          return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
        };
        const item = {
          id: `${file.name}-${Date.now()}-${Math.random()}`,
          rawFile: file,
          name: file.name,
          totalSizeMB: formatSize(file.size),
          currentLoadedMB: formatSize(0),
          progress: 0,
          status: "uploading",
          materialId: null,
          error: null,
          formatSize,
        };
        newItems.push(item);
      }
    });

    if (rejectedFiles.length > 0) {
      setError(rejectedFiles.join(". "));
    }

    setFileList((prev) => [...prev, ...newItems]);
    event.target.value = "";

    newItems.forEach((item) => {
      startSingleFileUpload(item);
    });
  };

  const startSingleFileUpload = async (item) => {
    setFileList((prev) =>
      prev.map((f) =>
        f.id === item.id ? { ...f, status: "uploading", progress: 0, error: null } : f
      )
    );

    try {
      const task = uploadMaterial(
        item.rawFile,
        item.name,
        (percent, loaded) => {
          setFileList((prev) =>
            prev.map((f) =>
              f.id === item.id
                ? { ...f, progress: percent, currentLoadedMB: f.formatSize ? f.formatSize(loaded) : `${(loaded / (1024 * 1024)).toFixed(2)} MB` }
                : f
            )
          );
        }
      );

      setFileList((prev) =>
        prev.map((f) => (f.id === item.id ? { ...f, cancelUpload: task.cancel } : f))
      );

      const material = await task.promise;

      setFileList((prev) =>
        prev.map((f) =>
          f.id === item.id
            ? {
                ...f,
                progress: 100,
                currentLoadedMB: f.totalSizeMB,
                status: "uploaded",
                materialId: material.id,
                cancelUpload: null,
              }
            : f
        )
      );
    } catch (err) {
      const isCancelled = err.message === "Upload cancelled";
      const errMsg = isCancelled ? "Upload cancelled" : (err.message || "Upload failed");

      if (!isCancelled) {
        console.error(`Upload error for ${item.name}:`, err);
      }

      setFileList((prev) =>
        prev.map((f) =>
          f.id === item.id
            ? { ...f, status: isCancelled ? "cancelled" : "error", error: errMsg, cancelUpload: null }
            : f
        )
      );
    }
  };

  const handleRetry = (item) => {
    setError("");
    startSingleFileUpload(item);
  };

  const removeFile = async (idToRemove) => {
    if (pollersRef.current[idToRemove]) {
      clearTimeout(pollersRef.current[idToRemove]);
      delete pollersRef.current[idToRemove];
    }

    const item = fileList.find((f) => f.id === idToRemove);
    if (item) {
      if (item.cancelUpload && item.status === "uploading") {
        item.cancelUpload();
      }
      if (item.materialId) {
        try {
          await deleteMaterial(item.materialId);
        } catch (err) {
          console.error("Failed to delete material:", err);
        }
      }
    }
    setFileList((prev) => prev.filter((item) => item.id !== idToRemove));
  };

  const isAnyUploading = fileList.some((item) => item.status === "uploading");
  const hasFailed = fileList.some((item) => item.status === "error" || item.status === "cancelled");
  const allUploaded =
    fileList.length > 0 && fileList.every((item) => item.status === "uploaded" || item.status === "error" || item.status === "cancelled");
  const hasUploadedFiles = fileList.some((item) => item.status === "uploaded");

  const handleGenerateQuiz = async () => {
    if (!hasUploadedFiles) return;

    setIsGenerating(true);
    setError("");

    try {
      const readyMaterialIds = fileList
        .filter((f) => f.status === "uploaded")
        .map((f) => f.materialId)
        .filter(Boolean);

      const quiz = await generateQuizBackground({
        material_id: readyMaterialIds[0],
        material_ids: readyMaterialIds,
        number_of_questions: numQuestions,
        difficulty: "medium",
        question_types: ["multiple_choice"],
      });

      setGeneratedQuizId(quiz.id);
      toast.info("Quiz generation started! Processing in background...");

      pollQuizStatus(quiz.id);
    } catch (err) {
      console.error("Quiz generation failed:", err);
      setError(err.message || "Failed to start quiz generation.");
      setIsGenerating(false);
    }
  };

  const pollQuizStatus = (quizId) => {
    const maxAttempts = 120; // 4 minutes max
    let attempts = 0;

    const check = async () => {
      attempts++;
      try {
        const quiz = await getQuiz(quizId);
        if (quiz.status === "ready") {
          toast.success("Quiz generated! Redirecting...");
          setTimeout(() => navigate(`/quiz?id=${quizId}`), 1000);
          return;
        }
        if (quiz.status === "failed") {
          toast.error(quiz.generation_error || "Quiz generation failed.");
          setIsGenerating(false);
          return;
        }
        if (attempts < maxAttempts) {
          pollersRef.current["quiz-poll"] = setTimeout(check, 2000);
        } else {
          toast.error("Quiz generation timed out.");
          setIsGenerating(false);
        }
      } catch {
        if (attempts < maxAttempts) {
          pollersRef.current["quiz-poll"] = setTimeout(check, 3000);
        }
      }
    };

    pollersRef.current["quiz-poll"] = setTimeout(check, 2000);
  };

  return (
    <section className="upload-material">
      <div className="upload-material__header">
        <h1>Upload Material</h1>
        <p>Upload your study material, then generate a quiz from it.</p>
      </div>

      {!isGenerating && !generatedQuizId && (
        <>
          <div className="upload-material__box">
            <div className="upload-material__icon">
              <Upload size={24} />
            </div>

            <h2>Upload your study material</h2>

            <p>Choose one or more files from your device.</p>

            <label className="upload-material__button">
              Choose Files
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                multiple
                onChange={handleFileChange}
              />
            </label>

            <span className="upload-material__formats">
              Supported formats: PDF, DOCX, TXT · Maximum 20 MB per file
            </span>
          </div>

          {error && <p className="upload-material__error">{error}</p>}

          {fileList.length > 0 && (
            <div className="upload-material__files">
              <h3>Uploaded Materials</h3>

              {fileList.map((item) => (
                <div className="upload-material__file-wrapper" key={item.id}>
                  <div className="upload-material__file">
                    <div>
                      <strong>{item.name}</strong>
                      <span
                        className={`upload-material__file-status ${
                          item.status === "error" || item.status === "cancelled"
                            ? "upload-material__file-status--error"
                            : item.status === "uploaded"
                            ? "upload-material__file-status--ready"
                            : ""
                        }`}
                      >
                        {item.status === "uploading" &&
                          `${item.currentLoadedMB} / ${item.totalSizeMB} (${item.progress}%)`}
                        {item.status === "uploaded" && `${item.totalSizeMB} · Uploaded`}
                        {item.status === "cancelled" && "Upload cancelled"}
                        {item.status === "error" && (item.error || "Upload failed")}
                      </span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      {item.status === "uploading" && (
                        <Loader2 size={16} className="upload-material__spin" style={{ color: "var(--primary)" }} />
                      )}
                      {item.status === "uploaded" && (
                        <CheckCircle size={18} style={{ color: "#10b981" }} />
                      )}
                      {(item.status === "error" || item.status === "cancelled") && (
                        <button
                          type="button"
                          className="upload-material__retry-btn"
                          onClick={() => handleRetry(item)}
                          title="Retry upload"
                        >
                          <RotateCcw size={15} />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => removeFile(item.id)}
                        aria-label={`Remove ${item.name}`}
                        title="Remove file"
                      >
                        <X size={18} />
                      </button>
                    </div>
                  </div>

                  {item.status === "uploading" && (
                    <div className="upload-material__progress-bar-wrap">
                      <div
                        className="upload-material__progress-bar-fill"
                        style={{ width: `${item.progress}%` }}
                      ></div>
                    </div>
                  )}
                </div>
              ))}

              {hasUploadedFiles && (
                <div className="upload-material__settings">
                  <div className="upload-material__field">
                    <label htmlFor="num-questions">
                      <Hash size={14} />
                      Number of Questions
                    </label>
                    <select
                      id="num-questions"
                      value={numQuestions}
                      onChange={(e) => setNumQuestions(Number(e.target.value))}
                    >
                      {[5, 10, 15, 20, 25, 30, 40, 50].map((n) => (
                        <option key={n} value={n}>{n} questions</option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              <button
                type="button"
                className="upload-material__generate"
                onClick={handleGenerateQuiz}
                disabled={!hasUploadedFiles || isAnyUploading}
              >
                {isAnyUploading ? (
                  <Loader2 size={18} className="upload-material__spin" />
                ) : (
                  <Sparkles size={18} />
                )}
                {isAnyUploading
                  ? "Uploading..."
                  : hasFailed && !hasUploadedFiles
                  ? "Retry Failed Files to Continue"
                  : "Generate Quiz"}
              </button>
            </div>
          )}
        </>
      )}

      {isGenerating && (
        <div className="upload-material__generation">
          <div className="upload-material__ai-icon">
            <Sparkles size={30} />
          </div>

          <h2>Generating your quiz...</h2>

          <p>
            Your materials are being processed and questions are being generated.
            You can safely navigate away — we'll notify you when it's ready.
          </p>

          <div className="upload-material__loader">
            <span></span>
          </div>
        </div>
      )}
    </section>
  );
}

export default UploadMaterial;
