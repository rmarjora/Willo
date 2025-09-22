import { useState, useEffect } from "react";
import { getQuestions, submitAnswer, getQuizStatus, getPlayerMatches } from "../services/api";

const PlayerView = () => {
  const [step, setStep] = useState("menu");
  const [current, setCurrent] = useState(0);
  const [nameInput, setNameInput] = useState("");
  const [playerName, setPlayerName] = useState("");
  const [playerId, setPlayerId] = useState(null);
  const [answers, setAnswers] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [openResponse, setOpenResponse] = useState("");
  const [quizId, setQuizId] = useState(null);
  const [quizIdInput, setQuizIdInput] = useState("");
  const [match, setMatch] = useState(null);

  const handleStart = () => {
    setStep("quiz");
    setCurrent(0);
  };

  const handlePlayAgain = () => {
     setStep("menu");
    setCurrent(0);
    setNameInput("");
    setPlayerName("");
    setPlayerId(null);
    setAnswers([]);       
    setQuestions([]);     
    setQuizId(null);
    setQuizIdInput("");
    setError("");
    setMatch(null);
  };

  const handleNext = async (option) => {
    const newAnswers = [...answers, { questionId: questions[current].id, response: option }];
    setAnswers(newAnswers);
    setOpenResponse("");

    const isFinalQuestion = current + 1 === questions.length;

    if (isFinalQuestion) {
      try {
        const result = await submitAnswer(quizId, playerName, newAnswers);
        console.log("Submit response:", result);
        setPlayerId(result.user_id); // backend returns user_id
      } catch (err) {
        console.error("Failed to submit answers:", err);
      }
      setStep("waiting");
    } else {
      setCurrent(current + 1);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    if (!nameInput.trim()) {
      setError("Please enter your name.");
      return;
    }
    if (!quizIdInput.trim()) {
      setError("Please enter the Quiz ID.");
      return;
    }
    setPlayerName(nameInput.trim());
    setQuizId(quizIdInput.trim());

    setLoading(true);
    try {
      const data = await getQuestions(quizIdInput.trim());

      if (data.active === false) {
        setError("This quiz is not active right now.");
        setLoading(false);
        return;
      }

      const questionsArray = Array.isArray(data.questions) ? data.questions : [];
      const filteredQuestions = questionsArray.filter(q => q.active !== false);

      setQuestions(filteredQuestions);

      if (filteredQuestions.length > 0) {
        handleStart();
      } else {
        setError("No active questions available in this quiz.");
      }
    } catch (err) {
      setError("Failed to load questions. Try again.");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  // Poll quiz status while waiting
  useEffect(() => {
    if (!quizId || step !== "waiting") return;

    const interval = setInterval(async () => {
      try {
        const { active } = await getQuizStatus(quizId);
        if (active === false) setStep("finalResults");
      } catch (err) {
        console.error("Failed to check quiz status:", err);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [quizId, step]);

  // Fetch closest match after quiz ends
 useEffect(() => {
  if (step !== "finalResults" || !quizId || !playerId) return;

  let interval = setInterval(async () => {
    try {
      const data = await getPlayerMatches(quizId, playerId);
      console.log("Fetched match data:", data);

      if (data) {
        setMatch(data);      // set state
        clearInterval(interval); // stop polling once we get data
      }
    } catch (err) {
      console.error("Error fetching matches:", err);
    }
  }, 5000); // poll every 5 seconds

  return () => clearInterval(interval);
}, [step, quizId, playerId]);

  // --- Render ---
  if (step === "menu") return (
    <div>
      <h1 className="text-5xl font-extrabold mb-8">Willo</h1>
      <form onSubmit={handleSubmit} className="flex flex-col items-center w-full max-w-md">
        <input
          type="text"
          placeholder="Enter your name"
          value={nameInput}
          onChange={(e) => setNameInput(e.target.value)}
          className="mb-4 px-6 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full text-lg"
        />
        <input
          type="text"
          placeholder="Quiz ID"
          value={quizIdInput}
          onChange={e => setQuizIdInput(e.target.value)}
          className="mb-4 px-6 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full text-lg"
        />
        <button
          type="submit"
          className="px-6 py-3 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700 w-full text-lg"
        >
          {loading ? "Loading..." : "Start Quiz"}
        </button>
        {error && <p className="mt-4 text-red-500">{error}</p>}
      </form>
    </div>
  );

  if (step === "quiz") {
    if (!questions.length || !questions[current]) {
      return (
        <div className="p-6">
          <h2 className="text-2xl font-bold mb-4">
            No active questions available for this quiz.
          </h2>
          <button onClick={handlePlayAgain} className="px-6 py-3 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700">
            Back to Start
          </button>
        </div>
      );
    }

    const q = questions[current];

    return (
      <div className="p-6">
        <h2 className="text-2xl font-bold mb-4">
          Hello {playerName}, {q.question_text}
        </h2>

        <div className="grid grid-cols-2 gap-4 w-full max-w-lg">
          {q.choices?.length > 0 && q.choices.map((opt, idx) => (
            <button
              key={opt.id || idx}
              onClick={() => handleNext(opt.choice_text || opt)}
              className="p-4 rounded-xl bg-indigo-100 hover:bg-indigo-300"
            >
              {opt.choice_text || opt}
            </button>
          ))}

          {q.allow_open_response && (
            <div className="flex flex-col gap-4 w-full col-span-2 mt-4">
              <input
                type="text"
                placeholder="Type your answer..."
                value={openResponse}
                onChange={(e) => setOpenResponse(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                onClick={() => {
                  if (!openResponse.trim()) return;
                  handleNext(openResponse.trim());
                }}
                className="px-6 py-3 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700"
              >
                Submit Answer
              </button>
            </div>
          )}
        </div>

        <p className="mt-6">
          Question {current + 1} / {questions.length}
        </p>
      </div>
    );
  }

  if (step === "waiting") return (
    <div className="result-screen">
      <p>{playerName}, Waiting for the quiz to be finished</p>
      <p style={{ fontSize: '1.5rem', margin: '1rem 0' }}>Please Wait </p>
    </div>
  );

  if (step === "finalResults") return (
    <div className="result-screen p-6">
      <h2 className="text-2xl font-bold mb-4">Results</h2>
      <p>{playerName}, you have answered {questions.length} questions!</p>

     {match === null ? (
  <p className="mt-4">Calculating your closest match...</p>
) : match.top_matches && match.top_matches.length > 0 ? (
  <div className="mt-4">
    <h3 className="font-semibold mb-2">Your Closest Match:</h3>
    <p className="text-lg font-medium">{match.top_matches[0].name}</p>
  </div>
) : (
  <p className="mt-4"> 😢 Unfortunately, 0 matches found 😢</p>
)}

      <button
        onClick={handlePlayAgain}
        className="mt-6 px-6 py-3 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700"
      >
        Home
      </button>
    </div>
  );

  return null;
};

export default PlayerView;
