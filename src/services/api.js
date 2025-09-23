const API_URL = "http://192.168.1.15:5000";



export const submitAnswer = async (formId, name, newAnswers) => {
  try {
    const responses = {};
    newAnswers.forEach(({ questionId, response }) => {
      responses[questionId] = response;
    });

    const payload = {
      name,
      responses,
    };

    const res = await fetch(`${API_URL}/forms/${formId}/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) throw new Error("Submit Failed");

    return await res.json();
  } catch (err) {
    console.error("Error submitting answer:", err);
    throw err;
  }
};


// Get quiz status
export const getQuizStatus = async (quizId) => {
  try {
    const res = await fetch(`${API_URL}/forms/${quizId}/questions`);
    if (!res.ok) throw new Error("Failed to fetch quiz status");
    const data = await res.json();
    return { active: data.active };
  } catch (err) {
    console.error("Error fetching quiz status:", err);
    throw err;
  }
};

// Get questions for a specific form
export const getQuestions = async (formId) => {
  try {
    const res = await fetch(`${API_URL}/forms/${formId}/questions`);
    if (!res.ok) throw new Error("Failed to fetch questions");
    const data = await res.json();
    if (data && Array.isArray(data.questions)) {
      return { active: data.active, questions: data.questions };
    }
    if (Array.isArray(data)) {
      return { active: true, questions: data }; 
    }
    return { active: true, questions: [] };
  } catch (err) {
    console.error("Error fetching questions:", err);
    throw err;
  }
};

// End a quiz for a specific form
export const endQuiz = async (formId) => {
  try {
    const res = await fetch(`${API_URL}/forms/${formId}/close`, { method: "POST" });
    let data;
    try { data = await res.json(); } catch { data = null; }

    if (!res.ok) {
      const errorMessage = data?.message || res.statusText || "Failed to end quiz";
      throw new Error(errorMessage);
    }

    return data;
  } catch (err) {
    console.error("Error ending quiz:", err);
    throw err;
  }
};

export const getForm = async (formId) => {
  try {
    const res = await fetch(`${API_URL}/forms/${formId}`);
    if (!res.ok) throw new Error("Failed to fetch form");
    return await res.json();
  } catch (err) {
    console.error("Error fetching form:", err);
    throw err;
  }
};

export const createForm = async (formData) => {
  try {
    const res = await fetch(`${API_URL}/forms`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(formData),
    });

    if (!res.ok) {
      const errData = await res.json().catch(() => ({}));
      throw new Error(errData.message || "Failed to create form");
    }

    return await res.json();
  } catch (err) {
    console.error("Error creating form:", err);
    throw err;
  }
};

// Get results from your current form

  export const getPlayerMatches = async (quizId, playerId) => {
    try{
      const res = await fetch(`${API_URL}/forms/${quizId}/matches/${playerId}`);
      if (!res.ok) throw new Error("Failed to fetch matches");
      return await res.json();
    }catch (err){
      console.error("Error fetching matches:", err);
      return[];
    }
  }
