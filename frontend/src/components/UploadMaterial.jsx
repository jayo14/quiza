import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, X, Sparkles, CheckCircle, Loader2, RotateCcw, Hash, AlertCircle } from "lucide-react";
import { toast } from "sonner";
import {
  uploadMaterial,
  generateQuizBackground,
  deleteMaterial,
  getMaterial,
  getQuiz,
  listMaterials,
  listQuizzes,
} from "../services/apiClient";
import "./UploadMaterial.css";

const POLL_INTERVAL = 2000;
const MAX_POLL_ATTEMPTS = 120; // 4 min

const fmtBytes = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
};

function materialToFormItem(material) {
  const statusMap = { ready: "uploaded", processing: "uploaded", uploaded: "uploaded", failed: "error" };
  return {
    id: `mat-${material.id}`,
    rawFile: null,
    name: material.filename,
    sizeLabel: fmtBytes(material.file_size),
    progress: 100,
    status: statusMap[material.status] || "uploaded",
    materialId: material.id,
    error: material.processing_error || null,
  };
}

function UploadMaterial() {
  const [fileList, setFileList] = useState([]);
  const [error, setError] = useState("");
  const [numQuestions, setNumQuestions] = useState(10);
  const navigate = useNavigate();
  const pollersRef = useRef({});

  // Generation state machine: idle → ingesting → generating → ready | failed
  const [genPhase, setGenPhase] = useState("idle");
  const [genQuizId, setGenQuizId] = useState(null);
  const [genError, setGenError] = useState(null);
  const [materialStates, setMaterialStates] = useState({});
  const [restoring, setRestoring] = useState(true);

  // ── Cleanup ─────────────────────────────────────────────────

  useEffect(() => {
    return () => {
      Object.values(pollersRef.current).forEach(clearTimeout);
      pollersRef.current = {};
    };
  }, []);

  // ── Polling helpers ─────────────────────────────────────────

  const cancelPoll = (key) => {
    if (pollersRef.current[key]) {
      clearTimeout(pollersRef.current[key]);
      delete pollersRef.current[key];
    }
  };

  const schedulePoll = (key, fn, delay = POLL_INTERVAL) => {
    pollersRef.current[key] = setTimeout(fn, delay);
  };

  // ── Material ingestion polling ──────────────────────────────

  const pollMaterialIngestion = useCallback((materialId) => {
    let attempts = 0;
    const check = async () => {
      attempts++;
      try {
        const mat = await getMaterial(materialId);
        setMaterialStates((prev) => ({ ...prev, [materialId]: mat.status }));

        if (mat.status === "ready") {
          // Update file list status
          setFileList((prev) =>
            prev.map((f) =>
              f.materialId === materialId ? { ...f, status: "uploaded", error: null } : f
            )
          );
          return;
        }
        if (mat.status === "failed") {
          setFileList((prev) =>
            prev.map((f) =>
              f.materialId === materialId
                ? { ...f, status: "error", error: mat.processing_error || "Ingestion failed" }
                : f
            )
          );
          toast.error(`${mat.filename} processing failed: ${mat.processing_error || "Unknown error"}`);
          return;
        }
        if (attempts < MAX_POLL_ATTEMPTS) {
          schedulePoll(`mat-${materialId}`, check);
        }
      } catch {
        if (attempts < MAX_POLL_ATTEMPTS) schedulePoll(`mat-${materialId}`, check, 3000);
      }
    };
    schedulePoll(`mat-${materialId}`, check);
  }, []);

  // ── Quiz status polling ─────────────────────────────────────

  const pollQuizStatus = useCallback(
    (quizId) => {
      let attempts = 0;
      const check = async () => {
        attempts++;
        try {
          const quiz = await getQuiz(quizId);
          if (quiz.status === "ready") {
            setGenPhase("ready");
            setGenQuizId(quizId);
            toast.success("Quiz ready! Redirecting...");
            setTimeout(() => navigate(`/quiz?id=${quizId}`), 1200);
            return;
          }
          if (quiz.status === "failed") {
            setGenPhase("failed");
            setGenQuizId(quizId);
            setGenError(quiz.generation_error || "Quiz generation failed.");
            toast.error(quiz.generation_error || "Quiz generation failed.");
            return;
          }
          if (attempts < MAX_POLL_ATTEMPTS) {
            schedulePoll("quiz", check);
          } else {
            setGenPhase("failed");
            setGenError("Quiz generation timed out.");
            toast.error("Quiz generation timed out.");
          }
        } catch {
          if (attempts < MAX_POLL_ATTEMPTS) schedulePoll("quiz", check, 3000);
        }
      };
      schedulePoll("quiz", check);
    },
    [navigate]
  );

  // ── Restore state from DB on mount ─────────────────────────

  useEffect(() => {
    let cancelled = false;

    const restore = async () => {
      try {
        const [materials, quizzes] = await Promise.all([listMaterials(), listQuizzes()]);
        if (cancelled) return;

        // Build file list from materials
        const items = materials.map(materialToFormItem);
        setFileList(items);

        // Build material status map
        const matMap = {};
        materials.forEach((m) => {
          matMap[m.id] = m.status;
        });
        setMaterialStates(matMap);

        // Find most recent in-progress or recent quiz
        const generatingQuizzes = quizzes.filter((q) => q.status === "generating");
        const readyQuizzes = quizzes.filter((q) => q.status === "ready");
        const failedQuizzes = quizzes.filter((q) => q.status === "failed");
        const processingMats = materials.filter(
          (m) => m.status === "processing" || m.status === "uploaded"
        );

        if (generatingQuizzes.length > 0) {
          // Most recent generating quiz
          const quiz = generatingQuizzes[0];
          setGenQuizId(quiz.id);
          setNumQuestions(quiz.number_of_questions);
          setGenPhase("generating");
          pollQuizStatus(quiz.id);

          // Also poll materials that are still processing
          materials
            .filter((m) => m.status === "processing")
            .forEach((m) => pollMaterialIngestion(m.id));
        } else if (processingMats.length > 0) {
          // Materials still ingesting, no quiz yet
          setGenPhase("ingesting");
          processingMats.forEach((m) => pollMaterialIngestion(m.id));
        } else if (failedQuizzes.length > 0) {
          const quiz = failedQuizzes[0];
          setGenQuizId(quiz.id);
          setNumQuestions(quiz.number_of_questions);
          setGenPhase("failed");
          setGenError(quiz.generation_error || "Previous quiz generation failed.");
        } else if (readyQuizzes.length > 0) {
          const quiz = readyQuizzes[0];
          setGenQuizId(quiz.id);
          setNumQuestions(quiz.number_of_questions);
        }
        // else: idle, show upload view
      } catch {
        // Silent — show empty upload view
      } finally {
        if (!cancelled) setRestoring(false);
      }
    };

    restore();
    return () => { cancelled = true; };
  }, [pollMaterialIngestion, pollQuizStatus]);

  // ── Upload logic ────────────────────────────────────────────

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files);
    setError("");

    const rejected = [];
    const newItems = [];

    selectedFiles.forEach((file) => {
      const sizeMB = file.size / (1024 * 1024);
      if (sizeMB > 20) {
        rejected.push(`${file.name} is larger than 20 MB`);
        return;
      }
      newItems.push({
        id: `${file.name}-${Date.now()}-${Math.random()}`,
        rawFile: file,
        name: file.name,
        sizeLabel: fmtBytes(file.size),
        progress: 0,
        status: "uploading",
        materialId: null,
        error: null,
      });
    });

    if (rejected.length) setError(rejected.join(". "));
    setFileList((prev) => [...prev, ...newItems]);
    event.target.value = "";
    newItems.forEach(startUpload);
  };

  const startUpload = async (item) => {
    setFileList((prev) =>
      prev.map((f) => (f.id === item.id ? { ...f, status: "uploading", progress: 0, error: null } : f))
    );
    try {
      const task = uploadMaterial(item.rawFile, item.name, (pct) => {
        setFileList((prev) =>
          prev.map((f) => (f.id === item.id ? { ...f, progress: pct } : f))
        );
      });
      setFileList((prev) =>
        prev.map((f) => (f.id === item.id ? { ...f, cancelUpload: task.cancel } : f))
      );
      const mat = await task.promise;
      setFileList((prev) =>
        prev.map((f) =>
          f.id === item.id
            ? { ...f, progress: 100, status: "uploaded", materialId: mat.id, cancelUpload: null }
            : f
        )
      );
    } catch (err) {
      const cancelled = err.message === "Upload cancelled";
      setFileList((prev) =>
        prev.map((f) =>
          f.id === item.id
            ? { ...f, status: cancelled ? "cancelled" : "error", error: err.message, cancelUpload: null }
            : f
        )
      );
    }
  };

  const handleRetry = (item) => {
    setError("");
    startUpload(item);
  };

  const removeFile = async (id) => {
    cancelPoll(id);
    const item = fileList.find((f) => f.id === id);
    if (item) {
      if (item.cancelUpload && item.status === "uploading") item.cancelUpload();
      if (item.materialId) deleteMaterial(item.materialId).catch(() => {});
    }
    setFileList((prev) => prev.filter((f) => f.id !== id));
  };

  // ── Wait for materials to finish ingesting ──────────────────

  const waitForMaterials = (materialIds) => {
    return new Promise((resolve, reject) => {
      let attempts = 0;
      const checkAll = async () => {
        attempts++;
        try {
          const statuses = await Promise.all(
            materialIds.map((id) =>
              getMaterial(id).then((m) => ({ id, status: m.status, error: m.processing_error }))
            )
          );

          const failed = statuses.filter((s) => s.status === "failed");
          if (failed.length) {
            reject(new Error(`Ingestion failed for: ${failed.map((s) => s.id).join(", ")}`));
            return;
          }

          const allReady = statuses.every((s) => s.status === "ready");
          if (allReady) {
            resolve();
            return;
          }

          if (attempts >= MAX_POLL_ATTEMPTS) {
            reject(new Error("Ingestion timed out waiting for materials to process."));
            return;
          }

          schedulePoll("wait-materials", checkAll);
        } catch {
          if (attempts < MAX_POLL_ATTEMPTS) schedulePoll("wait-materials", checkAll, 3000);
          else reject(new Error("Failed to check material status."));
        }
      };
      checkAll();
    });
  };

  // ── Generate quiz ───────────────────────────────────────────

  const handleGenerateQuiz = async () => {
    const uploaded = fileList.filter((f) => f.status === "uploaded" && f.materialId);
    if (!uploaded.length) return;

    setError("");
    setGenError(null);
    setGenPhase("ingesting");
    setMaterialStates({});

    const matMap = {};
    uploaded.forEach((f) => {
      matMap[f.materialId] = "processing";
    });
    setMaterialStates(matMap);

    // Poll each material for UI status
    uploaded.forEach((f) => pollMaterialIngestion(f.materialId));

    try {
      // Wait for all materials to finish ingesting BEFORE generating
      await waitForMaterials(uploaded.map((f) => f.materialId));

      const ids = uploaded.map((f) => f.materialId);
      const quiz = await generateQuizBackground({
        material_id: ids[0],
        material_ids: ids,
        number_of_questions: numQuestions,
        difficulty: "medium",
        question_types: ["multiple_choice"],
      });

      setGenQuizId(quiz.id);
      setGenPhase("generating");
      toast.info("Materials ready. Generating quiz...");

      pollQuizStatus(quiz.id);
    } catch (err) {
      setGenPhase("failed");
      setGenError(err.message || "Failed to start quiz generation.");
      toast.error(err.message || "Failed to start quiz generation.");
    }
  };

  const resetGeneration = () => {
    Object.keys(pollersRef.current).forEach(cancelPoll);
    setGenPhase("idle");
    setGenQuizId(null);
    setGenError(null);
    setMaterialStates({});
  };

  // ── Derived state ───────────────────────────────────────────

  const isAnyUploading = fileList.some((f) => f.status === "uploading");
  const hasUploaded = fileList.some((f) => f.status === "uploaded");
  const uploadErrors = fileList.filter((f) => f.status === "error");

  const ingestingMats = fileList.filter(
    (f) => f.materialId && materialStates[f.materialId] === "processing"
  );

  // ── Render ──────────────────────────────────────────────────

  if (restoring) {
    return (
      <section className="upload-material">
        <div className="upload-material__header">
          <h1>Upload Material</h1>
          <p>Loading...</p>
        </div>
        <div className="upload-material__processing">
          <div className="upload-material__phase">
            <div className="upload-material__phase-header">
              <Loader2 size={20} className="upload-material__spin" style={{ color: "var(--primary)" }} />
              <h2>Restoring state...</h2>
            </div>
          </div>
        </div>
      </section>
    );
  }

  const showUploadView = genPhase === "idle";
  const showProcessingView = genPhase === "ingesting" || genPhase === "generating";
  const showResultView = genPhase === "ready" || genPhase === "failed";

  return (
    <section className="upload-material">
      <div className="upload-material__header">
        <h1>Upload Material</h1>
        <p>Upload study materials, then generate a quiz from them.</p>
      </div>

      {/* ── Upload view ─────────────────────────────────────── */}
      {showUploadView && (
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
              <h3>Materials</h3>

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
                        {item.status === "uploading" && `${item.progress}%`}
                        {item.status === "uploaded" && `${item.sizeLabel} · Uploaded`}
                        {item.status === "cancelled" && "Cancelled"}
                        {item.status === "error" && (item.error || "Failed")}
                      </span>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                      {item.status === "uploading" && (
                        <Loader2
                          size={16}
                          className="upload-material__spin"
                          style={{ color: "var(--primary)" }}
                        />
                      )}
                      {item.status === "uploaded" && (
                        <CheckCircle size={18} style={{ color: "#10b981" }} />
                      )}
                      {(item.status === "error" || item.status === "cancelled") && (
                        <button
                          type="button"
                          className="upload-material__retry-btn"
                          onClick={() => handleRetry(item)}
                          title="Retry"
                        >
                          <RotateCcw size={15} />
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => removeFile(item.id)}
                        aria-label={`Remove ${item.name}`}
                        title="Remove"
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
                      />
                    </div>
                  )}
                </div>
              ))}

              {hasUploaded && (
                <div className="upload-material__settings">
                  <div className="upload-material__field">
                    <label htmlFor="num-questions">
                      <Hash size={14} /> Number of Questions
                    </label>
                    <select
                      id="num-questions"
                      value={numQuestions}
                      onChange={(e) => setNumQuestions(Number(e.target.value))}
                    >
                      {[5, 10, 15, 20, 25, 30, 40, 50].map((n) => (
                        <option key={n} value={n}>
                          {n} questions
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              )}

              <button
                type="button"
                className="upload-material__generate"
                onClick={handleGenerateQuiz}
                disabled={!hasUploaded || isAnyUploading}
              >
                {isAnyUploading ? (
                  <Loader2 size={18} className="upload-material__spin" />
                ) : (
                  <Sparkles size={18} />
                )}
                {isAnyUploading
                  ? "Uploading..."
                  : uploadErrors.length && !hasUploaded
                  ? "Retry Failed"
                  : "Generate Quiz"}
              </button>
            </div>
          )}
        </>
      )}

      {/* ── Processing view ─────────────────────────────────── */}
      {showProcessingView && (
        <div className="upload-material__processing">
          {/* Material ingestion progress */}
          {genPhase === "ingesting" && (
            <div className="upload-material__phase">
              <div className="upload-material__phase-header">
                <Loader2
                  size={20}
                  className="upload-material__spin"
                  style={{ color: "#f59e0b" }}
                />
                <h2>Processing materials...</h2>
              </div>
              <p className="upload-material__phase-sub">
                Extracting and indexing content from{" "}
                {ingestingMats.length || fileList.filter((f) => f.materialId).length} file(s).
              </p>
              <div className="upload-material__material-list">
                {fileList
                  .filter((f) => f.materialId)
                  .map((f) => {
                    const st = materialStates[f.materialId];
                    return (
                      <div key={f.id} className="upload-material__material-row">
                        <div className="upload-material__material-info">
                          {st === "processing" && (
                            <Loader2
                              size={14}
                              className="upload-material__spin"
                              style={{ color: "#f59e0b" }}
                            />
                          )}
                          {st === "ready" && (
                            <CheckCircle size={14} style={{ color: "#10b981" }} />
                          )}
                          {st === "failed" && (
                            <AlertCircle size={14} style={{ color: "#ef4444" }} />
                          )}
                          {!st && <div style={{ width: 14, height: 14 }} />}
                          <span>{f.name}</span>
                        </div>
                        <span
                          className={`upload-material__material-status upload-material__material-status--${
                            st || "pending"
                          }`}
                        >
                          {st === "processing" && "Processing..."}
                          {st === "ready" && "Ready"}
                          {st === "failed" && "Failed"}
                          {!st && "Queued"}
                        </span>
                      </div>
                    );
                  })}
              </div>
            </div>
          )}

          {/* Quiz generation progress */}
          {genPhase === "generating" && (
            <div className="upload-material__phase">
              <div className="upload-material__phase-header">
                <Sparkles
                  size={20}
                  className="upload-material__spin"
                  style={{ color: "var(--primary)" }}
                />
                <h2>Generating quiz...</h2>
              </div>
              <p className="upload-material__phase-sub">
                AI is creating {numQuestions} questions from your material.
              </p>
              <div className="upload-material__loader">
                <span />
              </div>
            </div>
          )}

          <p className="upload-material__safe-notice">
            You can safely navigate away. We'll notify you when it's ready.
          </p>
        </div>
      )}

      {/* ── Result view ─────────────────────────────────────── */}
      {showResultView && genPhase === "ready" && (
        <div className="upload-material__generation">
          <div className="upload-material__success-icon">
            <CheckCircle size={30} />
          </div>
          <h2>Quiz generated successfully!</h2>
          <p>Your study material has been turned into a quiz.</p>
          <button
            type="button"
            className="upload-material__generate"
            onClick={() => navigate(`/quiz?id=${genQuizId}`)}
          >
            Start Quiz
          </button>
        </div>
      )}

      {showResultView && genPhase === "failed" && (
        <div className="upload-material__generation">
          <div className="upload-material__error-icon">
            <AlertCircle size={30} />
          </div>
          <h2>Generation failed</h2>
          <p>{genError}</p>
          <button
            type="button"
            className="upload-material__generate"
            onClick={resetGeneration}
          >
            Try Again
          </button>
        </div>
      )}
    </section>
  );
}

export default UploadMaterial;
