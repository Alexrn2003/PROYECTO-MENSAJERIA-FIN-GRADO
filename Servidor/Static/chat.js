const socket = io(); // IIS se encarga del resto

// No necesitas enviar "connect_user", tu Python ya saca los datos de la session
// al detectar el evento "connect" nativo.

// ESCUCHAR mensajes del servidor
socket.on("nuevo_mensaje", (data) => {
    const chat = document.getElementById("chat");
    
    // Quitar estado vacío si existe
    const emptyState = chat.querySelector(".empty-state");
    if (emptyState) emptyState.remove();

    const messageDiv = document.createElement("div");
    // Comprobamos si el nombre de pantalla coincide para ponerlo a la derecha
    const esPropio = data.usuario === sessionStorage.getItem("display_name");
    messageDiv.className = `message ${esPropio ? 'own' : 'other'}`;
    
    messageDiv.innerHTML = `
        <div class="message-user">${data.usuario}</div>
        <div class="message-text">${escapeHtml(data.mensaje)}</div>
        <div class="message-timestamp">${data.fecha}</div>
    `;
    
    chat.appendChild(messageDiv);
    chat.scrollTop = chat.scrollHeight;
});

// ENVIAR mensaje al servidor
function enviar() {
    const input = document.getElementById("msg");
    const message = input.value.trim();
    if (message !== "") {
        // CAMBIO: Usamos "mensaje" porque así lo espera tu @socketio.on("mensaje")
        socket.emit("mensaje", { 
            mensaje: message,
            canal: "global" // O el canal que tengas activo
        });
        input.value = "";
        input.focus();
    }
}