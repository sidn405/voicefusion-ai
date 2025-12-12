import { useState } from "react";
import axios from "axios";

export default function TranslationForm({ onTranslated }) {
  const [text, setText] = useState("");
  const [translated, setTranslated] = useState("");
  const [srcLang, setSrcLang] = useState("en");
  const [tgtLang, setTgtLang] = useState("es");

  const handleTranslate = async () => {
    const res = await axios.post("/translate", {
      text,
      source_lang: srcLang,
      target_lang: tgtLang,
    });
    setTranslated(res.data.translated_text);
    onTranslated(res.data.translated_text); // pass to TTS
  };

  return (
    <div className="p-4 bg-gray-900 rounded-xl shadow-md">
      <textarea
        className="w-full p-2 rounded bg-black text-white"
        rows="3"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Enter text to translate"
      />
      <div className="flex gap-4 mt-2">
        <select value={srcLang} onChange={e => setSrcLang(e.target.value)} className="p-2 rounded bg-gray-800 text-white">
          <option value="en">English</option>
          <option value="fr">French</option>
          <option value="de">German</option>
          <option value="es">Spanish</option>
        </select>
        <select value={tgtLang} onChange={e => setTgtLang(e.target.value)} className="p-2 rounded bg-gray-800 text-white">
          <option value="es">Spanish</option>
          <option value="fr">French</option>
          <option value="de">German</option>
          <option value="en">English</option>
        </select>
        <button onClick={handleTranslate} className="bg-blue-600 px-4 py-2 rounded hover:bg-blue-700 text-white">
          Translate
        </button>
      </div>
      {translated && (
        <div className="mt-4 text-green-300">
          <strong>Translated:</strong> {translated}
        </div>
      )}
    </div>
  );
}
