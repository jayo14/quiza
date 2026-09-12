import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowRight, Loader2, RotateCcw, Sparkles, Upload, X } from "lucide-react";
import { toast } from "sonner";
import {
  deleteMaterial,
  generateQuizBackground,
  getGenerationJob,
  listGenerationJobs,
  listMaterials,
  uploadMaterial,
} from "../services/apiClient";
import "./UploadMaterial.css";

const POLL_INTERVAL = 2500;

const fmtBytes = (bytes) => {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
};

function materialToItem(material) {
  return {
    id: `mat-${material.id}`,
    rawFile: null,
    name: material.filename,
    sizeLabel: fmtBytes(material.file_size),
    progress: 100,
    status: material.status === "failed" ? "error" : "uploaded",
    materialId: material.id,
    error: material.processing_error || null,
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

  const [isDragging, setIsDragging] = useState(false);

  const processFiles = (files) => {
    const selected = Array.from(files);
    selected.forEach(async (file) => {
      const itemId = `${file.name}-${Date.now()}-${Math.random()}`;
      if (file.size > 20 * 1024 * 1024) {
        setError(`${file.name} is larger than 20 MB.`);
        return;
      }
      setFileList((items) => [...items, {
        id: itemId,
        rawFile: file,
        name: file.name,
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
            ? { ...item, status: "uploaded", progress: 100, materialId: material.id, rawFile: null }
            : item
        ));
        if (material?.id) {
          setSelectedIds((prev) => new Set([...prev, material.id]));
        }
      } catch (err) {
        setFileList((items) => items.map((item) =>
          item.id === itemId ? { ...item, status: "error", error: err.message } : item
        ));
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

  const removeMaterial = async (item) => {
    if (item.materialId) {
      await deleteMaterial(item.materialId).catch(() => {});
      setSelectedIds((prev) => {
        const next = new Set(prev);
        next.delete(item.materialId);
        return next;
      });
    }
    setFileList((items) => items.filter((candidate) => candidate.id !== item.id));
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
        <div className="upload-material__files">
          <div className="upload-material__files-header">
            <div>
              <h3>Materials</h3>
              <span className="upload-material__files-subtitle">
                {selectedIds.size} of {availableMaterialIds.length} selected for quiz
              </span>
            </div>
            {availableMaterialIds.length > 1 && (
              <button
                type="button"
                className="upload-material__select-all-btn"
                onClick={toggleSelectAll}
              >
                {selectedIds.size === availableMaterialIds.length ? "Deselect all" : "Select all"}
              </button>
            )}
          </div>
          {fileList.map((item) => (
            <div
              className={`upload-material__file ${
                item.materialId && selectedIds.has(item.materialId) ? "upload-material__file--selected" : ""
              }`}
              key={item.id}
            >
              <div className="upload-material__file-left">
                {item.status === "uploaded" && item.materialId && (
                  <input
                    type="checkbox"
                    className="upload-material__checkbox"
                    checked={selectedIds.has(item.materialId)}
                    onChange={() => toggleMaterialSelection(item.materialId)}
                    aria-label={`Select ${item.name} for quiz`}
                  />
                )}
                <div className="upload-material__file-details">
                  <strong>{item.name}</strong>
                  <span className="upload-material__file-status">
                    {item.status === "uploading" ? `${item.progress}%` : item.error || `${item.sizeLabel} · Ready`}
                  </span>
                </div>
              </div>
              <button type="button" onClick={() => removeMaterial(item)} aria-label={`Remove ${item.name}`}>
                <X size={16} />
              </button>
            </div>
          ))}
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
              onClick={() => navigate(`/quiz?id=${job.quiz_id}`)}
            >
              <span>Start Quiz</span>
              <ArrowRight size={16} />
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
                onClick={handleGenerate}
              >
                <RotateCcw size={15} />
                <span>Try Again</span>
              </button>
            </div>
          )}
        </div>
      )}
    </section>
  );
}

export default UploadMaterial;
