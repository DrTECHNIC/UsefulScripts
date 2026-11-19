const { contextBridge, ipcRenderer, clipboard, webUtils } = require("electron");

contextBridge.exposeInMainWorld("psWorkbench", {
  minimizeWindow: () => ipcRenderer.send("window:minimize"),
  maximizeWindow: () => ipcRenderer.send("window:maximize"),
  closeWindow: () => ipcRenderer.send("window:close"),

  pickTarget: (mode) => ipcRenderer.invoke("dialog:pickTarget", mode),
  pickSaveOrOpenFile: (title) => ipcRenderer.invoke("dialog:pickSaveOrOpenFile", title),
  pickScriptFile: () => ipcRenderer.invoke("dialog:pickScriptFile"),

  getPathForFile: (file) => {
    try {
      if (webUtils && typeof webUtils.getPathForFile === "function") {
        return webUtils.getPathForFile(file);
      }
    } catch (_) {
      // ignore
    }
    return file && file.path ? file.path : "";
  },

  copyText: async (text) => {
    try {
      clipboard.writeText(text);
      return true;
    } catch (_) {
      return false;
    }
  },

  parseScript: (scriptPath) => ipcRenderer.invoke("scripts:parse", scriptPath),
  getBundledScripts: () => ipcRenderer.invoke("scripts:bundled"),
  unblockScripts: (paths) => ipcRenderer.invoke("scripts:unblock", paths),
  getShellInfo: () => ipcRenderer.invoke("terminal:info"),
  completePath: (token, isFirstToken) =>
    ipcRenderer.invoke("terminal:completePath", { token, isFirstToken }),
  runCommand: (command) => ipcRenderer.invoke("terminal:run", command),
  stopCommand: () => ipcRenderer.invoke("terminal:stop"),

  onTerminalEvent: (listener) => {
    const handler = (_event, payload) => listener(payload);
    ipcRenderer.on("terminal:event", handler);
    return () => ipcRenderer.removeListener("terminal:event", handler);
  },

  loadConfig: () => ipcRenderer.invoke("store:load"),
  saveConfig: (config) => ipcRenderer.invoke("store:save", config),
});
