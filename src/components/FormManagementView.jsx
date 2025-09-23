// ./components/FormManagementView.jsx
import { useState, useEffect } from "react";
import { endQuiz, getForm } from "../services/api";

const FormManagementView = ({ formId, onBack }) => {
  const [isQuizEnded, setIsQuizEnded] = useState(false);
  const [message, setMessage] = useState("");
  const [respondedUsers, setRespondedUsers] = useState([]);

  useEffect(() => {
    const loadForm = async () => {
      if (!formId) return;

      try {
        const data = await getForm(formId);
        setRespondedUsers(data.responded_users || []);
      } catch (err) {
        setMessage("Failed to load form");
      }
    };

    loadForm();
  }, [formId]);


  const endQuizHandler = async () => {
    if (!formId) return;
    try {
      const data = await endQuiz(formId);
      setIsQuizEnded(true);
      setMessage(data?.message || "Form ended successfully!");
    } catch (err) {
        if(err.message.includes("CONFLICT")) {
            setIsQuizEnded(true);
            setMessage("Quiz was already ended")
        } else {
      setMessage(`Error ending form: ${err.message}`);
    }
   }
 };

  return (
    <div className="p-6 max-w-lg mx-auto">
      <h2 className="text-2xl font-bold mb-4">Managing Form ID: {formId}</h2>

      <button
        disabled={isQuizEnded || !formId}
        onClick={endQuizHandler}
        className={`mt-6 px-4 py-2 rounded ${
          isQuizEnded || !formId
            ? "bg-gray-400 cursor-not-allowed text-white"
            : "bg-red-600 text-white hover:bg-red-700"
        }`}
      >
        End Form
      </button>

      <button
        onClick={onBack}
        className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700 mt-4"
      >
        Back
      </button>

      <h3 className="text-lg font-semibold mt-6">Responded Users</h3>
      <ul className="list-disc ml-6">
        {respondedUsers.map((user, index) => (
          <li key={index}>{user.name}</li>
        ))}
      </ul>

      {message && (
        <p className="mt-4 text-center font-medium">
          {isQuizEnded ? "✅" : "❌"} {message}
        </p>
      )}
    </div>
  );
};

export default FormManagementView;
