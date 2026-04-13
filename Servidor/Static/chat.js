const socket = io();

let username = null;
let display_name = null;
let role = null;

socket.on("connect", () => {
  console.log("Conectado al servidor de chat");
});

socket.on("message", (msg) => {
  const chat = document.getElementById("chat");
  
  // Limpiar el estado vacío si existe
  const emptyState = chat.querySelector(".empty-state");
  if (emptyState) {
    emptyState.remove();
  }
  
  // El mensaje viene como objeto JSON desde el servidor
  const messageDiv = document.createElement("div");
  const isOwn = msg.username === username;
  messageDiv.className = `message ${isOwn ? 'own' : 'other'}`;
  
  const time = new Date().toLocaleTimeString('es-ES', {hour: '2-digit', minute:'2-digit'});
  
  messageDiv.innerHTML = `
    <div class="message-user">${escapeHtml(msg.display_name)}</div>
    <div class="message-text">${escapeHtml(msg.text)}</div>
    <div class="message-timestamp">${time}</div>
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

function logout() {
  // Hacer logout en el servidor
  fetch("/logout", { method: "POST" }).then(() => {
    window.location.href = "/";
  });
}

// Cargar información del usuario desde el servidor
window.addEventListener('load', () => {
  // Obtener información del usuario actual
  fetch("/get_user_info")
    .then(response => response.json())
    .then(data => {
      if (!data.username) {
        // Sin sesión, redirigir a login
        window.location.href = "/";
        return;
      }
      
      username = data.username;
      display_name = data.display_name;
      role = data.role;
      
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
    })
    .catch(error => {
      console.error("Error obteniendo información del usuario:", error);
      window.location.href = "/";
    });
});
