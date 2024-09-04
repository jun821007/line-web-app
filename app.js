document.getElementById("openWindow").addEventListener("click", function() {
    // 显示嵌入的 LINE 界面
    var lineContainer = document.getElementById("lineContainer");
    lineContainer.style.display = "block";
});

document.getElementById("sendMessage").addEventListener("click", function() {
    var messageInput = document.getElementById("messageInput");
    var messageText = messageInput.value;
    if (messageText.trim() !== "") {
        var chatWindow = document.getElementById("chatWindow");
        var newMessage = document.createElement("div");
        newMessage.className = "message sent";
        newMessage.textContent = messageText;
        chatWindow.appendChild(newMessage);
        messageInput.value = "";
        chatWindow.scrollTop = chatWindow.scrollHeight;
    }
});
