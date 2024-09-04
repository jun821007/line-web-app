chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  if (request.action === "openLine") {
    chrome.tabs.create({ url: "https://web.line.me/" });
    sendResponse({ status: "LINE opened" });
  } else if (request.action === "getQRCode") {
    // 模拟获取二维码
    sendResponse({ qrCodeUrl: "https://via.placeholder.com/150" });
  } else if (request.action === "getAuthCode") {
    // 模拟获取认证码
    sendResponse({ authCode: "123456" });
  } else if (request.action === "getChatHistory") {
    // 模拟获取对话记录
    sendResponse({ chatHistory: [
      { sender: "Alice", message: "Hello!" },
      { sender: "Bob", message: "Hi there!" }
    ]});
  }
});
