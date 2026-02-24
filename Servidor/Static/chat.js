const socket = io();

// Obtener datos del usuario del sessionStorage (guardado en login)
const username = sessionStorage.getItem("username");
const display_name = sessionStorage.getItem("display_name") || username || "Usuario";
const role = sessionStorage.getItem("role") || "user";

// Mostrar información del usuario en la interfaz
console.log(`✅ Usuario conectado: ${display_name} (${username})`);
console.log(`👤 Rol: ${role}`);

// Conectar usuario
socket.emit("connect_user", { 
  username: username,
  display_name: display_name,
  role: role 
});

socket.on("message", (msg) => {
  const chat = document.getElementById("chat");
  chat.innerHTML += msg + "<br>";
  chat.scrollTop = chat.scrollHeight;
});

function enviar() {
  const input = document.getElementById("msg");
  const message = input.value;
  if (message.trim() !== "") {
    socket.emit("send_message", { message });
    input.value = "";
  }
}

// Verificar que el usuario está autenticado y permitir enviar con Enter
window.addEventListener('load', () => {
  if (!username) {
    alert("No hay sesión activa. Redirigiendo al login...");
    window.location.href = "/";
  } else {
    // Mostrar usuario en la página
    const header = document.querySelector('h2');
    if (header) {
      header.textContent = `Chat Empresarial - ${display_name}`;
    }
    // Permitir enviar mensaje con Enter
    const input = document.getElementById("msg");
    if (input) {
      input.addEventListener("keydown", function(e) {
        if (e.key === "Enter") {
          e.preventDefault();
          enviar();
        }
      });
    }
  }
});
