// src/components/ChatInput.jsx
import { useState } from "react";

export default function ChatInput({ onSend }) {
    const [text, setText] = useState("");

    const handleSend = () => {
        if (!text.trim()) return;
        onSend(text);
        setText("");
    };

    return (
        <div className="chat-input">
            <input
                type="text"
                value={text}
                placeholder="Tulis prompt..."
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSend()}
            />
            <button onClick={handleSend}>Kirim</button>
        </div>
    );
}
