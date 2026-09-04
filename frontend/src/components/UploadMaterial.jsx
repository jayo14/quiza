import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, X, Sparkles, CheckCircle, Loader2 } from "lucide-react";
import { uploadMaterial, generateQuiz, deleteMaterial } from "../services/apiClient";
import "./UploadMaterial.css";

function UploadMaterial() {
  const [fileList, setFileList] = useState([]);
  const [error, setError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGenerated, setIsGenerated] = useState(false);
  const [generatedQuizId, setGeneratedQuizId] = useState(null);
  const navigate = useNavigate();

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
          uploading: true,
          uploaded: false,
          materialId: null,
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

      setFileList((prev) =>
        prev.map((f) =>
          f.id === item.id
            ? {
                ...f,
                progress: 100,
                currentLoadedMB: f.totalSizeMB,
                uploading: false,
                uploaded: true,
                materialId: material.id,
              }
            : f
        )
      );
    } catch (err) {
      if (err.message !== "Upload cancelled") {
        console.error(`Upload error for ${item.name}:`, err);
        setError(`Failed to upload ${item.name}: ${err.message}`);
      }
      setFileList((prev) =>
        prev.map((f) =>
          f.id === item.id
            ? {
                ...f,
                uploading: false,
                uploaded: false,
                error: err.message,
              }
            : f
        )
      );
    }
  };

  const removeFile = async (idToRemove) => {
    const item = fileList.find((f) => f.id === idToRemove);
    if (item) {
      if (item.cancelUpload && item.uploading) {
        item.cancelUpload();
      }
      if (item.materialId) {
        try {
          await deleteMaterial(item.materialId);
        } catch (err) {
          console.error("Failed to delete cancelled material:", err);
        }
      }
    }
    setFileList((prev) => prev.filter((item) => item.id !== idToRemove));
  };

  const isAnyUploading = fileList.some((item) => item.uploading);
  const allUploaded =
    fileList.length > 0 && fileList.every((item) => item.uploaded);

  const handleGenerateQuiz = async () => {
    if (!allUploaded) return;

    setIsGenerating(true);
    setIsGenerated(false);
    setError("");

    try {
      const uploadedMaterialId = fileList[0].materialId;

      const quiz = await generateQuiz({
        material_id: uploadedMaterialId,
        number_of_questions: 5,
        difficulty: "medium",
        question_types: ["multiple_choice"],
      });

      setGeneratedQuizId(quiz.id);
      setIsGenerated(true);
    } catch (err) {
      console.error("Quiz generation failed:", err);
      setError(err.message || "Failed to generate quiz. Please try again.");
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
                      <span className="upload-material__file-status">
                        {item.uploaded
                          ? item.totalSizeMB
                          : `${item.currentLoadedMB} / ${item.totalSizeMB} (${item.progress}%)`}
                      </span>
                    </div>

                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                      {item.uploading && (
                        <Loader2
                          size={16}
                          className="upload-material__spin"
                          style={{ color: "var(--primary)" }}
                        />
                      )}
                      {item.uploaded && (
                        <CheckCircle
                          size={18}
                          style={{ color: "#10b981" }}
                        />
                      )}
                      <button
                        type="button"
                        onClick={() => removeFile(item.id)}
                        aria-label={`Remove ${item.name}`}
                      >
                        <X size={18} />
                      </button>
                    </div>
                  </div>

                  {!item.uploaded && (
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
                disabled={!allUploaded || isAnyUploading}
              >
                <Sparkles size={18} />
                {isAnyUploading ? "Uploading Material..." : "Generate Quiz"}
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
