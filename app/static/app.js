const form = document.querySelector("#chat-form");
const submitButton = document.querySelector("#submit-button");
const messageInput = document.querySelector("#message");
const messagesContainer = document.querySelector("#messages");
const emptyState = document.querySelector("#empty-state");
const suggestionsContainer = document.querySelector("#suggestions");
const emptySuggestionsContainer = document.querySelector("#empty-suggestions");
const newChatButton = document.querySelector("#new-chat-button");
const threadBadge = document.querySelector("#thread-badge");
const connectionBadge = document.querySelector("#connection-badge");

const threadIdKey = "fadua-bi-thread-id";
let threadId = window.localStorage.getItem(threadIdKey);
let activeTypingNode = null;
let currentStatus = "Listo";

const suggestedPrompts = [
  "¿Cuántas ventas tenemos al día de hoy?",
  "¿Cuál fue el mes de mayores ventas?",
  "¿En qué mes tuvimos pocos leads pero muchas ventas?",
  "¿Cuál es la cantidad de lead y ventas proyectadas del próximo mes?",
];

function autosizeTextarea() {
  messageInput.style.height = "auto";
  messageInput.style.height = `${Math.min(messageInput.scrollHeight, 220)}px`;
}

function formatDateRange(dataRange) {
  if (!dataRange?.from_date && !dataRange?.to_date) {
    return null;
  }
  if (dataRange?.from_date && dataRange?.to_date) {
    return `${dataRange.from_date} → ${dataRange.to_date}`;
  }
  return dataRange?.to_date || dataRange?.from_date;
}

function setThreadBadge() {
  threadBadge.textContent = threadId ? `Sesión ${threadId}` : "Sin sesión";
}

function setConnectionStatus(text, muted = false) {
  currentStatus = text;
  connectionBadge.textContent = text;
  connectionBadge.classList.toggle("badge-muted", muted);
}

function hideEmptyStateIfNeeded() {
  const hasMessages = messagesContainer.querySelector(".message-row");
  emptyState.classList.toggle("is-hidden", Boolean(hasMessages));
}

function createSuggestionButton(promptText) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "suggestion-chip";
  button.textContent = promptText;
  button.addEventListener("click", () => {
    messageInput.value = promptText;
    autosizeTextarea();
    messageInput.focus();
  });
  return button;
}

function renderSuggestions() {
  [suggestionsContainer, emptySuggestionsContainer].forEach((container) => {
    container.replaceChildren();
    suggestedPrompts.forEach((promptText) => {
      container.appendChild(createSuggestionButton(promptText));
    });
  });
}

function createMetadataCard(label, value, isLink = false) {
  const card = document.createElement("div");
  card.className = "metadata-card";

  const title = document.createElement("p");
  title.className = "metadata-label";
  title.textContent = label;

  const body = document.createElement(isLink ? "a" : "p");
  body.className = "metadata-value";

  if (isLink) {
    body.classList.add("trace-link");
    body.href = value;
    body.target = "_blank";
    body.rel = "noreferrer";
    body.textContent = "Abrir trace";
  } else {
    body.textContent = value;
  }

  card.append(title, body);
  return card;
}

function buildAssistantExtras(payload) {
  const extras = document.createElement("div");
  extras.className = "assistant-extras";

  const metadataGrid = document.createElement("div");
  metadataGrid.className = "metadata-grid";

  const dateRange = formatDateRange(payload.data_range);
  if (dateRange) {
    metadataGrid.appendChild(createMetadataCard("Período analizado", dateRange));
  }
  if (payload.meta?.last_data_date) {
    metadataGrid.appendChild(createMetadataCard("Último dato", payload.meta.last_data_date));
  }
  if (payload.meta?.model) {
    metadataGrid.appendChild(createMetadataCard("Modelo", payload.meta.model));
  }
  if (payload.intent) {
    metadataGrid.appendChild(createMetadataCard("Intent detectado", payload.intent));
  }
  if (payload.meta?.trace_url) {
    metadataGrid.appendChild(createMetadataCard("Observabilidad", payload.meta.trace_url, true));
  }

  if (metadataGrid.childElementCount > 0) {
    extras.appendChild(metadataGrid);
  }

  if (Array.isArray(payload.meta?.warnings) && payload.meta.warnings.length > 0) {
    const warningCard = document.createElement("div");
    warningCard.className = "metadata-card";

    const label = document.createElement("p");
    label.className = "metadata-label";
    label.textContent = "Warnings";

    const list = document.createElement("ul");
    list.className = "warning-list";
    payload.meta.warnings.forEach((warning) => {
      const item = document.createElement("li");
      item.textContent = warning;
      list.appendChild(item);
    });

    warningCard.append(label, list);
    extras.appendChild(warningCard);
  }

  if (Array.isArray(payload.meta?.prompts) && payload.meta.prompts.length > 0) {
    const promptCard = document.createElement("div");
    promptCard.className = "metadata-card";

    const label = document.createElement("p");
    label.className = "metadata-label";
    label.textContent = "Prompts";

    const value = document.createElement("p");
    value.className = "metadata-value";
    value.textContent = payload.meta.prompts
      .map((prompt) => `${prompt.name} v${prompt.version}${prompt.label ? ` (${prompt.label})` : ""}`)
      .join(" · ");

    promptCard.append(label, value);
    extras.appendChild(promptCard);
  }

  if (payload.chart) {
    const chartCard = document.createElement("div");
    chartCard.className = "chart-card";

    const frame = document.createElement("div");
    frame.className = "chart-frame";

    const canvas = document.createElement("canvas");
    frame.appendChild(canvas);
    chartCard.appendChild(frame);
    extras.appendChild(chartCard);

    requestAnimationFrame(() => renderChart(canvas, payload.chart));
  }

  return extras.childElementCount > 0 ? extras : null;
}

