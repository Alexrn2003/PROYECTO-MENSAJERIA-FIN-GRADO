const socket = io();
const username = localStorage.getItem("username");

socket.emit("connect_user", { username });

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
