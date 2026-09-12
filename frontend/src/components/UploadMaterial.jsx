import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  Check,
  ChevronLeft,
  ChevronRight,
  FileCode,
  FileImage,
  FileSpreadsheet,
  FileText,
  Loader2,
  RotateCcw,
  Sparkles,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import { toast } from "sonner";
import {
  deleteMaterial,
  generateQuizBackground,
  getGenerationJob,
  listGenerationJobs,
  listMaterials,
  retryGenerationJob,
  startAttempt,
  uploadMaterial,
} from "../services/apiClient";
import "./UploadMaterial.css";

const POLL_INTERVAL = 2500;

const fmtBytes = (bytes) => {
  if (!bytes || isNaN(bytes)) return "0 B";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
};

function getFileTypeInfo(filename = "", fileType = "") {
  const ext = (filename.split(".").pop() || "").toLowerCase();
  const type = (fileType || "").toLowerCase();

  if (ext === "pdf" || type.includes("pdf")) {
    return {
      category: "pdf",
      label: "PDF",
      badgeClass: "file-type-logo--pdf",
      icon: "pdf",
    };
  }

  if (
    ["doc", "docx"].includes(ext) ||
    type.includes("word") ||
    type.includes("officedocument.wordprocessingml")
  ) {
    return {
      category: "doc",
      label: ext.toUpperCase() || "DOC",
      badgeClass: "file-type-logo--doc",
      icon: "doc",
    };
  }

  if (["txt", "text", "md", "rtf"].includes(ext) || type.includes("text/plain")) {
    return {
      category: "txt",
      label: ext.toUpperCase() || "TXT",
      badgeClass: "file-type-logo--txt",
      icon: "txt",
    };
  }

  if (
    ["png", "jpg", "jpeg", "webp", "svg", "gif"].includes(ext) ||
    type.startsWith("image/")
  ) {
    return {
      category: "image",
      label: ext.toUpperCase() || "IMG",
      badgeClass: "file-type-logo--image",
      icon: "image",
    };
  }

  if (
    ["ppt", "pptx"].includes(ext) ||
    type.includes("presentation") ||
    type.includes("powerpoint")
  ) {
    return {
      category: "ppt",
      label: ext.toUpperCase() || "PPT",
      badgeClass: "file-type-logo--ppt",
      icon: "ppt",
    };
  }

  if (
    ["xls", "xlsx", "csv"].includes(ext) ||
    type.includes("spreadsheet") ||
    type.includes("excel") ||
    type.includes("csv")
  ) {
    return {
      category: "sheet",
      label: ext.toUpperCase() || "XLS",
      badgeClass: "file-type-logo--sheet",
      icon: "sheet",
    };
  }

  return {
    category: "default",
    label: (ext || "FILE").toUpperCase().slice(0, 4),
    badgeClass: "file-type-logo--default",
    icon: "default",
  };
}

function FileTypeLogo({ filename, fileType }) {
  const info = getFileTypeInfo(filename, fileType);
  const IconComponent =
    info.icon === "image"
      ? FileImage
      : info.icon === "sheet"
      ? FileSpreadsheet
      : info.icon === "txt"
      ? FileCode
      : FileText;

  return (
    <div className={`file-type-logo ${info.badgeClass}`} title={`${info.label} file`}>
      <div className="file-type-logo__icon-box">
        <IconComponent size={18} className="file-type-logo__icon" />
      </div>
      <span className="file-type-logo__badge">{info.label}</span>
    </div>
  );
}

function materialToItem(material) {
  return {
    id: `mat-${material.id}`,
    rawFile: null,
    name: material.filename,
    fileType: material.file_type,
    sizeLabel: fmtBytes(material.file_size),
    progress: 100,
    status: "uploaded",
    materialId: material.id,
    error: null,
  };
}

