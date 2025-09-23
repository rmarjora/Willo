import { useState, useEffect } from "react";
import { getQuestions, submitAnswer, getQuizStatus, getPlayerMatches } from "../services/api";
import { useParams } from "react-router-dom";

const PlayerView = () => {
  const { id } = useParams();
  const quiz_id = id;
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
  const [matchLoading, setMatchLoading] = useState(true);
  const [questionsAnswered, setQuestionsAnswered] = useState(
    Number(window.localStorage.getItem("questions_answered")) || 0
  );
  const [quizTitle, setQuizTitle] = useState(""); // <-- Add this

  const handleStart = () => {
    setStep("quiz");
    setCurrent(0);
    setPlayerId(null);
    // window.localStorage.clear();
  };

  const handlePlayAgain = () => {
    setStep("menu");
    setCurrent(0);
    setNameInput("");
    setPlayerName("");
    setAnswers([]);
    setQuestions([]);
    setQuizId(window.localStorage.getItem("quiz_id"));
    setQuizIdInput(quiz_id || "");
    setError("");
    setMatch(null);
    setQuestionsAnswered(Number(window.localStorage.getItem("questions_answered")) || 0);
    setQuizTitle(""); // <-- Reset title
  };

  const handleCheckresults = () => {
    setStep("finalResults");
  };

  useEffect(() => {
    const storedId = window.localStorage.getItem("user_id");
    const storedQuizId = window.localStorage.getItem("quiz_id");
    const storeUserName = window.localStorage.getItem("user_name");
    const storedQuestionsAnswered = window.localStorage.getItem("questions_answered");

    if (storeUserName) {
      setPlayerName(storeUserName);
      setNameInput(storeUserName);
    }
    if (storedQuizId) {
      setQuizId(storedQuizId);
    }
    if (storedId) {
      setPlayerId(storedId);
    }
    if (storedQuestionsAnswered) {
      setQuestionsAnswered(Number(storedQuestionsAnswered));
    }
    if (quiz_id) {
      setQuizIdInput(quiz_id);
    }
  }, [quiz_id]);

  const handleNext = async (option) => {
    const newAnswers = [...answers, { questionId: questions[current].id, response: option }];
    setAnswers(newAnswers);
    setOpenResponse("");

    const isFinalQuestion = current + 1 === questions.length;

    if (isFinalQuestion) {
      try {
        const result = await submitAnswer(quizId, playerName, newAnswers);
        setPlayerId(result.user_id);
        window.localStorage.setItem("user_id", result.user_id);
        window.localStorage.setItem("questions_answered", newAnswers.length);
        setQuestionsAnswered(newAnswers.length);
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
    window.localStorage.setItem("quiz_id", quizIdInput.trim());
    window.localStorage.setItem("user_name", nameInput.trim());
    console.log("data stored to localStorage:", {
      quiz_id: quizIdInput.trim(),
      user_name: nameInput.trim(),
      user_id: playerId
    });

    setLoading(true);
    try {
      const data = await getQuestions(quizIdInput.trim());
      console.log(data); // <-- Move this inside the try block

      if (data.active === false) {
        setError("This quiz is not active right now.");
        setLoading(false);
        return;
      }

      setQuizTitle(data.title || "");

      const questionsArray = Array.isArray(data.questions) ? data.questions : [];
      const filteredQuestions = questionsArray.filter(q => q.active !== false);

      setQuestions(filteredQuestions);

      if (filteredQuestions.length > 0) {
        setStep("showTitle");
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

  const formatScore = (score) => {
    if (typeof score !== "number") return "";
    return `${Math.round(score * 100)}%`;
  };

  // Poll quiz status while waiting
  useEffect(() => {
    if (!quizId || step !== "waiting") return;

    // First check instantly
    const checkStatus = async () => {
      try {
        const { active } = await getQuizStatus(quizId);
        if (active === false) setStep("finalResults");
      } catch (err) {
        console.error("Failed to check quiz status:", err);
      }
    };

    checkStatus(); // Run immediately

    // Then poll every 15 seconds
    const interval = setInterval(checkStatus, 15000);

    return () => clearInterval(interval);
  }, [quizId, step]);

  // Fetch closest match after quiz ends
  useEffect(() => {
    if (step !== "finalResults" || !quizId || !playerId) return;

    setMatchLoading(true);

    // First check instantly
    const fetchMatches = async () => {
      try {
        const data = await getPlayerMatches(quizId, playerId);
        console.log("Fetched match data:", data);

        if (data && data.top_matches && data.top_matches.length > 0) {
          setMatch(data);
          setMatchLoading(false);
          clearInterval(interval); // stop polling once we get data
        } else if (data && data.top_matches && data.top_matches.length === 0) {
          setMatch(data);
          setMatchLoading(false);
          clearInterval(interval); // stop polling if server says 0 matches
        }
        // else: keep polling if data is not valid
      } catch (err) {
        console.error("Error fetching matches:", err);
        // Optionally set an error state here
      }
    };

    fetchMatches(); // Run immediately

    // Then poll every 15 seconds
    const interval = setInterval(fetchMatches, 15000);

    return () => clearInterval(interval);
  }, [step, quizId, playerId]);

  // --- Render ---
  if (step === "menu") return (
    <div className="min-h-screen flex items-center justify-center bg-indigo-100">
      <div className="bg-white rounded-2xl shadow-xl px-10 py-12 flex flex-col items-center">
        <h1 className="text-5xl font-extrabold mb-8">Willo</h1>
        <form onSubmit={handleSubmit} className="flex flex-col items-center w-full max-w-md">
          <input
            type="text"
            placeholder="Enter your name"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            className="mb-4 px-6 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full text-lg"
          />
          { !quiz_id && (
          <input
            type="text"
            placeholder="Quiz ID"
            value={quizIdInput}
            onChange={e => setQuizIdInput(e.target.value)}
            className="mb-4 px-6 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 w-full text-lg"
          />
          )}
          <button
            type="submit"
            className="px-6 py-3 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700 w-full text-lg"
          >
            {loading ? "Loading..." : "Start Quiz"}
          </button>
          {error && <p className="mt-4 text-red-500">{error}</p>}
        </form>
        {playerId !== null && quizId !== null && (
          <button
            onClick={handleCheckresults}
            className="mt-6 px-6 py-3 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700"
          >
            Check Results
          </button>
        )}
      </div>
    </div>
  );

  if (step === "showTitle") return (
    <div className="min-h-screen flex items-center justify-center bg-indigo-100">
      <div className="bg-white rounded-2xl shadow-xl px-10 py-12 flex flex-col items-center">
        <h1 className="text-4xl font-extrabold mb-8 text-indigo-700">{quizTitle}</h1>
        <button
          onClick={handleStart}
          className="px-8 py-4 bg-indigo-700 text-white rounded-2xl hover:bg-indigo-800 text-lg font-semibold"
        >
          Start Quiz
        </button>
      </div>
    </div>
  );

  if (step === "quiz") {
    if (!questions.length || !questions[current]) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-indigo-100">
          <div className="bg-white rounded-2xl shadow-xl px-10 py-12 flex flex-col items-center">
            <h2 className="text-2xl font-bold mb-4">
              No active questions available for this quiz.
            </h2>
            <button onClick={handlePlayAgain} className="px-8 py-4 bg-indigo-700 text-white rounded-2xl hover:bg-indigo-800 text-lg font-semibold">
              Back to Start
            </button>
          </div>
        </div>
      );
    }

    const q = questions[current];

    return (
      <div className="min-h-screen flex items-center justify-center bg-indigo-100">
        <div className="bg-white rounded-2xl shadow-xl px-10 py-12 flex flex-col items-center w-full max-w-lg">
          {quizTitle && (
            <h1 className="text-2xl font-bold mb-4 text-indigo-700">{quizTitle}</h1>
          )}
          {current === 0 ? (
  <h2 className="text-xl font-semibold mb-6 text-gray-800 text-center">
    Hello {playerName},<br />{q.question_text}
  </h2>
) : (
  <h2 className="text-xl font-semibold mb-6 text-gray-800 text-center">
    {q.question_text}
  </h2>
)}

          <div className="grid grid-cols-2 gap-4 w-full mb-6">
            {q.choices?.length > 0 && q.choices.map((opt, idx) => (
              <button
                key={opt.id || idx}
                onClick={() => handleNext(opt.choice_text || opt)}
                className="w-full py-3 rounded-xl bg-indigo-100 hover:bg-indigo-300 text-indigo-800 font-medium transition"
              >
                {opt.choice_text || opt}
              </button>
            ))}
          </div>

          {q.allow_open_response && (
            <div className="flex flex-col gap-4 w-full mb-6">
              <input
                type="text"
                placeholder="Type your answer..."
                value={openResponse}
                onChange={(e) => setOpenResponse(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button
                onClick={() => handleNext(openResponse)}
                className="px-8 py-3 bg-indigo-700 text-white rounded-2xl hover:bg-indigo-800 text-lg font-semibold"
              >
                Submit Answer
              </button>
            </div>
          )}

          <p className="mt-6 text-gray-500">
            Question {current + 1} / {questions.length}
          </p>
        </div>
      </div>
    );
  }

  if (step === "waiting") return (
    <div className="min-h-screen flex items-center justify-center bg-indigo-100">
      <div className="bg-white rounded-2xl shadow-xl px-10 py-12 flex flex-col items-center">
        <p>{playerName}, Waiting for the quiz to be finished</p>
        <p style={{ fontSize: '1.5rem', margin: '1rem 0' }}>Please Wait </p>
        <button
          onClick={handlePlayAgain}
          className="mt-6 px-6 py-3 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700"
        >
          Home
        </button>
      </div>
    </div>
  );

  if (step === "finalResults") return (
    <div className="min-h-screen flex items-center justify-center bg-indigo-100">
      <div className="bg-white rounded-2xl shadow-xl px-10 py-12 flex flex-col items-center">
        <h2 className="text-2xl font-bold mb-4">Results</h2>
        <p>
          {(playerName || window.localStorage.getItem("user_name"))}, you have answered{" "}
          {(questions.length || questionsAnswered || window.localStorage.getItem("questions_answered"))} questions!
        </p>

        {matchLoading ? (
          <p className="mt-4">Waiting for admin to close the quiz...</p>
        ) : match && match.top_matches && match.top_matches.length > 0 ? (
          <div className="mt-4 bg-indigo-50 rounded-xl shadow-md p-6 flex flex-col items-center">
            <h3 className="font-semibold mb-4 text-indigo-700 text-xl">Your Closest Match:</h3>
            <p className="text-2xl font-bold text-indigo-900 mb-2">{match.top_matches[0].name}</p>
            <p className="text-lg text-indigo-600 font-semibold mb-2">
              {formatScore(match.top_matches[0].score)} Match
            </p>
            <p className="text-md text-gray-700 mb-2">
              Most similar answer: <span className="font-medium">{match.top_matches[0].most_similar_answer}</span>
            </p>
          </div>
        ) : match && match.top_matches && match.top_matches.length === 0 ? (
          <p className="mt-4"> 😢 Unfortunately, 0 matches found 😢</p>
        ) : null}

        <button
          onClick={handlePlayAgain}
          className="mt-6 px-6 py-3 bg-indigo-600 text-white rounded-2xl hover:bg-indigo-700"
        >
          Home
        </button>
      </div>
    </div>
  );

  return null;
};

export default PlayerView;
