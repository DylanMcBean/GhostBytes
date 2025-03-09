import { MessageHandler } from "./messages.js";
import { scrollToBottom } from "./utils.js";

document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.getElementById("messages");
  const messageForm = document.getElementById("message-form");
  const messageInput = document.getElementById("message-input");
  const cancelReplyBtn = document.getElementById("cancel-reply-btn");

  const messageHandler = new MessageHandler(messagesContainer);
  let pollInterval;

  // Set lastMessageId from the last message element, if any.
  const initializeLastMessage = () => {
    const lastMessage = document.querySelector(".message-container:last-child");
    messageHandler.lastMessageId = lastMessage?.dataset.messageId || null;
  };

  // Event: Send message on Enter (without Shift) or form submit.
  const handleInputKeydown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      messageHandler.sendMessage(messageInput.value).then(() => {
        messageInput.value = "";
        scrollToBottom(messagesContainer);
      });
    }
  };

  const handleFormSubmit = (e) => {
    e.preventDefault();
    messageHandler.sendMessage(messageInput.value).then(() => {
      messageInput.value = "";
      scrollToBottom(messagesContainer);
    });
  };

  // Event: Cancel reply when the cancel button is clicked.
  const handleCancelReply = () => {
    messageHandler.cancelReply();
  };

  // Initialization
  const init = () => {
    initializeLastMessage();
    scrollToBottom(messagesContainer);

    // Start polling for new messages every 3 seconds
    pollInterval = setInterval(() => {
      messageHandler.checkForNewMessages();
    }, 3000);

    // Add event listeners
    messageInput.addEventListener("keydown", handleInputKeydown);
    messageForm.addEventListener("submit", handleFormSubmit);
    cancelReplyBtn.addEventListener("click", handleCancelReply);
  };

  // Cleanup on page unload (optional but good practice)
  const cleanup = () => {
    clearInterval(pollInterval); // Stop polling
    messageInput.removeEventListener("keydown", handleInputKeydown);
    messageForm.removeEventListener("submit", handleFormSubmit);
    cancelReplyBtn.removeEventListener("click", handleCancelReply);
  };

  // Initialize the app
  init();

  // Cleanup when the page is unloaded
  window.addEventListener("beforeunload", cleanup);
});