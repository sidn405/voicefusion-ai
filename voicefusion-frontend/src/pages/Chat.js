import React, { useState } from "react";
import axios from "axios";



const Chat = () => {
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Hi! I'm VoiceFusion AI. Ask me anything!" }
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

async function handleTranslateAndSpeak(inputText, sourceLang = "auto", targetLang = "en") {
  const response = await fetch('/api/translate-and-speak', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text: inputText, source_lang: sourceLang, target_lang: targetLang })
  });
  const data = await response.json();
  console.log("🎙️ Translated:", data.translated_text);
  const audio = new Audio(data.audio_url);
  audio.play();
}

  // 👇 Updated: Use custom TTS API instead of browser speech synthesis
  const playClonedVoice = async (text) => {
    try {
      const res = await axios.post("http://localhost:8000/api/tts", { text });
      const audio = new Audio(res.data.audio_url);
      audio.play();
    } catch (err) {
      console.error("TTS failed:", err);
      // Fallback to browser speech synthesis if TTS fails
  
    const synth = window.speechSynthesis;
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = "en-US";
    synth.speak(utter);
    }
  };

  const sendMessage = async () => {
  if (!input.trim()) return;

  const userMessage = { role: "user", content: input };
  const updatedMessages = [...messages, userMessage];
  setMessages(updatedMessages);
  setLoading(true);

  const payload = {
    messages: updatedMessages.map(m => ({
      role: m.role,
      content: m.content
    })),
    instructions: "You are VoiceFusion AI, a helpful voice assistant."
  };

  console.log("📤 Sending to backend:", payload);

  try {
    const res = await axios.post("http://localhost:8000/api/chat", payload);
    console.log("🛬 Response from backend:", res);

    const assistantMessage = { role: "assistant", content: res.data.reply };
    setMessages([...updatedMessages, assistantMessage]);

    // 👇 Updated: Use custom TTS with await
    await playClonedVoice(res.data.reply);

    setInput("");
  } catch (err) {
    console.error("🔴 AXIOS ERROR:", err);
    if (err.response) {
      console.error("🔴 Server Response:", err.response.data);
    }
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "Oops! Something went wrong." }
    ]);
  } finally {
    setLoading(false);
  }
};


  return (
    <div style={{ maxWidth: 700, margin: "auto", padding: 20 }}>
      <h2>💬 VoiceFusion AI Chat</h2>
      <div style={{ border: "1px solid #ccc", padding: 10, height: 400, overflowY: "auto", marginBottom: 10 }}>
        {messages.map((msg, idx) => (
          <div key={idx} style={{ textAlign: msg.role === "user" ? "right" : "left" }}>
            <p><strong>{msg.role === "user" ? "You" : "AI"}:</strong> {msg.content}</p>
          </div>
        ))}
      </div>
      <div style={{ display: "flex" }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your message..."
          style={{ flex: 1, padding: 10 }}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <button onClick={sendMessage} disabled={loading} style={{ padding: "10px 20px" }}>
          {loading ? "..." : "Send"}
        </button>
      </div>
    </div>
  );
};

export default Chat;