function renderChart(canvas, chartPayload) {
  const datasetColors = ["#111827", "#6b7280", "#2563eb", "#059669"];
  const borderColors = ["#111827", "#6b7280", "#2563eb", "#059669"];

  new window.Chart(canvas, {
    type: chartPayload.type || "bar",
    data: {
      labels: chartPayload.labels || [],
      datasets: (chartPayload.datasets || []).map((dataset, index) => ({
        label: dataset.label,
        data: dataset.data,
        backgroundColor:
          chartPayload.type === "line"
            ? `${borderColors[index % borderColors.length]}22`
            : datasetColors[index % datasetColors.length],
        borderColor: borderColors[index % borderColors.length],
        borderWidth: 2,
        fill: chartPayload.type === "line",
        tension: 0.35,
        pointRadius: chartPayload.type === "line" ? 3 : 0,
        borderRadius: chartPayload.type === "bar" ? 8 : 0,
      })),
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: {
            color: "#4b5563",
            usePointStyle: true,
            boxWidth: 10,
            boxHeight: 10,
            padding: 18,
          },
        },
      },
      scales: {
        x: {
          ticks: {
            color: "#6b7280",
          },
          grid: {
            display: false,
          },
        },
        y: {
          ticks: {
            color: "#6b7280",
          },
          grid: {
            color: "#ececf1",
          },
          beginAtZero: true,
        },
      },
    },
  });
}

function createMessageRow({ role, text, payload = null, isLoading = false }) {
  const row = document.createElement("article");
  row.className = `message-row ${role}-row`;

  const avatar = document.createElement("div");
  avatar.className = `message-avatar ${role}-avatar`;
  avatar.textContent = role === "assistant" ? "AI" : role === "user" ? "Tú" : "!";

  const content = document.createElement("div");
  content.className = "message-content";

  const meta = document.createElement("div");
  meta.className = "message-meta";

  const roleLabel = document.createElement("span");
  roleLabel.className = "message-role";
  roleLabel.textContent =
    role === "assistant" ? "BI Assistant" : role === "user" ? "Vos" : "Sistema";

  meta.appendChild(roleLabel);

  if (payload?.meta?.source) {
    const source = document.createElement("span");
    source.textContent = payload.meta.source;
    meta.appendChild(source);
  }

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  if (isLoading) {
    const typing = document.createElement("div");
    typing.className = "typing-indicator";
    typing.innerHTML = "<span></span><span></span><span></span>";
    bubble.appendChild(typing);
  } else {
    const paragraph = document.createElement("p");
    paragraph.textContent = text;
    bubble.appendChild(paragraph);
  }

  content.append(meta, bubble);

  if (role === "assistant" && payload && !isLoading) {
    const extras = buildAssistantExtras(payload);
    if (extras) {
      content.appendChild(extras);
    }
  }

  row.append(avatar, content);
  return row;
}

function appendMessage(role, text, payload = null) {
  const row = createMessageRow({ role, text, payload });
  messagesContainer.appendChild(row);
  hideEmptyStateIfNeeded();
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  row.scrollIntoView({ behavior: "smooth", block: "end" });
}

function showTypingIndicator() {
  removeTypingIndicator();
  activeTypingNode = createMessageRow({
    role: "assistant",
    text: "",
    payload: null,
    isLoading: true,
  });
  messagesContainer.appendChild(activeTypingNode);
  hideEmptyStateIfNeeded();
  activeTypingNode.scrollIntoView({ behavior: "smooth", block: "end" });
}

function removeTypingIndicator() {
  if (activeTypingNode) {
    activeTypingNode.remove();
    activeTypingNode = null;
  }
}

function clearConversation() {
  Array.from(messagesContainer.querySelectorAll(".message-row")).forEach((node) => node.remove());
  removeTypingIndicator();
  hideEmptyStateIfNeeded();
}

function resetConversation() {
  threadId = null;
  window.localStorage.removeItem(threadIdKey);
  clearConversation();
  setThreadBadge();
  setConnectionStatus("Listo", false);
  messageInput.value = "";
  autosizeTextarea();
  messageInput.focus();
}

async function handleSubmit(event) {
  event.preventDefault();

  const message = messageInput.value.trim();
  if (!message) {
    return;
  }

  appendMessage("user", message);
  messageInput.value = "";
  autosizeTextarea();
  submitButton.disabled = true;
  setConnectionStatus("Consultando...", true);
  showTypingIndicator();

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
    removeTypingIndicator();

    if (!response.ok) {
      const errorMessage =
        payload?.error?.message || "No pudimos procesar la consulta en este momento.";
      appendMessage("system", errorMessage);
      setConnectionStatus("Error controlado", true);
      return;
    }

    threadId = payload.meta.thread_id;
    window.localStorage.setItem(threadIdKey, threadId);
    setThreadBadge();
    setConnectionStatus(payload.meta?.source || currentStatus, true);
    appendMessage("assistant", payload.answer, payload);
  } catch (error) {
    removeTypingIndicator();
    appendMessage("system", "La API no está disponible en este momento.");
    setConnectionStatus("API no disponible", true);
  } finally {
    submitButton.disabled = false;
    messageInput.focus();
  }
}

function handleComposerKeydown(event) {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    form.requestSubmit();
  }
}

form.addEventListener("submit", handleSubmit);
messageInput.addEventListener("input", autosizeTextarea);
messageInput.addEventListener("keydown", handleComposerKeydown);
newChatButton.addEventListener("click", resetConversation);

renderSuggestions();
setThreadBadge();
autosizeTextarea();
