import { useState } from "react";
import { Routes, Route } from "react-router-dom";
import PlayerView from "./components/PlayerView";
import AdminView from "./components/Adminview";
import FormManagementView from "./components/FormManagementView";
import './index.css';

const App = () => {
  const [view, setView] = useState("player");
  const [currentFormId, setCurrentFormId] = useState(null);
  const [managedFormId, setManagedFormId] = useState(null);

  return (
    <Routes>
      <Route path="/:id" element={<PlayerView />} />
      <Route path="/" element={
        <div>
          <button
            onClick={() => setView(view === "player" ? "Create" : "player")}
            className="px-4 py-2 m-4 bg-gray-600 text-white rounded hover:bg-gray-700"
          >
            Switch to {view === "player" ? "Create" : "Player"} Panel
          </button>
          
          {managedFormId ? (
            <FormManagementView
              formId={managedFormId}
              onBack={() => setManagedFormId(null)}
            />
          ) : view === "Create" ? (
            <AdminView
              onFormCreated={setCurrentFormId}
              onManageForm={setManagedFormId}
            />
          ) : (
            <PlayerView quizId={currentFormId} />
          )}
        </div>
      } />
      {/* Add other routes as needed */}
    </Routes>
  );
};

export default App;
