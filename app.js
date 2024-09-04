document.getElementById("openWindow").addEventListener("click", function() {
    // 显示嵌入的 LINE 界面
    var lineContainer = document.getElementById("lineContainer");
    var lineFrame = document.getElementById("lineFrame");
    lineFrame.src = "chrome-extension://<YOUR_EXTENSION_ID>/main.html"; // 替换为你的 Chrome 扩展的 URL
    lineContainer.style.display = "block";
});
