document.getElementById("openWindow").addEventListener("click", async function() {
    // 模拟打开新窗口的功能
    alert("Opening new window...");
    // 在实际应用中，你可以使用 window.open() 打开新窗口
    // window.open("https://line.me", "_blank", "width=800,height=580");
});

document.getElementById("openWindow").addEventListener("touchstart", async function() {
    // 模拟打开新窗口的功能
    alert("Opening new window...");
});

// 模拟删除旧数据的功能
async function checkAndDeleteLegacyData() {
    console.log("Checking and deleting legacy data...");
    // 在实际应用中，你可以使用 localStorage 或 IndexedDB 进行数据存储和删除
}

// 模拟获取显示器信息的功能
async function getDisplayInfo() {
    console.log("Getting display info...");
    // 在实际应用中，你可以使用 window.screen 对象获取显示器信息
    return {
        bounds: {
            left: 0,
            top: 0,
            width: window.screen.width,
            height: window.screen.height
        }
    };
}

// 初始化
(async function init() {
    await checkAndDeleteLegacyData();
    const displayInfo = await getDisplayInfo();
    console.log("Display info:", displayInfo);
})();
