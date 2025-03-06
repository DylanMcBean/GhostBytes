import { escapeHtml, scrollToBottom } from "./utils.js";

const MESSAGES_API_URL = "/messages";
const RECENT_MESSAGES_API_URL = "/messages/recent";

export class MessageHandler {
  constructor(messagesContainer) {
    this.messagesContainer = messagesContainer;
    this.lastMessageId = null;
  }

  /**
   * Creates or groups a message element.
   * @param {object} messageData
   * @returns {HTMLElement|null} The new message element or null if grouped.
   */
  createMessageElement(messageData) {
    const lastMessageElement = this.messagesContainer.lastElementChild;
    let shouldGroup = false;

    if (lastMessageElement) {
      const lastTimestamp = new Date(
        lastMessageElement.querySelector(".message-timestamp").dataset.timestamp
      );
      const newTimestamp = new Date(messageData.timestamp);
      const lastUsername =
        lastMessageElement.querySelector(".username").textContent;

      shouldGroup =
        messageData.username === lastUsername &&
        newTimestamp - lastTimestamp < 60000;
    }

    if (shouldGroup) {
      const contentDiv = lastMessageElement.querySelector(".message-content");
      contentDiv.innerHTML += `<br>${escapeHtml(messageData.content)}`;

      const timestampElement =
        lastMessageElement.querySelector(".message-timestamp");
      timestampElement.textContent = new Date(
        messageData.timestamp
      ).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
      timestampElement.dataset.timestamp = messageData.timestamp;

      lastMessageElement.dataset.messageId = messageData.id;
      this.lastMessageId = messageData.id;
      return null;
    } else {
      const messageDiv = document.createElement("div");
      messageDiv.className = `message ${
        messageData.isUser ? "user-message" : ""
      }`;
      messageDiv.dataset.messageId = messageData.id;

      messageDiv.innerHTML = `
        <div class="message-header">
          <span class="username">${escapeHtml(messageData.username)}</span>
          <span class="message-timestamp" data-timestamp="${
            messageData.timestamp
          }">
            ${new Date(messageData.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
        <div class="message-content">${escapeHtml(messageData.content)}</div>
      `;
      return messageDiv;
    }
  }

  /**
   * Handles a new message received from the server.
   * @param {object} messageData
   * @returns {boolean} True if a new element was created.
   */
  handleNewMessage(messageData) {
    const existingMessage = document.querySelector(
      `[data-message-id="${messageData.id}"]`
    );
    if (!existingMessage) {
      const messageElement = this.createMessageElement(messageData);
      if (messageElement) {
        this.messagesContainer.appendChild(messageElement);
      }
      this.lastMessageId = messageData.id;
      return true;
    }
    this.lastMessageId = messageData.id;
    return false;
  }

  /**
   * Polls the server for new messages.
   */
  async checkForNewMessages() {
    try {
      const params = new URLSearchParams();
      if (this.lastMessageId) params.append("after", this.lastMessageId);

      const response = await fetch(
        `${RECENT_MESSAGES_API_URL}?${params.toString()}`
      );
      if (!response.ok) return;

      const messages = await response.json();
      messages.forEach((message) => {
        if (this.handleNewMessage(message)) {
          const { scrollTop, scrollHeight, clientHeight } =
            this.messagesContainer;
          if (scrollHeight - (scrollTop + clientHeight) < 100) {
            scrollToBottom(this.messagesContainer);
          }
        }
      });
    } catch (error) {
      console.error("Error checking messages:", error);
    }
  }

  /**
   * Sends a new message to the server.
   * @param {string} content
   */
  async sendMessage(content) {
    if (!content.trim()) return;

    try {
      // Check for new messages before sending
      await this.checkForNewMessages();

      const csrfToken = document.querySelector(
        'meta[name="csrf-token"]'
      ).content;
      const response = await fetch(MESSAGES_API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrfToken,
        },
        body: JSON.stringify({ content: content.trim() }),
      });

      if (response.ok) {
        const messageData = await response.json();
        this.handleNewMessage(messageData);
        return messageData;
      }
    } catch (error) {
      console.error("Message send error:", error);
    }
  }
}
