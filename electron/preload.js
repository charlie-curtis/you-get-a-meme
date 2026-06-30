const { contextBridge } = require("electron");

const backendArg = process.argv.find((arg) => arg.startsWith("--backend-url="));
const backendUrl = backendArg ? backendArg.replace("--backend-url=", "") : "http://127.0.0.1:8765";

contextBridge.exposeInMainWorld("youGetAMeme", {
  backendUrl,
  platform: process.platform
});
