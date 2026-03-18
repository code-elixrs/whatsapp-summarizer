import { useState } from "react";
import type { ChatMessage } from "../../types/media";
import styles from "./ChatBubbleView.module.css";

interface ChatBubbleViewProps {
  messages: ChatMessage[];
  onUpdateMessage: (messageId: string, field: string, value: string | boolean) => void;
}

export function ChatBubbleView({ messages, onUpdateMessage }: ChatBubbleViewProps) {
  return (
    <div className={styles.container}>
      {messages.map((msg) => (
        <ChatBubble
          key={msg.id}
          message={msg}
          onUpdate={onUpdateMessage}
        />
      ))}
    </div>
  );
}

interface ChatBubbleProps {
  message: ChatMessage;
  onUpdate: (messageId: string, field: string, value: string | boolean) => void;
}

function ChatBubble({ message, onUpdate }: ChatBubbleProps) {
  const [editing, setEditing] = useState(false);
  const [editText, setEditText] = useState(message.message);
  const [editSender, setEditSender] = useState(message.sender || "");

  function handleSave() {
    if (editText !== message.message) {
      onUpdate(message.id, "message", editText);
    }
    if (editSender !== (message.sender || "")) {
      onUpdate(message.id, "sender", editSender);
    }
    setEditing(false);
  }

  function handleCancel() {
    setEditText(message.message);
    setEditSender(message.sender || "");
    setEditing(false);
  }

  const formattedTime = message.message_timestamp
    ? new Date(message.message_timestamp).toLocaleTimeString("en-IN", {
        hour: "2-digit",
        minute: "2-digit",
      })
    : null;

  return (
    <div className={`${styles.bubbleRow} ${message.is_sent ? styles.sent : styles.received}`}>
      <div className={`${styles.bubble} ${message.is_sent ? styles.bubbleSent : styles.bubbleReceived}`}>
        {/* Sender name (for received messages or group chats) */}
        {!message.is_sent && message.sender && !editing && (
          <div className={styles.sender}>{message.sender}</div>
        )}

        {editing ? (
          <div className={styles.editForm}>
            <input
              type="text"
              className={styles.editSenderInput}
              value={editSender}
              onChange={(e) => setEditSender(e.target.value)}
              placeholder="Sender name"
            />
            <textarea
              className={styles.editTextarea}
              value={editText}
              onChange={(e) => setEditText(e.target.value)}
              rows={3}
              autoFocus
            />
            <div className={styles.editActions}>
              <button className={styles.saveBtn} onClick={handleSave}>Save</button>
              <button className={styles.cancelBtn} onClick={handleCancel}>Cancel</button>
            </div>
          </div>
        ) : (
          <>
            <div className={styles.messageText}>{message.message}</div>
            <div className={styles.meta}>
              {formattedTime && <span className={styles.timestamp}>{formattedTime}</span>}
              <button
                className={styles.editBtn}
                onClick={() => setEditing(true)}
                title="Edit message (correct OCR errors)"
              >
                edit
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
