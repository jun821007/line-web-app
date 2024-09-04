document.getElementById("qrLogin").addEventListener("click", function() {
    // 显示二维码登录界面
    var qrCodeContainer = document.getElementById("qrCodeContainer");
    qrCodeContainer.style.display = "block";
});

document.getElementById("qrCodeContainer").addEventListener("click", function() {
    // 模拟登录成功，显示 LINE 界面
    var loginContainer = document.getElementById("loginContainer");
    var lineContainer = document.getElementById("lineContainer");
    loginContainer.style.display = "none";
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
