import { API_BASE_URL } from "../config/api";

const DEFAULT_TIMEOUT = 30000;

async function fetchWithTimeout(url, options = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    clearTimeout(timeoutId);
    return response;
  } catch (err) {
    clearTimeout(timeoutId);
    if (err.name === "AbortError") {
      throw new Error("Request timed out. Please try again.");
    }
    throw err;
  }
}

function isValidId(id) {
  return typeof id === "string" && /^[0-9a-f-]{36}$/i.test(id);
}

const getAuthHeaders = () => {
  const token = localStorage.getItem("access_token");
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
};

async function handleResponse(response) {
  if (response.status === 204) {
    return null;
  }
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("user");
    if (window.location.pathname !== "/signin") {
      window.location.href = "/signin";
    }
  }
  if (!response.ok) {
    const errorMsg =
      typeof data.detail === "string"
        ? data.detail
        : data.detail?.[0]?.msg || "API request failed";
    throw new Error(errorMsg);
  }
  return data;
}

// --- Health ---
export async function getHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/ping`);
    if (!response.ok) return { status: "offline" };
    return await response.json();
  } catch {
    return { status: "offline" };
  }
}

// --- Materials ---
export function uploadMaterial(file, title, onProgress) {
  let xhrRef = null;
  const promise = new Promise((resolve, reject) => {
    const token = localStorage.getItem("access_token");
    const formData = new FormData();
    formData.append("file", file);
    if (title) formData.append("title", title);

    const xhr = new XMLHttpRequest();
    xhrRef = xhr;
    xhr.open("POST", `${API_BASE_URL}/materials`);

    if (token) {
      xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    }

    if (xhr.upload && onProgress) {
      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.round(
            (event.loaded / event.total) * 100
          );
          onProgress(percentComplete, event.loaded, event.total);
        }
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const data = JSON.parse(xhr.responseText);
          resolve(data);
        } catch {
          resolve({});
        }
      } else {
        try {
          const data = JSON.parse(xhr.responseText);
          const errorMsg =
            typeof data.detail === "string"
              ? data.detail
              : data.detail?.[0]?.msg || "Upload failed";
          reject(new Error(errorMsg));
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    };

    xhr.onabort = () => reject(new Error("Upload cancelled"));
    xhr.onerror = () => reject(new Error("Network error during file upload"));
    xhr.send(formData);
  });

  return {
    promise,
    cancel: () => {
      if (xhrRef) xhrRef.abort();
    },
  };
}

export async function listMaterials() {
  const response = await fetchWithTimeout(`${API_BASE_URL}/materials`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function getMaterial(materialId) {
  if (!isValidId(materialId)) throw new Error("Invalid material ID");
  const response = await fetchWithTimeout(`${API_BASE_URL}/materials/${materialId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function deleteMaterial(materialId) {
  if (!isValidId(materialId)) throw new Error("Invalid material ID");
  const response = await fetch(`${API_BASE_URL}/materials/${materialId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

// --- Quizzes ---
export async function generateQuiz({
  material_id,
  material_ids,
  number_of_questions = 5,
  difficulty = "medium",
  question_types = ["multiple_choice"],
}) {
  const response = await fetchWithTimeout(`${API_BASE_URL}/quizzes/generate`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      material_id,
      material_ids,
      number_of_questions,
      difficulty,
      question_types,
    }),
  });
  return handleResponse(response);
}

export async function generateQuizBackground({
  material_id,
  material_ids,
  number_of_questions = 10,
  difficulty = "medium",
  question_types = ["multiple_choice"],
}) {
  const response = await fetchWithTimeout(`${API_BASE_URL}/quizzes/generate-background`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      material_id,
      material_ids,
      number_of_questions,
      difficulty,
      question_types,
    }),
  });
  return handleResponse(response);
}

export async function listQuizzes() {
  const response = await fetchWithTimeout(`${API_BASE_URL}/quizzes`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function getQuiz(quizId) {
  if (!isValidId(quizId)) throw new Error("Invalid quiz ID");
  const response = await fetchWithTimeout(`${API_BASE_URL}/quizzes/${quizId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function deleteQuiz(quizId) {
  if (!isValidId(quizId)) throw new Error("Invalid quiz ID");
  const response = await fetch(`${API_BASE_URL}/quizzes/${quizId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function getQuizQuestions(quizId) {
  if (!isValidId(quizId)) throw new Error("Invalid quiz ID");
  const response = await fetch(`${API_BASE_URL}/quizzes/${quizId}/questions`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function startAttempt(quizId) {
  if (!isValidId(quizId)) throw new Error("Invalid quiz ID");
  const response = await fetchWithTimeout(`${API_BASE_URL}/quizzes/${quizId}/attempts`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

// --- Attempts ---
export async function submitAttempt(attemptId, answers) {
  if (!isValidId(attemptId)) throw new Error("Invalid attempt ID");
  const response = await fetchWithTimeout(`${API_BASE_URL}/attempts/${attemptId}/submit`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ answers }),
  });
  return handleResponse(response);
}

export async function getAttempt(attemptId) {
  if (!isValidId(attemptId)) throw new Error("Invalid attempt ID");
  const response = await fetchWithTimeout(`${API_BASE_URL}/attempts/${attemptId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function listAttempts() {
  const response = await fetchWithTimeout(`${API_BASE_URL}/attempts`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

// --- Summaries ---
export async function getAttemptSummary(attemptId) {
  if (!isValidId(attemptId)) throw new Error("Invalid attempt ID");
  const response = await fetchWithTimeout(
    `${API_BASE_URL}/attempts/${attemptId}/summary`,
    {
      headers: getAuthHeaders(),
    }
  );
  return handleResponse(response);
}

// --- Analytics ---
export async function listWeaknesses() {
  const response = await fetchWithTimeout(`${API_BASE_URL}/analytics/weaknesses`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function listTopicMastery() {
  const response = await fetchWithTimeout(`${API_BASE_URL}/analytics/topics`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

// --- Practice ---
export async function generatePractice({
  material_id,
  number_of_questions = 5,
  question_types = ["multiple_choice"],
  topics = [],
}) {
  const response = await fetchWithTimeout(`${API_BASE_URL}/practice/generate`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      material_id,
      number_of_questions,
      question_types,
      topics,
    }),
  });
  return handleResponse(response);
}
