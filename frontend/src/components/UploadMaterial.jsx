import { useState } from "react";
import "./UploadMaterial.css";

function UploadMaterial() {
  const [file, setFile] = useState(null);

  const handleFileChange = (event) => {
    const selectedFile = event.target.files[0];

    if (selectedFile) {
      setFile(selectedFile);
    }
  };

  return (
    <section className="upload-material">
      <div className="upload-material__header">
        <h1>Upload Material</h1>
        <p>Upload your study material and let Quiza turn it into a quiz.</p>
      </div>

      <div className="upload-material__box">
        <div className="upload-material__icon">↑</div>

        <h2>Upload your study material</h2>

        <p>Drag and drop your file here, or choose a file from your device.</p>

        <label className="upload-material__button">
          Choose File
          <input
            type="file"
            accept=".pdf,.docx,.txt"
            onChange={handleFileChange}
          />
        </label>

        {file && (
          <p className="upload-material__filename">Selected: {file.name}</p>
        )}

        <span className="upload-material__formats">
          Supported formats: PDF, DOCX, TXT
        </span>
      </div>
    </section>
  );
}

export default UploadMaterial;
