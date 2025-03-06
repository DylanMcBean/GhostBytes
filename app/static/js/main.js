import { MessageHandler } from "./messages.js";
import { scrollToBottom } from "./utils.js";

document.addEventListener("DOMContentLoaded", () => {
  const messagesContainer = document.getElementById("messages");
  const messageForm = document.getElementById("message-form");
  const messageInput = document.getElementById("message-input");

  const messageHandler = new MessageHandler(messagesContainer);
  let pollInterval;

  // Set lastMessageId from the last message element, if any.
  const initializeLastMessage = () => {
    const lastMessage = document.querySelector(".message:last-child");
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

  // Initialization
  const init = () => {
    initializeLastMessage();
    scrollToBottom(messagesContainer);
    pollInterval = setInterval(() => {
      messageHandler.checkForNewMessages();
    }, 3000);

    messageInput.addEventListener("keydown", handleInputKeydown);
    messageForm.addEventListener("submit", handleFormSubmit);
  };

  init();
});
