document.getElementById("openLine").addEventListener("click", function() {
  chrome.runtime.sendMessage({ action: "openLine" }, function(response) {
    console.log(response.status);
  });
});

document.getElementById("getQRCode").addEventListener("click", function() {
  chrome.runtime.sendMessage({ action: "getQRCode" }, function(response) {
    var qrCodeContainer = document.getElementById("qrCodeContainer");
    var qrCodeImage = document.getElementById("qrCodeImage");
    qrCodeImage.src = response.qrCodeUrl;
    qrCodeContainer.style.display = "block";
  });
});

document.getElementById("getAuthCode").addEventListener("click", function() {
  chrome.runtime.sendMessage({ action: "getAuthCode" }, function(response) {
    var authCodeContainer = document.getElementById("authCodeContainer");
    var authCode = document.getElementById("authCode");
    authCode.textContent = "Auth Code: " + response.authCode;
    authCodeContainer.style.display = "block";
  });
});

document.getElementById("getChatHistory").addEventListener("click", function() {
  chrome.runtime.sendMessage({ action: "getChatHistory" }, function(response) {
    var chatHistoryContainer = document.getElementById("chatHistoryContainer");
    var chatHistory = document.getElementById("chatHistory");
    chatHistory.innerHTML = "";
    response.chatHistory.forEach(function(chat) {
      var li = document.createElement("li");
      li.textContent = chat.sender + ": " + chat.message;
      chatHistory.appendChild(li);
    });
    chatHistoryContainer.style.display = "block";
  });
});
