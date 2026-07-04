const form = document.querySelector("#chat-form");
const messageInput = document.querySelector("#message");
const messagesContainer = document.querySelector("#messages");

const threadIdKey = "fadua-bi-thread-id";
let threadId = window.localStorage.getItem(threadIdKey);

function appendMessage(role, text) {
  const article = document.createElement("article");
  article.className = `message ${role}`;

  const paragraph = document.createElement("p");
  paragraph.textContent = text;

  article.appendChild(paragraph);
  messagesContainer.appendChild(article);
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

async function handleSubmit(event) {
  event.preventDefault();

  const message = messageInput.value.trim();
  if (!message) {
    return;
  }

  appendMessage("user", message);
  messageInput.value = "";

  const submitButton = form.querySelector("button[type='submit']");
  submitButton.disabled = true;

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        thread_id: threadId,
      }),
    });

    const payload = await response.json();

    if (!response.ok) {
      const errorMessage =
        payload?.error?.message || "No pudimos procesar la consulta en este momento.";
      appendMessage("system", errorMessage);
      return;
    }

    threadId = payload.meta.thread_id;
    window.localStorage.setItem(threadIdKey, threadId);
    appendMessage("assistant", payload.answer);
  } catch (error) {
    appendMessage("system", "La API no esta disponible en este momento.");
  } finally {
    submitButton.disabled = false;
    messageInput.focus();
  }
}

form.addEventListener("submit", handleSubmit);
