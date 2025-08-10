import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function ChatBubble({ role, message }) {
    return (
        <div
            style={{
                display: "flex",
                justifyContent: role === "user" ? "flex-end" : "flex-start",
            }}
        >
            <div
                style={{
                    background: role === "user" ? "#DCF8C6" : "#FFF",
                    borderRadius: "8px",
                    padding: "8px 12px",
                    margin: "6px 0",
                    maxWidth: "70%",
                    width: "fit-content",
                    wordBreak: "break-word",
                }}
            >
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message || ""}
                </ReactMarkdown>
            </div>
        </div>
    );
}

export default ChatBubble;
