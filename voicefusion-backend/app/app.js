import { BrowserRouter, Routes, Route } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import TTS from './pages/TTS';
import STT from './pages/STT';
import Clone from './pages/Clone';
import Translate from './pages/Translate';
import Chat from './pages/Chat';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/tts" element={<TTS />} />
        <Route path="/stt" element={<STT />} />
        <Route path="/clone" element={<Clone />} />
        <Route path="/translate" element={<Translate />} />
        <Route path="/chat" element={<Chat />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
