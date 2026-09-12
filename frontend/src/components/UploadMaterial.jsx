import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Loader2, Upload, X } from "lucide-react";
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
        setFileList((materials || []).map(materialToItem));
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

  const handleFileChange = (event) => {
    const selected = Array.from(event.target.files);
    event.target.value = "";
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
      } catch (err) {
        setFileList((items) => items.map((item) =>
          item.id === itemId ? { ...item, status: "error", error: err.message } : item
        ));
      }
    });
  };

  const removeMaterial = async (item) => {
    if (item.materialId) await deleteMaterial(item.materialId).catch(() => {});
    setFileList((items) => items.filter((candidate) => candidate.id !== item.id));
  };

  const handleGenerate = async () => {
    const materialIds = fileList
      .filter((item) => item.status === "uploaded" && item.materialId)
      .map((item) => item.materialId);
    if (!materialIds.length) {
      setError("Upload at least one material first.");
      return;
    }
    setError("");
    try {
      const created = await generateQuizBackground({
        material_ids: materialIds,
        question_count: numQuestions,
        difficulty: "medium",
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

      <div className="upload-material__box">
        <div className="upload-material__icon"><Upload size={24} /></div>
        <h2>Upload your study material</h2>
        <p>Choose one or more PDF, DOCX, or TXT files.</p>
        <label className="upload-material__button">
          Choose Files
          <input type="file" accept=".pdf,.docx,.txt" multiple onChange={handleFileChange} />
        </label>
        <span className="upload-material__formats">Maximum 20 MB per file</span>
      </div>

      {error && <p className="upload-material__error">{error}</p>}
      {fileList.length > 0 && (
        <div className="upload-material__files">
          <h3>Materials</h3>
          {fileList.map((item) => (
            <div className="upload-material__file" key={item.id}>
              <div>
                <strong>{item.name}</strong>
                <span className="upload-material__file-status">
                  {item.status === "uploading" ? `${item.progress}%` : item.error || `${item.sizeLabel} · Uploaded`}
                </span>
              </div>
              <button type="button" onClick={() => removeMaterial(item)} aria-label={`Remove ${item.name}`}>
                <X size={16} />
              </button>
            </div>
          ))}
        </div>
      )}

      <div className="upload-material__actions">
        <label>
          Questions
          <input
            type="number"
            min="1"
            max="50"
            value={numQuestions}
            onChange={(event) => setNumQuestions(Number(event.target.value))}
            disabled={generating}
          />
        </label>
        <button type="button" onClick={handleGenerate} disabled={generating || fileList.some((item) => item.status === "uploading")}>
          {generating ? <><Loader2 size={16} className="upload-material__spin" /> Generating...</> : "Generate Quiz"}
        </button>
      </div>

      {job && (
        <div className={`upload-material__processing upload-material__processing--${job.status}`}>
          <div className="upload-material__processing-header">
            <div>
              <span className="upload-material__eyebrow">Generation job</span>
              <h2>{jobTitle}</h2>
            </div>
            <span className="upload-material__status-pill">{job.status}</span>
          </div>
          <div className="upload-material__job-details">
            <div><span>Materials</span><strong>{job.material_ids.length} selected</strong></div>
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
            <button type="button" onClick={() => navigate(`/quiz?id=${job.quiz_id}`)}>
              Start Quiz
            </button>
          )}
          {job.status === "failed" && (
            <p className="upload-material__error">{job.error_message || "We couldn't generate this quiz. Please try again."}</p>
          )}
        </div>
      )}
    </section>
  );
}

export default UploadMaterial;
