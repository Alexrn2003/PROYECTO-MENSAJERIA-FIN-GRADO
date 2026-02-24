const socket = io();

// Obtener datos del usuario del sessionStorage
const username = sessionStorage.getItem("username");
const display_name = sessionStorage.getItem("display_name") || username || "Usuario";
const role = sessionStorage.getItem("role") || "user";

// Conectar usuario
socket.emit("connect_user", { 
  username: username,
  display_name: display_name,
  role: role 
});

socket.on("message", (msg) => {
  const chat = document.getElementById("chat");
  
  // Limpiar el estado vacío si existe
  const emptyState = chat.querySelector(".empty-state");
  if (emptyState) {
    emptyState.remove();
  }
  
  // Parsear el mensaje si viene en formato JSON
  let messageObj = typeof msg === 'string' ? JSON.parse(msg) : msg;
  
  const messageDiv = document.createElement("div");
  messageDiv.className = `message ${messageObj.username === username ? 'own' : 'other'}`;
  
  messageDiv.innerHTML = `
    <div class="message-user">${messageObj.display_name || messageObj.username}</div>
    <div class="message-text">${escapeHtml(messageObj.text || messageObj.message)}</div>
    <div class="message-timestamp">${new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit'})}</div>
  `;
  
  chat.appendChild(messageDiv);
  chat.scrollTop = chat.scrollHeight;
});

function enviar() {
  const input = document.getElementById("msg");
  const message = input.value.trim();
  if (message !== "") {
    socket.emit("send_message", { message });
    input.value = "";
    input.focus();
  }
}

function escapeHtml(text) {
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

// Verificar sesión y configurar UI
window.addEventListener('load', () => {
  if (!username) {
    alert("No hay sesión activa. Redirigiendo al login...");
    window.location.href = "/";
  } else {
    // Mostrar información del usuario
    document.getElementById("userDisplay").textContent = `${display_name} (${role})`;
    
    // Permitir enviar con Enter
    const input = document.getElementById("msg");
    if (input) {
      input.addEventListener("keydown", function(e) {
        if (e.key === "Enter") {
          e.preventDefault();
          enviar();
        }
      });
      input.focus();
    }
  }
});
