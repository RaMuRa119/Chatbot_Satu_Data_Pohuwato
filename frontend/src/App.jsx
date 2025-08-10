// src/App.jsx
import { useState } from "react";
import axios from "axios";
import "./App.css";
import ChatBubble from "./components/ChatBubble";
import DataTable from "./components/DataTable";
import ChatInput from "./components/ChatInput";

function App() {
    const [messages, setMessages] = useState([]);

    const handleSend = async (prompt) => {
        setMessages((prev) => [...prev, { role: "user", text: prompt }]);

        try {
            const res = await axios.post("http://localhost:5000/chat_submit", {
                prompt,
                threshold: 0.5,
            });

            setMessages((prev) => [
                ...prev,
                {
                    role: "model",
                    text: res.data.response,
                    ragData:
                        res.data.source === "retrieval_augmented"
                            ? res.data.search_result
                            : null,
                },
            ]);
        } catch {
            setMessages((prev) => [
                ...prev,
                { role: "model", text: "Gagal menghubungi server." },
            ]);
        }
    };

    return (
        <div className="app">
            <div className="chat-container">
                <div className="chat-messages">
                    {messages.map((msg, i) => (
                        <div key={i}>
                            {msg.role === "model" && msg.ragData && (
                                <DataTable data={msg.ragData} />
                            )}
                            <ChatBubble role={msg.role} message={msg.text} />
                        </div>
                    ))}
                </div>
            </div>
            <ChatInput onSend={handleSend} />
        </div>
    );
}

export default App;
