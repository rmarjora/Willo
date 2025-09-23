import { useState, useEffect } from "react";
import { createForm, endQuiz } from "../services/api";

const baseQuestions = [
  { question_text: "What is your mindset going into the upcoming event?", allow_open_response: false, choices: ["Good", "Excited", "Not sure", "Nervous"] },
  { question_text: "What is your educational background?", allow_open_response: false, choices: ["High school", "Bachelor's", "Master's", "PhD", "Other"] },
  { question_text: "In which language would you like to have the conversation?", allow_open_response: false, choices: ["Finnish", "English", "Other"] },
  { question_text: "Are humans considered as Bees?", allow_open_response: false, choices: ["No", "Yes", "Other"] },
];

const AdminView = ({ onFormCreated, onManageForm }) => {
  const [formData, setFormData] = useState({ title: "Test Form", questions: [...baseQuestions] });
  const [message, setMessage] = useState("");
  const [formId, setFormId] = useState(null);
  const [showcaseId, setShowcaseId] = useState(null); 


 
  const [manageFormIdInput, setManageFormIdInput] = useState("");

  // --- Handlers ---
  const handleQuestionChange = (index, value) => {
    const newQuestions = [...formData.questions];
    newQuestions[index].question_text = value;
    setFormData({ ...formData, questions: newQuestions });
  };

  const handleManageForm = (e) => {
  e.preventDefault();
  if (!manageFormIdInput.trim()) {
    setMessage("Please enter a Form ID to manage.");
    return;
  }
  onManageForm(manageFormIdInput.trim());
};

  const toggleAllowOpenResponse = (index) => {
    const newQuestions = [...formData.questions];
    newQuestions[index].allow_open_response = !newQuestions[index].allow_open_response;
    setFormData({ ...formData, questions: newQuestions });
  };

  const handleChoiceChange = (qIndex, cIndex, value) => {
    const newQuestions = [...formData.questions];
    newQuestions[qIndex].choices[cIndex] = value;
    setFormData({ ...formData, questions: newQuestions });
  };

  const addQuestion = () => {
    setFormData({ ...formData, questions: [...formData.questions, { question_text: "", allow_open_response: false, choices: [] }] });
  };

  const deleteQuestion = (index) => {
    if (index < baseQuestions.length) return;
    const newQuestions = formData.questions.filter((_, i) => i !== index);
    setFormData({ ...formData, questions: newQuestions });
  };

  // --- Submit Form ---
  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const data = await createForm(formData);
      if (data.id) {
        setMessage("Form created successfully!");
        setFormId(data.id);
        setShowcaseId(data.id); // Show the ID in a separate box
        onFormCreated(data.id);
      } else {
        setMessage("Failed to create form");
      }
    } catch (err) {
      setMessage("Network error or invalid JSON");
    }
  };

  // --- Message timeout ---
  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(""), 5000);
    return () => clearTimeout(timer);
  }, [message]);

 return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Message Box (only for errors/success, not for ID) */}
      {message && (
        <div className={`mb-4 p-3 rounded flex items-center gap-2 font-medium ${
          message.toLowerCase().includes("error") || message.toLowerCase().includes("fail")
            ? "bg-red-100 text-red-800 border border-red-300"
            : "bg-green-100 text-green-800 border-green-300"
        }`}>
          {message.toLowerCase().includes("error") || message.toLowerCase().includes("fail")
            ? "❌"
            : "✅"}
          <span>{message}</span>
        </div>
      )}
      <div className="flex flex-row gap-8">
        {/* Question Creation Panel (left side) */}
        <div className="flex-1">
          <h1 className="text-2xl font-bold mb-4">Question Creation Panel</h1>
          <h2 className="text-lg font-semibold">Title</h2>
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            <input 
            type="text" 
            placeholder="Title" 
            value={formData.title} 
            onChange={(e) => setFormData({ ...formData, title: e.target.value })} 
            className="border p-2 rounded" />

            <h2 className="text-lg font-semibold">Questions</h2>
            {formData.questions.map((q, index) => (
              <div key={index} className="flex flex-col gap-2 border-b pb-2">
                <input type="text" placeholder={`Question ${index + 1}`} value={q.question_text} onChange={(e) => handleQuestionChange(index, e.target.value)} className="border p-2 rounded" />

                {q.choices.length > 0 && (
                  <div className="ml-4">
                    <h3 className="font-medium">Choices:</h3>
                    {q.choices.map((choice, cIndex) => (
                      <input key={cIndex} type="text" value={choice} onChange={(e) => handleChoiceChange(index, cIndex, e.target.value)} className="border p-1 rounded mb-1 w-full" />
                    ))}
                  </div>
                )}

                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={q.allow_open_response} onChange={() => toggleAllowOpenResponse(index)} /> Allow Open Response
                </label>

                {index >= baseQuestions.length && (
                  <button type="button" onClick={() => deleteQuestion(index)} className="text-red-600 text-sm self-start">
                    Delete Question
                  </button>
                )}
              </div>
            ))}

            <button type="button" onClick={addQuestion} className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700">
              + Add
            </button>

            <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">
              Submit
            </button>
          </form>

          {/* Form ID Showcase Box */}
          {showcaseId && (
            <div className="mb-4 p-3 rounded bg-yellow-100 text-yellow-900 border border-yellow-300 font-mono text-lg flex items-center gap-2">
              <span>Form ID:</span>
              <span className="font-bold">{showcaseId}</span>
            </div>
          )}
        </div>

        {/* Manage Form Section (right side) */}
        <div className="w-80 flex-shrink-0">
          <form onSubmit={handleManageForm} className="mb-6 flex flex-col gap-2">
            <label className="font-semibold">Manage Existing Form</label>
            <input
              type="text"
              placeholder="Id here"
              value={manageFormIdInput}
              onChange={e => setManageFormIdInput(e.target.value)}
              className="border p-2 rounded"
            />
            <button
              type="submit"
              className="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700"
            >
              Manage Form
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default AdminView;