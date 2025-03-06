/**
 * Escapes HTML to prevent XSS attacks.
 * @param {string} text
 * @returns {string} Escaped text.
 */
export const escapeHtml = (text) => {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
};

/**
 * Scrolls the messages container to the bottom.
 * @param {HTMLElement} container
 */
export const scrollToBottom = (container) => {
  container.scrollTop = container.scrollHeight;
};
