import { escapeHtml, scrollToBottom } from "./utils.js";

const MESSAGES_API_URL = "/messages";
const RECENT_MESSAGES_API_URL = "/messages/recent";

export class MessageHandler {
  constructor(messagesContainer) {
    this.messagesContainer = messagesContainer;
    this.lastMessageId = null; // Tracks the last message ID for polling
    this.isChecking = false; // Prevents concurrent polling
    this.replyMessageId = null; // Tracks the message being replied to

    // Bind event listeners
    this.messagesContainer.addEventListener("click", this.handleMessageClick.bind(this));
    document.getElementById("cancel-reply-btn").addEventListener("click", this.cancelReply.bind(this));
  }

  /**
   * Creates a new message element.
   * @param {object} messageData - The message data (id, username, content, timestamp).
   * @returns {HTMLElement} - The new message element.
   */
  createMessageElement(messageData) {
    const messageContainer = document.createElement("div");
    messageContainer.className = `message-container`;
    messageContainer.dataset.messageId = messageData.id;

    messageContainer.innerHTML = `
        <span class="message-timestamp" data-timestamp="${messageData.timestamp}">
            ${new Date(messageData.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit",})}
        </span>
        <div class="message-bubble">
            <span class="message-username">${escapeHtml(messageData.username)}</span>
            <span class="message-content">${escapeHtml(messageData.content)}</span>
        </div>
    `;

    if (messageData.parent_message_id) {
        const replyContent = document.createElement("div");
        replyContent.className = "message-reply";
        replyContent.innerHTML = `
            <div class="reply-content">
                <span class="message-username">${escapeHtml(messageData.parent.username)}</span>
                <span class="message-content">${escapeHtml(messageData.parent.content)}</span>
            </div>
        ` + messageContainer.outerHTML;
        return replyContent;
    }

    return messageContainer;
}

  /**
   * Handles a new message received from the server.
   * @param {object} messageData - The message data.
   * @returns {boolean} - True if a new element was created.
   */
  handleNewMessage(messageData) {
    const existingMessage = document.querySelector(`[data-message-id="${messageData.id}"]`);
    if (!existingMessage) {
        const messageElement = this.createMessageElement(messageData);
        this.messagesContainer.appendChild(messageElement);
        this.lastMessageId = messageData.id;
        return true;
    }
    return false;
}

  /**
   * Polls the server for new messages.
   */
  async checkForNewMessages() {
    if (this.isChecking) return; // Prevent concurrent polling
    this.isChecking = true;

    try {
      const params = new URLSearchParams();
      if (this.lastMessageId) params.append("after", this.lastMessageId);

      const response = await fetch(`${RECENT_MESSAGES_API_URL}?${params.toString()}`);
      if (!response.ok) return;

      const messages = await response.json();
      messages.forEach((message) => {
        if (this.handleNewMessage(message)) {
          // Auto-scroll if the user is near the bottom
          const { scrollTop, scrollHeight, clientHeight } = this.messagesContainer;
          if (scrollHeight - (scrollTop + clientHeight) < 100) {
            scrollToBottom(this.messagesContainer);
          }
        }
      });
    } catch (error) {
      console.error("Error checking messages:", error);
    } finally {
      this.isChecking = false; // Reset the flag after the check is complete
    }
  }

  /**
   * Sends a new message to the server.
   * @param {string} content - The message content.
   */
  async sendMessage(content) {
    if (!content.trim()) return;

    try {
        // Check for new messages before sending
        await this.checkForNewMessages();

        const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
        const response = await fetch(MESSAGES_API_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken,
            },
            body: JSON.stringify({  
                content: content.trim(), 
                parent_message_id: this.replyMessageId
            }),
        });

        if (response.ok) {
            const messageData = await response.json();
            this.handleNewMessage(messageData);
            scrollToBottom(this.messagesContainer);
            this.cancelReply(); // Clear the reply after sending
            return messageData;
        } else if (response.status === 429) {
            console.log("Rate limit exceeded. Please wait before sending more messages.");
            return null;
        }
    } catch (error) {
        console.error("Error sending message:", error);
    }
}

  /**
   * Handles clicking on a message to set it as a reply.
   * @param {Event} event - The click event.
   */
  handleMessageClick(event) {
    const messageBubble = event.target.closest(".message-bubble");
    if (messageBubble) {
      const messageContainer = messageBubble.closest(".message-container");
      const messageId = messageContainer.dataset.messageId;
      const username = messageContainer.querySelector(".message-username").textContent;
      const content = messageContainer.querySelector(".message-content").textContent;

      this.setReply(messageId, username, content);
    }
  }

  /**
   * Sets the reply message and updates the UI.
   * @param {string} messageId - The ID of the message being replied to.
   * @param {string} username - The username of the message author.
   * @param {string} content - The content of the message.
   */
  setReply(messageId, username, content) {
    this.replyMessageId = messageId;
    document.getElementById("reply-username").textContent = username;
    document.getElementById("reply-content").textContent = content;
    document.getElementById("reply-container").style.display = "flex"; // Show the reply container
  }

  /**
   * Cancels the reply and hides the reply container.
   */
  cancelReply() {
    this.replyMessageId = null;
    document.getElementById("reply-username").textContent = "";
    document.getElementById("reply-content").textContent = "";
    document.getElementById("reply-container").style.display = "none"; // Hide the reply container
  }
}