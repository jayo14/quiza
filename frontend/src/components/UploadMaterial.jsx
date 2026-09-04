import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Upload, X, Sparkles, CheckCircle } from "lucide-react";
import { uploadMaterial, generateQuiz } from "../services/apiClient";
import "./UploadMaterial.css";

function UploadMaterial() {
  const [files, setFiles] = useState([]);
  const [error, setError] = useState("");
  const [isGenerating, setIsGenerating] = useState(false);
  const [isGenerated, setIsGenerated] = useState(false);
  const [generatedQuizId, setGeneratedQuizId] = useState(null);
  const navigate = useNavigate();

  const handleFileChange = (event) => {
    const selectedFiles = Array.from(event.target.files);

    setError("");

    const validFiles = [];
    const rejectedFiles = [];

    selectedFiles.forEach((file) => {
      const fileSizeMB = file.size / (1024 * 1024);

      if (fileSizeMB > 20) {
        rejectedFiles.push(`${file.name} is larger than 20 MB`);
      } else {
        validFiles.push(file);
      }
    });

    if (rejectedFiles.length > 0) {
      setError(rejectedFiles.join(". "));
    }

    setFiles((previousFiles) => [...previousFiles, ...validFiles]);

    event.target.value = "";
  };

  const removeFile = (fileToRemove) => {
    setFiles((previousFiles) =>
      previousFiles.filter((file) => file !== fileToRemove),
    );
  };

  const handleGenerateQuiz = async () => {
    if (files.length === 0) return;

    setIsGenerating(true);
    setIsGenerated(false);
    setError("");

    try {
      const fileToUpload = files[0];
      const material = await uploadMaterial(fileToUpload, fileToUpload.name);

      const quiz = await generateQuiz({
        material_id: material.id,
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

          {files.length > 0 && (
            <div className="upload-material__files">
              <h3>Selected Materials</h3>

              {files.map((file) => (
                <div className="upload-material__file" key={file.name}>
                  <div>
                    <strong>{file.name}</strong>
                    <span>{(file.size / (1024 * 1024)).toFixed(2)} MB</span>
                  </div>

                  <button
                    type="button"
                    onClick={() => removeFile(file)}
                    aria-label={`Remove ${file.name}`}
                  >
                    <X size={18} />
                  </button>
                </div>
              ))}

              <button
                type="button"
                className="upload-material__generate"
                onClick={handleGenerateQuiz}
              >
                <Sparkles size={18} />
                Generate Quiz
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
