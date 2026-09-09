import { useState, useRef, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, X, Sparkles, CheckCircle, Loader2, RotateCcw, AlertCircle } from "lucide-react";
import { uploadMaterial, generateQuiz, deleteMaterial, getMaterial } from "../services/apiClient";
import "./UploadMaterial.css";

function UploadMaterial() {
  const [fileList, setFileList] = useState([]);
  const [error, setError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGenerated, setIsGenerated] = useState(false);
  const [generatedQuizId, setGeneratedQuizId] = useState(null);
  const navigate = useNavigate();

  // Track active pollers so they can be cancelled when files are removed or retried
  const pollersRef = useRef({});

  // Clean up all pollers on unmount
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
          status: "uploading", // "uploading" | "processing" | "ready" | "error" | "cancelled"
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

  const pollMaterialStatus = (itemId, materialId) => {
    if (pollersRef.current[itemId]) {
      clearTimeout(pollersRef.current[itemId]);
      delete pollersRef.current[itemId];
    }

    const maxAttempts = 60; // Up to 2 minutes of polling
    let attempts = 0;

    const checkStatus = async () => {
      attempts++;
      try {
        const mat = await getMaterial(materialId);
        if (mat.status === "ready") {
          delete pollersRef.current[itemId];
          setFileList((prev) =>
            prev.map((f) =>
              f.id === itemId
                ? {
                    ...f,
                    status: "ready",
                    error: null,
                  }
                : f
            )
          );
        } else if (mat.status === "failed") {
          delete pollersRef.current[itemId];
          setFileList((prev) =>
            prev.map((f) =>
              f.id === itemId
                ? {
                    ...f,
                    status: "error",
                    error: mat.processing_error || "Content processing failed",
                  }
                : f
            )
          );
        } else {
          // Still uploaded or processing
          if (attempts < maxAttempts) {
            pollersRef.current[itemId] = setTimeout(checkStatus, 2000);
          } else {
            delete pollersRef.current[itemId];
            setFileList((prev) =>
              prev.map((f) =>
                f.id === itemId
                  ? {
                      ...f,
                      status: "error",
                      error: "Processing timed out. Please retry.",
                    }
                  : f
              )
            );
          }
        }
      } catch (err) {
        if (attempts < maxAttempts) {
          pollersRef.current[itemId] = setTimeout(checkStatus, 2500);
        }
      }
    };

    pollersRef.current[itemId] = setTimeout(checkStatus, 1500);
  };

  const startSingleFileUpload = async (item) => {
    // Clear any previous poll timer
    if (pollersRef.current[item.id]) {
      clearTimeout(pollersRef.current[item.id]);
      delete pollersRef.current[item.id];
    }

    setFileList((prev) =>
      prev.map((f) =>
        f.id === item.id
          ? {
              ...f,
              status: "uploading",
              progress: 0,
              error: null,
            }
          : f
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
                ? {
                    ...f,
                    progress: percent,
                    currentLoadedMB: f.formatSize ? f.formatSize(loaded) : `${(loaded / (1024 * 1024)).toFixed(2)} MB`,
                  }
                : f
            )
          );
        }
      );

      setFileList((prev) =>
        prev.map((f) => (f.id === item.id ? { ...f, cancelUpload: task.cancel } : f))
      );

      const material = await task.promise;

      if (material.status === "ready") {
        setFileList((prev) =>
          prev.map((f) =>
            f.id === item.id
              ? {
                  ...f,
                  progress: 100,
                  currentLoadedMB: f.totalSizeMB,
                  status: "ready",
                  materialId: material.id,
                  cancelUpload: null,
                }
              : f
          )
        );
      } else {
        setFileList((prev) =>
          prev.map((f) =>
            f.id === item.id
              ? {
                  ...f,
                  progress: 100,
                  currentLoadedMB: f.totalSizeMB,
                  status: "processing",
                  materialId: material.id,
                  cancelUpload: null,
                }
              : f
          )
        );
        pollMaterialStatus(item.id, material.id);
      }
    } catch (err) {
      const isCancelled = err.message === "Upload cancelled";
      const errMsg = isCancelled ? "Upload cancelled" : (err.message || "Upload failed");

      if (!isCancelled) {
        console.error(`Upload error for ${item.name}:`, err);
        setError(`Failed to upload ${item.name}: ${errMsg}`);
      }

      setFileList((prev) =>
        prev.map((f) =>
          f.id === item.id
            ? {
                ...f,
                status: isCancelled ? "cancelled" : "error",
                error: errMsg,
                cancelUpload: null,
              }
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
  const isAnyProcessing = fileList.some((item) => item.status === "processing");
  const hasFailed = fileList.some((item) => item.status === "error" || item.status === "cancelled");
  const allReady =
    fileList.length > 0 && fileList.every((item) => item.status === "ready");

  const handleGenerateQuiz = async () => {
    if (!allReady) return;

    setIsGenerating(true);
    setIsGenerated(false);
    setError("");

    try {
      const readyMaterialIds = fileList
        .filter((f) => f.status === "ready")
        .map((f) => f.materialId)
        .filter(Boolean);

      const targetCount = readyMaterialIds.length > 1 ? 10 : 5;

      const quiz = await generateQuiz({
        material_id: readyMaterialIds[0],
        material_ids: readyMaterialIds,
        number_of_questions: targetCount,
        difficulty: "medium",
        question_types: ["multiple_choice"],
      });

      setGeneratedQuizId(quiz.id);
      setIsGenerated(true);
    } catch (err) {
      console.error("Quiz generation failed:", err);
      if (err.message && err.message.toLowerCase().includes("still processing")) {
        setError("Study material is still finalizing indexing. Please wait a moment and click Generate Quiz again.");
      } else {
        setError(err.message || "Failed to generate quiz. Please try again.");
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleStartQuiz = () => {
    if (generatedQuizId) {
      navigate(`/quiz?id=${generatedQuizId}`);
    } else {
      navigate("/quizzes");
    }
  };

  return (
    <section className="upload-material">
      <div className="upload-material__header">
        <h1>Upload Material</h1>
        <p>Upload your study material and let Quiza turn it into a quiz.</p>
      </div>

      {!isGenerating && !isGenerated && (
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
              <h3>Selected Materials</h3>

              {fileList.map((item) => (
                <div className="upload-material__file-wrapper" key={item.id}>
                  <div className="upload-material__file">
                    <div>
                      <strong>{item.name}</strong>
                      <span
                        className={`upload-material__file-status ${
                          item.status === "error" || item.status === "cancelled"
                            ? "upload-material__file-status--error"
                            : item.status === "processing"
                            ? "upload-material__file-status--processing"
                            : item.status === "ready"
                            ? "upload-material__file-status--ready"
                            : ""
                        }`}
                      >
                        {item.status === "uploading" &&
                          `${item.currentLoadedMB} / ${item.totalSizeMB} (${item.progress}%)`}
                        {item.status === "processing" &&
                          `${item.totalSizeMB} · Processing & indexing content...`}
                        {item.status === "ready" && `${item.totalSizeMB} · Ready`}
                        {item.status === "cancelled" && "Upload cancelled"}
                        {item.status === "error" && (item.error || "Upload failed")}
                      </span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      {item.status === "uploading" && (
                        <Loader2
                          size={16}
                          className="upload-material__spin"
                          style={{ color: "var(--primary)" }}
                        />
                      )}
                      {item.status === "processing" && (
                        <Loader2
                          size={16}
                          className="upload-material__spin"
                          style={{ color: "#f59e0b" }}
                          title="Extracting and indexing text..."
                        />
                      )}
                      {item.status === "ready" && (
                        <CheckCircle
                          size={18}
                          style={{ color: "#10b981" }}
                        />
                      )}
                      {(item.status === "error" || item.status === "cancelled") && (
                        <button
                          type="button"
                          className="upload-material__retry-btn"
                          onClick={() => handleRetry(item)}
                          title="Retry upload"
                          aria-label={`Retry upload for ${item.name}`}
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

              <button
                type="button"
                className="upload-material__generate"
                onClick={handleGenerateQuiz}
                disabled={!allReady || isAnyUploading || isAnyProcessing}
              >
                {isAnyUploading || isAnyProcessing ? (
                  <Loader2 size={18} className="upload-material__spin" />
                ) : (
                  <Sparkles size={18} />
                )}
                {isAnyUploading
                  ? "Uploading Material..."
                  : isAnyProcessing
                  ? "Processing Material..."
                  : hasFailed && !allReady
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
            Quiza is analyzing your study material and creating questions for
            you.
          </p>

          <div className="upload-material__loader">
            <span></span>
          </div>
        </div>
      )}

      {isGenerated && (
        <div className="upload-material__generation">
          <div className="upload-material__success-icon">
            <CheckCircle size={30} />
          </div>

          <h2>Quiz generated successfully!</h2>

          <p>Your study material has been turned into a quiz.</p>

          <button
            type="button"
            className="upload-material__generate"
            onClick={handleStartQuiz}
          >
            Start Quiz
          </button>
        </div>
      )}
    </section>
  );
}

export default UploadMaterial;