function UploadMaterial() {
  const navigate = useNavigate();
  const poller = useRef(null);
  const [fileList, setFileList] = useState([]);
  const [selectedIds, setSelectedIds] = useState(new Set());
  const [difficulty, setDifficulty] = useState("medium");
  const [error, setError] = useState("");
  const [numQuestions, setNumQuestions] = useState(10);
  const [job, setJob] = useState(null);
  const [restoring, setRestoring] = useState(true);
  const [isDragging, setIsDragging] = useState(false);
  const [materialToDelete, setMaterialToDelete] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isRetryingJob, setIsRetryingJob] = useState(false);
  const [isStartingQuiz, setIsStartingQuiz] = useState(false);

  const pollJob = useCallback(async function pollGenerationJob(jobId) {
    try {
      const current = await getGenerationJob(jobId);
      setJob(current);
      if (current.status === "completed" && current.quiz_id) {
        toast.success("Quiz ready!");
        navigate(`/quiz?id=${current.quiz_id}`);
        return;
      }
      if (current.status === "failed") {
        toast.error(current.error_message || "Quiz generation failed.");
        return;
      }
      poller.current = setTimeout(() => pollGenerationJob(jobId), POLL_INTERVAL);
    } catch (err) {
      setError(err.message || "Unable to check quiz generation status.");
      poller.current = setTimeout(() => pollGenerationJob(jobId), POLL_INTERVAL * 2);
    }
  }, [navigate]);

  useEffect(() => {
    const restore = async () => {
      try {
        const [materials, jobs] = await Promise.all([listMaterials(), listGenerationJobs()]);
        const items = (materials || []).map(materialToItem);
        setFileList(items);
        setSelectedIds(new Set(items.filter((item) => item.materialId).map((item) => item.materialId)));
        const activeJob = (jobs || []).find((item) =>
          ["queued", "processing"].includes(item.status)
        ) || (jobs || [])[0];
        if (activeJob) {
          setJob(activeJob);
          setNumQuestions(activeJob.question_count);
          if (["queued", "processing"].includes(activeJob.status)) {
            pollJob(activeJob.id);
          }
        }
      } catch (err) {
        setError(err.message || "Unable to restore your materials.");
      } finally {
        setRestoring(false);
      }
    };
    restore();
    return () => {
      if (poller.current) clearTimeout(poller.current);
    };
  }, [pollJob]);

  const sliderRef = useRef(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const updateScrollButtons = useCallback(() => {
    const el = sliderRef.current;
    if (!el) return;
    const { scrollLeft, scrollWidth, clientWidth } = el;
    setCanScrollLeft(scrollLeft > 6);
    setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 6);
  }, []);

  useEffect(() => {
    const el = sliderRef.current;
    if (!el) return;
    updateScrollButtons();
    const handleScroll = () => updateScrollButtons();
    el.addEventListener("scroll", handleScroll, { passive: true });
    window.addEventListener("resize", handleScroll);
    return () => {
      el.removeEventListener("scroll", handleScroll);
      window.removeEventListener("resize", handleScroll);
    };
  }, [fileList.length, updateScrollButtons]);

  const scrollSlider = (direction) => {
    const el = sliderRef.current;
    if (!el) return;
    const scrollAmount = direction === "left" ? -280 : 280;
    el.scrollBy({ left: scrollAmount, behavior: "smooth" });
  };

  const processFiles = (files) => {
    const selected = Array.from(files);
    selected.forEach(async (file) => {
      const itemId = `${file.name}-${Date.now()}-${Math.random()}`;
      if (file.size > 20 * 1024 * 1024) {
        toast.error(`${file.name} is larger than 20 MB.`);
        return;
      }
      setFileList((items) => [...items, {
        id: itemId,
        rawFile: file,
        name: file.name,
        fileType: file.type || file.name.split(".").pop(),
        sizeLabel: fmtBytes(file.size),
        progress: 0,
        status: "uploading",
        materialId: null,
        error: null,
      }]);
      try {
        const request = uploadMaterial(file, file.name, (progress) => {
          setFileList((items) => items.map((item) =>
            item.id === itemId ? { ...item, progress } : item
          ));
        });
        const material = await request.promise;
        setFileList((items) => items.map((item) =>
          item.id === itemId
            ? {
                ...item,
                status: "uploaded",
                progress: 100,
                materialId: material.id,
                fileType: material.file_type || item.fileType,
                rawFile: null,
                error: null,
              }
            : item
        ));
        if (material?.id) {
          setSelectedIds((prev) => new Set([...prev, material.id]));
        }
        toast.success(`Uploaded "${file.name}" successfully.`);
      } catch (err) {
        // Failed resource upload (just upload) shouldn't be shown
        setFileList((items) => items.filter((item) => item.id !== itemId));
        toast.error(err.message || `Failed to upload "${file.name}".`);
      }
    });
  };

  const handleFileChange = (event) => {
    processFiles(event.target.files);
    event.target.value = "";
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      processFiles(e.dataTransfer.files);
    }
  };

  const handleConfirmDelete = async () => {
    if (!materialToDelete) return;
    setIsDeleting(true);
    try {
      if (materialToDelete.materialId) {
        await deleteMaterial(materialToDelete.materialId);
        setSelectedIds((prev) => {
          const next = new Set(prev);
          next.delete(materialToDelete.materialId);
          return next;
        });
      }
      setFileList((items) => items.filter((candidate) => candidate.id !== materialToDelete.id));
      toast.success(`Deleted "${materialToDelete.name}" successfully.`);
      setMaterialToDelete(null);
    } catch (err) {
      toast.error(err.message || "Failed to delete material.");
    } finally {
      setIsDeleting(false);
    }
  };

  const toggleMaterialSelection = (materialId) => {
    if (!materialId) return;
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(materialId)) {
        next.delete(materialId);
      } else {
        next.add(materialId);
      }
      return next;
    });
  };

  const availableMaterialIds = fileList
    .filter((item) => item.status === "uploaded" && item.materialId)
    .map((item) => item.materialId);

  const toggleSelectAll = () => {
    if (selectedIds.size === availableMaterialIds.length) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(availableMaterialIds));
    }
  };

  const handleGenerate = async () => {
    const targetMaterialIds = availableMaterialIds.filter((id) => selectedIds.has(id));
    if (!targetMaterialIds.length) {
      setError(fileList.length === 0 ? "Upload at least one material first." : "Select at least one material to generate a quiz.");
      return;
    }
    setError("");
    try {
      const created = await generateQuizBackground({
        material_ids: targetMaterialIds,
        question_count: numQuestions,
        difficulty,
        question_types: ["multiple_choice", "true_false"],
      });
      setJob(created);
      toast.info("Quiz generation started. You can safely leave this page.");
      pollJob(created.id);
    } catch (err) {
      setError(err.message || "Unable to start quiz generation.");
    }
  };

  const handleRetryJob = async () => {
    if (!job || isRetryingJob) return;
    setIsRetryingJob(true);
    setError("");
    try {
      let retriedJob;
      try {
        retriedJob = await retryGenerationJob(job.id);
      } catch {
        // Fallback to background generation using existing job parameters or current selection
        let fallbackMaterialIds = job.material_ids?.length
          ? job.material_ids
          : availableMaterialIds.filter((id) => selectedIds.has(id));
        if (!fallbackMaterialIds?.length) {
          fallbackMaterialIds = availableMaterialIds.length ? availableMaterialIds : Array.from(selectedIds);
        }
        if (!fallbackMaterialIds?.length) {
          throw new Error("No study materials found to retry generation.");
        }
        retriedJob = await generateQuizBackground({
          material_ids: fallbackMaterialIds,
          question_count: job.question_count || numQuestions || 10,
          difficulty: job.difficulty || difficulty || "medium",
          question_types: job.question_types || ["multiple_choice", "true_false"],
        });
      }
      setJob(retriedJob);
      toast.info("Quiz generation restarted.");
      pollJob(retriedJob.id);
    } catch (err) {
      console.error("Retry failed:", err);
      setError(err.message || "Failed to retry quiz generation.");
      toast.error(err.message || "Unable to retry quiz generation.");
    } finally {
      setIsRetryingJob(false);
    }
  };

  const handleStartQuizFromJob = async (quizId) => {
    try {
      setIsStartingQuiz(true);
      const attempt = await startAttempt(quizId);
      navigate(`/quiz?id=${quizId}&attempt_id=${attempt.id}`);
    } catch {
      navigate(`/quiz?id=${quizId}`);
    } finally {
      setIsStartingQuiz(false);
    }
  };

  if (restoring) {
    return <section className="upload-material"><h1>Upload Material</h1><p>Loading...</p></section>;
  }

  const generating = job && ["queued", "processing"].includes(job.status);
  const isAnyUploading = fileList.some((item) => item.status === "uploading");
  const targetMaterialIds = availableMaterialIds.filter((id) => selectedIds.has(id));
  const stageLabel = job?.current_stage
    ?.replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
  const jobTitle = job?.status === "completed"
    ? "Quiz ready"
    : job?.status === "failed"
      ? "Generation failed"
      : job?.status === "queued"
        ? "Waiting to start"
        : "Generating your quiz";
  return (
    <section className="upload-material">
      <div className="upload-material__header">
        <h1>Upload Material</h1>
        <p>Upload materials now. They are processed only when you generate a quiz.</p>
      </div>

      <div
        className={`upload-material__box ${isDragging ? "upload-material__box--dragging" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <div className="upload-material__icon"><Upload size={24} /></div>
        <h2>Upload your study material</h2>
        <p>Drag and drop files here, or browse your device (PDF, DOC, DOCX, TXT, or images).</p>
        <label className="upload-material__button">
          Choose Files
          <input
            type="file"
            accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg"
            multiple
            onChange={handleFileChange}
          />
        </label>
        <span className="upload-material__formats">Maximum 20 MB per file · Multiple files supported</span>
      </div>

      {error && <p className="upload-material__error">{error}</p>}

      {fileList.length > 0 && (
        <div className="upload-material__slider-section">
          <div className="upload-material__slider-header">
            <div className="upload-material__slider-title-wrap">
              <h3>Uploaded Materials</h3>
              <span className="upload-material__slider-subtitle">
                {selectedIds.size} of {availableMaterialIds.length} selected for quiz
              </span>
            </div>

            <div className="upload-material__slider-actions">
              {availableMaterialIds.length > 1 && (
                <button
                  type="button"
                  className="upload-material__select-all-btn"
                  onClick={toggleSelectAll}
                >
                  {selectedIds.size === availableMaterialIds.length ? "Deselect all" : "Select all"}
                </button>
              )}

              <div className="upload-material__slider-nav">
                <button
                  type="button"
                  className="upload-material__nav-btn"
                  onClick={() => scrollSlider("left")}
                  disabled={!canScrollLeft}
                  aria-label="Scroll left"
                  title="Scroll left"
                >
                  <ChevronLeft size={18} />
                </button>
                <button
                  type="button"
                  className="upload-material__nav-btn"
                  onClick={() => scrollSlider("right")}
                  disabled={!canScrollRight}
                  aria-label="Scroll right"
                  title="Scroll right"
                >
                  <ChevronRight size={18} />
                </button>
              </div>
            </div>
          </div>

          <div className="upload-material__slider-viewport">
            {canScrollLeft && (
              <div className="upload-material__slider-fade upload-material__slider-fade--left" />
            )}
            {canScrollRight && (
              <div className="upload-material__slider-fade upload-material__slider-fade--right" />
            )}

            <div className="upload-material__slider-track" ref={sliderRef}>
              {fileList.map((item) => {
                const isSelected = Boolean(item.materialId && selectedIds.has(item.materialId));
                const isReady = item.status === "uploaded" && Boolean(item.materialId);
                const isUploading = item.status === "uploading";

                return (
                  <div
                    key={item.id}
                    className={`material-card ${isSelected ? "material-card--selected" : ""} ${
                      isUploading ? "material-card--uploading" : ""
                    } ${item.error ? "material-card--error" : ""}`}
                    onClick={() => {
                      if (isReady) {
                        toggleMaterialSelection(item.materialId);
                      }
                    }}
                    onKeyDown={(e) => {
                      if ((e.key === "Enter" || e.key === " ") && isReady) {
                        e.preventDefault();
                        toggleMaterialSelection(item.materialId);
                      }
                    }}
                    role="button"
                    tabIndex={isReady ? 0 : -1}
                    aria-pressed={isSelected}
                    title={item.name}
                  >
                    <div className="material-card__top">
                      <FileTypeLogo filename={item.name} fileType={item.fileType} />

                      <div className="material-card__actions">
                        {isReady && (
                          <div
                            className={`material-card__check ${
                              isSelected ? "material-card__check--selected" : ""
                            }`}
                            aria-hidden="true"
                          >
                            {isSelected && <Check size={12} strokeWidth={3} />}
                          </div>
                        )}
                        <button
                          type="button"
                          className="material-card__delete-btn"
                          onClick={(e) => {
                            e.stopPropagation();
                            setMaterialToDelete(item);
                          }}
                          aria-label={`Delete ${item.name}`}
                          title="Delete material"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    <div className="material-card__body">
                      <strong className="material-card__name" title={item.name}>
                        {item.name}
                      </strong>

                      <div className="material-card__meta">
                        {isUploading ? (
                          <div className="material-card__uploading-meta">
                            <div className="material-card__progress-bar">
                              <div
                                className="material-card__progress-fill"
                                style={{ width: `${item.progress}%` }}
                              />
                            </div>
                            <span className="material-card__status-text">
                              Uploading {item.progress}%
                            </span>
                          </div>
                        ) : item.error ? (
                          <span className="material-card__status-error">
                            {item.error}
                          </span>
                        ) : (
                          <div className="material-card__ready-meta">
                            <span className="material-card__size">{item.sizeLabel}</span>
                            <span className="material-card__status-ready">Ready</span>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="material-card__footer">
                      <span
                        className={`material-card__select-label ${
                          isSelected ? "material-card__select-label--active" : ""
                        }`}
                      >
                        {isUploading
                          ? "Uploading..."
                          : isSelected
                            ? "Selected for quiz"
                            : "Click to select"}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <div className="upload-material__config-card">
        <div className="upload-material__config-header">
          <div className="upload-material__config-title-wrap">
            <div className="upload-material__config-icon">
              <Sparkles size={20} />
            </div>
            <div>
              <h3>Configure Quiz</h3>
              <p>Set question volume, difficulty, and generate from selected materials.</p>
            </div>
          </div>
          <div className="upload-material__selection-badge">
            <span className="upload-material__badge-count">{targetMaterialIds.length}</span>
            <span>materials selected</span>
          </div>
        </div>

        <div className="upload-material__config-body">
          <div className="upload-material__config-field">
            <div className="upload-material__field-header">
              <label htmlFor="question-count-input" className="upload-material__field-label">
                Questions
              </label>
              <span className="upload-material__field-hint">1 to 50 questions</span>
            </div>
            <div className="upload-material__presets-row">
              {[5, 10, 15, 20].map((preset) => (
                <button
                  key={preset}
                  type="button"
                  className={`upload-material__preset-chip ${numQuestions === preset ? "upload-material__preset-chip--active" : ""}`}
                  onClick={() => setNumQuestions(preset)}
                  disabled={generating}
                >
                  {preset}
                </button>
              ))}
              <div className="upload-material__custom-input-wrap">
                <input
                  id="question-count-input"
                  type="number"
                  min="1"
                  max="50"
                  value={numQuestions}
                  onChange={(event) => {
                    const val = parseInt(event.target.value, 10);
                    if (!isNaN(val)) {
                      setNumQuestions(Math.max(1, Math.min(50, val)));
                    } else {
                      setNumQuestions("");
                    }
                  }}
                  onBlur={() => {
                    if (!numQuestions || numQuestions < 1) setNumQuestions(10);
                  }}
                  className="upload-material__number-input"
                  disabled={generating}
                  placeholder="Custom"
                />
              </div>
            </div>
          </div>

          <div className="upload-material__config-field">
            <div className="upload-material__field-header">
              <label className="upload-material__field-label">Difficulty</label>
              <span className="upload-material__field-hint">Target knowledge depth</span>
            </div>
            <div className="upload-material__difficulty-row">
              {[
                { id: "easy", label: "Easy", desc: "Foundational concepts" },
                { id: "medium", label: "Medium", desc: "Comprehensive review" },
                { id: "hard", label: "Hard", desc: "Advanced application" },
              ].map((lvl) => (
                <button
                  key={lvl.id}
                  type="button"
                  className={`upload-material__diff-chip ${difficulty === lvl.id ? "upload-material__diff-chip--active" : ""}`}
                  onClick={() => setDifficulty(lvl.id)}
                  disabled={generating}
                >
                  <span className="upload-material__diff-label">{lvl.label}</span>
                  <span className="upload-material__diff-desc">{lvl.desc}</span>
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="upload-material__config-footer">
          <div className="upload-material__footer-info">
            {targetMaterialIds.length === 0 ? (
              <span className="upload-material__footer-hint upload-material__footer-hint--warn">
                Upload or select at least 1 study material above to enable quiz generation.
              </span>
            ) : (
              <span className="upload-material__footer-hint">
                Ready to generate {numQuestions || 10} questions from {targetMaterialIds.length} material{targetMaterialIds.length > 1 ? "s" : ""}.
              </span>
            )}
          </div>
          <button
            type="button"
            className="upload-material__generate-btn"
            onClick={handleGenerate}
            disabled={generating || isAnyUploading || targetMaterialIds.length === 0}
          >
            {generating ? (
              <>
                <Loader2 size={18} className="upload-material__spin" />
                <span>Generating Quiz...</span>
              </>
            ) : (
              <>
                <Sparkles size={18} />
                <span>Generate Quiz</span>
              </>
            )}
          </button>
        </div>
      </div>

      {job && (
        <div className={`upload-material__processing upload-material__processing--${job.status}`}>
          <div className="upload-material__processing-header">
            <div>
              <span className="upload-material__eyebrow">Generation Job</span>
              <h2>{jobTitle}</h2>
            </div>
            <div className="upload-material__processing-badges">
              <span className={`upload-material__status-pill upload-material__status-pill--${job.status}`}>
                {job.status}
              </span>
              {!generating && (
                <button
                  type="button"
                  className="upload-material__dismiss-btn"
                  onClick={() => setJob(null)}
                  aria-label="Dismiss job status"
                >
                  <X size={16} />
                </button>
              )}
            </div>
          </div>
          <div className="upload-material__job-details">
            <div><span>Materials</span><strong>{job.material_ids?.length || 1} selected</strong></div>
            <div><span>Questions</span><strong>{job.question_count}</strong></div>
            <div><span>Progress</span><strong>{job.progress}%</strong></div>
          </div>
          <div className="upload-material__progress-bar-wrap">
            <div className="upload-material__progress-bar-fill" style={{ width: `${job.progress}%` }} />
          </div>
          <p className="upload-material__job-stage">
            {stageLabel || "Waiting to start"}{generating ? " · This may take a few minutes." : ""}
          </p>
          {job.status === "completed" && job.quiz_id && (
            <button
              type="button"
              className="upload-material__start-btn"
              onClick={() => handleStartQuizFromJob(job.quiz_id)}
              disabled={isStartingQuiz}
            >
              {isStartingQuiz ? (
                <>
                  <Loader2 size={16} className="upload-material__spin" />
                  <span>Starting Quiz...</span>
                </>
              ) : (
                <>
                  <span>Start Quiz</span>
                  <ArrowRight size={16} />
                </>
              )}
            </button>
          )}
          {job.status === "failed" && (
            <div className="upload-material__job-failed-actions">
              <p className="upload-material__error">
                {job.error_message || "We couldn't generate this quiz. Please try again."}
              </p>
              <button
                type="button"
                className="upload-material__retry-job-btn"
                onClick={handleRetryJob}
                disabled={isRetryingJob}
              >
                {isRetryingJob ? (
                  <>
                    <Loader2 size={15} className="upload-material__spin" />
                    <span>Retrying...</span>
                  </>
                ) : (
                  <>
                    <RotateCcw size={15} />
                    <span>Try Again</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {materialToDelete && (
        <div
          className="material-delete-modal-overlay"
          onClick={() => !isDeleting && setMaterialToDelete(null)}
        >
          <div className="material-delete-modal" onClick={(e) => e.stopPropagation()}>
            <div className="material-delete-modal__header">
              <div className="material-delete-modal__icon">
                <Trash2 size={20} />
              </div>
              <div>
                <h3>Delete Study Material</h3>
                <p>This action cannot be undone.</p>
              </div>
            </div>

            <p className="material-delete-modal__text">
              Are you sure you want to delete <strong title={materialToDelete.name}>{materialToDelete.name}</strong>? This will permanently remove the material and any quizzes generated from it.
            </p>

            <div className="material-delete-modal__actions">
              <button
                type="button"
                className="material-delete-modal__btn-cancel"
                onClick={() => setMaterialToDelete(null)}
                disabled={isDeleting}
              >
                Cancel
              </button>
              <button
                type="button"
                className="material-delete-modal__btn-delete"
                onClick={handleConfirmDelete}
                disabled={isDeleting}
              >
                {isDeleting ? (
                  <>
                    <Loader2 size={15} className="upload-material__spin" />
                    <span>Deleting...</span>
                  </>
                ) : (
                  <span>Delete Material</span>
                )}
              </button>
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

export default UploadMaterial;
