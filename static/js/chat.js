const messagesContainer = document.getElementById('messages');
const messageForm = document.getElementById('message-form');
const messageInput = document.getElementById('message-input');
let lastMessageId = null;
let pollInterval;

// Message creation
const createMessageElement = (messageData) => {
  const lastMessageElement = messagesContainer.lastElementChild;
  let shouldGroup = false;

  if (lastMessageElement) {
    const lastTimestamp = new Date(lastMessageElement.querySelector('.message-timestamp').dataset.timestamp);
    const newTimestamp = new Date(messageData.timestamp);
    const lastUsername = lastMessageElement.querySelector('.username').textContent;

    shouldGroup = messageData.username === lastUsername && (newTimestamp - lastTimestamp) < 60000;
  }

  if (shouldGroup) {
    const contentDiv = lastMessageElement.querySelector('.message-content');
    contentDiv.innerHTML += `<br>${escapeHtml(messageData.content)}`;

    const timestampElement = lastMessageElement.querySelector('.message-timestamp');
    timestampElement.textContent = new Date(messageData.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    timestampElement.dataset.timestamp = messageData.timestamp;

    lastMessageElement.dataset.messageId = messageData.id;
    lastMessageId = messageData.id; // Update lastMessageId for grouped messages
    return null;
  } else {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${messageData.isUser ? 'user-message' : ''}`;
    messageDiv.dataset.messageId = messageData.id;

    messageDiv.innerHTML = `
      <div class="message-header">
        <span class="username">${escapeHtml(messageData.username)}</span>
        <span class="message-timestamp" data-timestamp="${messageData.timestamp}">
          ${new Date(messageData.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
      <div class="message-content">${escapeHtml(messageData.content)}</div>
    `;

    return messageDiv;
  }
};

// Message handling
const handleNewMessage = (messageData) => {
  const existingMessage = document.querySelector(`[data-message-id="${messageData.id}"]`);
  if (!existingMessage) {
    const messageElement = createMessageElement(messageData);
    if (messageElement) {
      messagesContainer.appendChild(messageElement);
    }
    lastMessageId = messageData.id;
    return true;
  }
  lastMessageId = messageData.id;
  return false;
};

// Message fetching
const checkForNewMessages = async () => {
  try {
    const params = new URLSearchParams();
    if (lastMessageId) params.append('after', lastMessageId);

    const response = await fetch(`/messages/recent?${params.toString()}`);
    if (!response.ok) return;

    const messages = await response.json();
    messages.forEach(message => {
      if (handleNewMessage(message)) {
        const { scrollTop, scrollHeight, clientHeight } = messagesContainer;
        if (scrollHeight - (scrollTop + clientHeight) < 100) {
          scrollToBottom();
        }
      }
    });
  } catch (error) {
    console.error('Error checking messages:', error);
  }
};

// Message submission
const sendMessage = async (content) => {
  if (!content.trim()) return;

  try {
    await checkForNewMessages();
    const response = await fetch('/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRFToken': document.querySelector('meta[name="csrf-token"]').content
      },
      body: JSON.stringify({ content: content.trim() })
    });

    if (response.ok) {
      const messageData = await response.json();
      handleNewMessage(messageData);
      messageInput.value = '';
      scrollToBottom();
    }
  } catch (error) {
    console.error('Message send error:', error);
  }
};

// Event handlers
const handleInputKeydown = (e) => {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault();
    sendMessage(messageInput.value);
  }
};

const handleFormSubmit = (e) => {
  e.preventDefault();
  sendMessage(messageInput.value);
};

// Utilities
const scrollToBottom = () => {
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
};

const escapeHtml = (text) => {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
};

const initializeLastMessage = () => {
  const lastMessage = document.querySelector('.message:last-child');
  lastMessageId = lastMessage?.dataset.messageId || null;
};

// Initialization
const init = () => {
  initializeLastMessage();
  scrollToBottom();
  pollInterval = setInterval(checkForNewMessages, 3000);

  messageInput.addEventListener('keydown', handleInputKeydown);
  messageForm.addEventListener('submit', handleFormSubmit);
};

// Start the application
init();
