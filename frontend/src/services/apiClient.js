import { API_BASE_URL } from "../config/api";

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
  const rootUrl = API_BASE_URL.replace(/\/api\/v1\/?$/, "");
  const response = await fetch(`${rootUrl}/health`);
  return handleResponse(response);
}

// --- Materials ---
export async function uploadMaterial(file, title) {
  const token = localStorage.getItem("access_token");
  const formData = new FormData();
  formData.append("file", file);
  if (title) formData.append("title", title);

  const response = await fetch(`${API_BASE_URL}/materials`, {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: formData,
  });
  return handleResponse(response);
}

export async function listMaterials() {
  const response = await fetch(`${API_BASE_URL}/materials`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function deleteMaterial(materialId) {
  const response = await fetch(`${API_BASE_URL}/materials/${materialId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

// --- Quizzes ---
export async function generateQuiz({
  material_id,
  number_of_questions = 5,
  difficulty = "medium",
  question_types = ["multiple_choice"],
}) {
  const response = await fetch(`${API_BASE_URL}/quizzes/generate`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({
      material_id,
      number_of_questions,
      difficulty,
      question_types,
    }),
  });
  return handleResponse(response);
}

export async function listQuizzes() {
  const response = await fetch(`${API_BASE_URL}/quizzes`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function getQuiz(quizId) {
  const response = await fetch(`${API_BASE_URL}/quizzes/${quizId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function deleteQuiz(quizId) {
  const response = await fetch(`${API_BASE_URL}/quizzes/${quizId}`, {
    method: "DELETE",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function getQuizQuestions(quizId) {
  const response = await fetch(`${API_BASE_URL}/quizzes/${quizId}/questions`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function startAttempt(quizId) {
  const response = await fetch(`${API_BASE_URL}/quizzes/${quizId}/attempts`, {
    method: "POST",
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

// --- Attempts ---
export async function submitAttempt(attemptId, answers) {
  const response = await fetch(`${API_BASE_URL}/attempts/${attemptId}/submit`, {
    method: "POST",
    headers: getAuthHeaders(),
    body: JSON.stringify({ answers }),
  });
  return handleResponse(response);
}

export async function getAttempt(attemptId) {
  const response = await fetch(`${API_BASE_URL}/attempts/${attemptId}`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

export async function listAttempts() {
  const response = await fetch(`${API_BASE_URL}/attempts`, {
    headers: getAuthHeaders(),
  });
  return handleResponse(response);
}

// --- Summaries ---
export async function getAttemptSummary(attemptId) {
  const response = await fetch(
    `${API_BASE_URL}/attempts/${attemptId}/summary`,
    {
      headers: getAuthHeaders(),
    }
  );
  return handleResponse(response);
}

// --- Analytics ---
export async function listWeaknesses() {
  const response = await fetch(`${API_BASE_URL}/analytics/weaknesses`, {
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
  const response = await fetch(`${API_BASE_URL}/practice/generate`, {
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
