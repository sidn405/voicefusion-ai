import React from "react";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Chat from "./pages/Chat";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Chat />} />
        {/* later you'll add: <Route path="/tts" element={<TTS />} /> etc. */}
      </Routes>
    </BrowserRouter>
  );
}

export default App;
