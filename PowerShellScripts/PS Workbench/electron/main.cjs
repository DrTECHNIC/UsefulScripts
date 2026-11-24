const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const path = require("path");
const fs = require("fs");
const os = require("os");
const { spawn, execFileSync, execFile } = require("child_process");
const { parseScriptFile } = require("./psParser.cjs");

const DONE_MARKER = "__PSW_CMD_DONE__";
const INIT_MARKER = "__PSW_SHELL_READY__";
const PROJECT_NAME = "PS Workbench";

function getProjectRoot() {
  if (app.isPackaged) {
    return path.dirname(app.getPath("exe"));
  }
  return path.resolve(__dirname, "..");
}

let mainWindow = null;
let psProcess = null;
let shellInfo = {
  shellName: "Windows PowerShell",
  shellExe: "powershell.exe",
  version: "5.1",
  cwd: getProjectRoot(),
  projectRoot: getProjectRoot(),
  projectName: PROJECT_NAME,
  encoding: "UTF-8",
};
let shellReady = false;
let stdoutBuffer = "";

function stripAnsi(str) {
  return str.replace(/\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])/g, "");
}

function getBundledScriptsDir() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, "scripts");
  }
  return path.join(__dirname, "..", "scripts");
}

function detectPowerShell() {
  const projectRoot = getProjectRoot();
  const candidates = [
    { exe: "pwsh.exe", label: "PowerShell" },
    { exe: "powershell.exe", label: "Windows PowerShell" },
  ];

  for (const c of candidates) {
    try {
      const version = execFileSync(
        c.exe,
        ["-NoLogo", "-NoProfile", "-Command", "$PSVersionTable.PSVersion.ToString()"],
        { encoding: "utf8", timeout: 4000, windowsHide: true },
      ).trim();
      if (version) {
        return {
          shellName: c.label,
          shellExe: c.exe,
          version,
          cwd: projectRoot,
          projectRoot,
          projectName: PROJECT_NAME,
          encoding: "UTF-8",
        };
      }
    } catch (_) {
      // Try next candidate
    }
  }

  return {
    ...shellInfo,
    cwd: projectRoot,
    projectRoot,
    projectName: PROJECT_NAME,
  };
}

function unblockFilesSilently(filePaths) {
  return new Promise((resolve) => {
    const existing = (filePaths || []).filter((p) => typeof p === "string" && p && fs.existsSync(p));
    if (existing.length === 0) {
      resolve({ ok: true, count: 0 });
      return;
    }
    const encodedList = Buffer.from(JSON.stringify(existing), "utf8").toString("base64");
    const cmd = `$paths = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('${encodedList}')) | ConvertFrom-Json; foreach ($p in $paths) { try { Unblock-File -LiteralPath $p -ErrorAction SilentlyContinue } catch {} }`;
    execFile(
      shellInfo.shellExe || "powershell.exe",
      ["-NoLogo", "-NoProfile", "-NonInteractive", "-Command", cmd],
      { timeout: 6000, windowsHide: true },
      (err) => {
        if (err) {
          resolve({ ok: false, count: 0, error: err.message });
        } else {
          resolve({ ok: true, count: existing.length });
        }
      },
    );
  });
}

async function loadBundledScripts() {
  const dir = getBundledScriptsDir();
  if (!fs.existsSync(dir)) return [];

  const helloPath = path.join(dir, "hello.ps1");
  const entries = fs.existsSync(helloPath)
    ? ["hello.ps1"]
    : fs
        .readdirSync(dir)
        .filter((name) => name.toLowerCase().endsWith(".ps1"))
        .sort((a, b) => a.localeCompare(b));

  const fullPaths = entries.map((name) => path.join(dir, name));
  await unblockFilesSilently(fullPaths);

  const items = [];
  for (let i = 0; i < entries.length; i++) {
    const fileName = entries[i];
    const fullPath = fullPaths[i];
    const parsed = await parseScriptFile(fullPath, shellInfo.shellExe);
    const baseName = fileName.replace(/\.ps1$/i, "");
    const title = parsed.title || baseName;

    items.push({
      id: `bundled-${baseName.toLowerCase()}`,
      file: fileName,
      title,
      shortTitle: title,
      description: parsed.description || fullPath,
      kind: parsed.inferredKind || "rename",
      icon: baseName.toLowerCase() === "hello" ? "terminal" : "file",
      sourcePath: fullPath,
      groupId: undefined,
      group: "",
      hidden: false,
      defaultParameterSet: parsed.defaultParameterSet,
      flags: parsed.ok ? parsed.flags : [],
    });
  }

  return items;
}

function sendTerminalEvent(payload) {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.send("terminal:event", payload);
  }
}

function startPowerShellSession() {
  stopPowerShellProcessOnly();
  shellReady = false;
  stdoutBuffer = "";

  const args = [
    "-NoLogo",
    "-NoExit",
    "-NoProfile",
    "-ExecutionPolicy",
    "Bypass",
    "-Command",
    "-",
  ];

  psProcess = spawn(shellInfo.shellExe, args, {
    cwd: shellInfo.cwd || shellInfo.projectRoot,
    windowsHide: true,
    stdio: ["pipe", "pipe", "pipe"],
  });

  psProcess.stdout.setEncoding("utf8");
  psProcess.stderr.setEncoding("utf8");

  psProcess.stdout.on("data", (chunk) => {
    stdoutBuffer += chunk;
    const lines = stdoutBuffer.split(/\r?\n/);
    stdoutBuffer = lines.pop() ?? "";

    for (const rawLine of lines) {
      const plainLine = stripAnsi(rawLine);

      if (plainLine.startsWith(INIT_MARKER)) {
        const parts = plainLine.split("|");
        if (parts[1]) shellInfo.cwd = parts[1].trim();
        shellReady = true;
        sendTerminalEvent({ type: "info", info: shellInfo });
        continue;
      }

      const doneIdx = plainLine.indexOf(DONE_MARKER);
      if (doneIdx !== -1) {
        if (doneIdx > 0 && shellReady) {
          const rawDoneIdx = rawLine.indexOf(DONE_MARKER);
          const prefix = rawDoneIdx > 0 ? rawLine.slice(0, rawDoneIdx) : plainLine.slice(0, doneIdx);
          if (prefix) sendTerminalEvent({ type: "stdout", text: prefix });
        }
        const parts = plainLine.slice(doneIdx).split("|");
        const exitCode = Number.parseInt(parts[1] || "0", 10) || 0;
        const nextCwd = parts.slice(2).join("|").trim();
        if (nextCwd) shellInfo.cwd = nextCwd;
        sendTerminalEvent({ type: "done", exitCode, cwd: shellInfo.cwd });
        continue;
      }

      if (shellReady) {
        sendTerminalEvent({ type: "stdout", text: rawLine });
      }
    }
  });

  psProcess.stderr.on("data", (chunk) => {
    if (!shellReady) return;
    const cleaned = stripAnsi(chunk);
    const lines = cleaned.split(/\r?\n/);
    for (const line of lines) {
      if (line.length > 0) {
        sendTerminalEvent({ type: "stderr", text: line });
      }
    }
  });

  psProcess.on("exit", () => {
    psProcess = null;
    shellReady = false;
  });

  psProcess.on("error", (err) => {
    sendTerminalEvent({
      type: "error",
      message: `Ошибка запуска PowerShell: ${err.message}`,
    });
  });

  const initLine =
    `try { chcp 65001 | Out-Null } catch {}; ` +
    `[Console]::InputEncoding = [System.Text.Encoding]::UTF8; ` +
    `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; ` +
    `$OutputEncoding = [System.Text.Encoding]::UTF8; ` +
    `$ProgressPreference = 'SilentlyContinue'; ` +
    `if ($PSStyle) { $PSStyle.OutputRendering = 'PlainText' }; ` +
    `Write-Output "${INIT_MARKER}|$((Get-Location).Path)"\n`;

  psProcess.stdin.write(initLine);
}

function stopPowerShellProcessOnly() {
  if (psProcess) {
    try {
      psProcess.kill();
    } catch (_) {
      // ignore
    }
    psProcess = null;
  }
}


function completeFileSystemPath(rawToken, isFirstToken) {
  const token = String(rawToken ?? "");
  let quoteChar = "";
  let unquoted = token;

  if (token.startsWith('"') || token.startsWith("'")) {
    quoteChar = token[0];
    unquoted = token.slice(1);
    if (unquoted.endsWith(quoteChar)) {
      unquoted = unquoted.slice(0, -1);
    }
  }

  const lastBackslash = unquoted.lastIndexOf("\\");
  const lastSlash = unquoted.lastIndexOf("/");
  const lastSepIdx = Math.max(lastBackslash, lastSlash);
  const sep = lastSlash > lastBackslash ? "/" : "\\";

  if (unquoted === "~") {
    return [`~${sep}`];
  }

  const dirPart = lastSepIdx >= 0 ? unquoted.slice(0, lastSepIdx + 1) : "";
  const prefix = lastSepIdx >= 0 ? unquoted.slice(lastSepIdx + 1) : unquoted;
  const baseCwd = shellInfo.cwd || shellInfo.projectRoot;

  let searchDir = baseCwd;
  if (dirPart) {
    let dirForResolve = dirPart;
    if (dirForResolve.startsWith("~\\") || dirForResolve.startsWith("~/")) {
      dirForResolve = path.join(os.homedir(), dirForResolve.slice(2));
    }
    searchDir = path.resolve(baseCwd, dirForResolve);
  }

  let entries;
  try {
    entries = fs.readdirSync(searchDir, { withFileTypes: true });
  } catch (_) {
    return [];
  }

  const lowerPrefix = prefix.toLowerCase();
  const matched = entries
    .filter((entry) => entry.name.toLowerCase().startsWith(lowerPrefix))
    .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" }));

  const results = [];
  for (const entry of matched) {
    let isDir = entry.isDirectory();
    if (!isDir && entry.isSymbolicLink()) {
      try {
        isDir = fs.statSync(path.join(searchDir, entry.name)).isDirectory();
      } catch (_) {
        isDir = false;
      }
    }

    let completedRaw;
    if (dirPart) {
      completedRaw = `${dirPart}${entry.name}${isDir ? sep : ""}`;
    } else if (isFirstToken && !isDir) {
      completedRaw = `.${sep}${entry.name}`;
    } else {
      completedRaw = `${entry.name}${isDir ? sep : ""}`;
    }

    const needsQuotes =
      Boolean(quoteChar) || /[\s'"`$&#;(){}\[\],|<>@]/.test(completedRaw);
    if (needsQuotes) {
      const q = quoteChar || '"';
      const escaped =
        q === '"' ? completedRaw.replace(/"/g, '`"') : completedRaw.replace(/'/g, "''");
      results.push(`${q}${escaped}${q}`);
    } else {
      results.push(completedRaw);
    }
  }

  return results;
}

function getConfigPath() {
  return path.join(app.getPath("userData"), "ps-workbench-config.json");
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 1100,
    minHeight: 680,
    frame: false,
    backgroundColor: "#0b0e13",
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  });

  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, "..", "dist", "index.html"));
  }

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  shellInfo = detectPowerShell();
  createWindow();
  startPowerShellSession();

  ipcMain.on("window:minimize", () => mainWindow?.minimize());
  ipcMain.on("window:maximize", () => {
    if (!mainWindow) return;
    if (mainWindow.isMaximized()) {
      mainWindow.unmaximize();
    } else {
      mainWindow.maximize();
    }
  });
  ipcMain.on("window:close", () => mainWindow?.close());

  ipcMain.handle("dialog:pickTarget", async (_event, mode) => {
    if (!mainWindow) return null;
    const isFile = mode === "file";
    const result = await dialog.showOpenDialog(mainWindow, {
      title: isFile ? "Выберите файл" : "Выберите директорию",
      defaultPath: shellInfo.projectRoot,
      properties: isFile ? ["openFile"] : ["openDirectory"],
    });
    if (result.canceled || result.filePaths.length === 0) return null;
    return result.filePaths[0];
  });

  ipcMain.handle("dialog:pickSaveOrOpenFile", async (_event, title) => {
    if (!mainWindow) return null;
    const result = await dialog.showSaveDialog(mainWindow, {
      title: title || "Выберите файл",
      defaultPath: shellInfo.projectRoot,
      filters: [
        { name: "Текстовые файлы", extensions: ["txt", "log"] },
        { name: "Все файлы", extensions: ["*"] },
      ],
    });
    if (result.canceled || !result.filePath) return null;
    return result.filePath;
  });

  ipcMain.handle("dialog:pickScriptFile", async () => {
    if (!mainWindow) return null;
    const scriptsDir = getBundledScriptsDir();
    const result = await dialog.showOpenDialog(mainWindow, {
      title: "Выберите PowerShell-скрипт (.ps1)",
      defaultPath: fs.existsSync(scriptsDir) ? scriptsDir : shellInfo.projectRoot,
      properties: ["openFile"],
      filters: [
        { name: "PowerShell Scripts", extensions: ["ps1"] },
        { name: "All Files", extensions: ["*"] },
      ],
    });
    if (result.canceled || result.filePaths.length === 0) return null;
    return result.filePaths[0];
  });

  ipcMain.handle("scripts:parse", async (_event, scriptPath) => {
    await unblockFilesSilently([scriptPath]);
    return parseScriptFile(scriptPath, shellInfo.shellExe);
  });

  ipcMain.handle("scripts:bundled", async () => {
    return loadBundledScripts();
  });

  ipcMain.handle("scripts:unblock", async (_event, paths) => {
    return unblockFilesSilently(paths);
  });

  ipcMain.handle("terminal:info", async () => shellInfo);

  ipcMain.handle("terminal:completePath", async (_event, payload) => {
    const token = payload && typeof payload.token === "string" ? payload.token : "";
    const isFirstToken = Boolean(payload && payload.isFirstToken);
    return completeFileSystemPath(token, isFirstToken);
  });

  ipcMain.handle("terminal:run", async (_event, command) => {
    if (!command || !String(command).trim()) {
      return { ok: false, error: "Пустая команда" };
    }
    if (!psProcess || psProcess.killed) {
      startPowerShellSession();
    }

    const b64 = Buffer.from(String(command), "utf8").toString("base64");
    const singleLine =
      `$global:LASTEXITCODE = 0; ` +
      `try { ` +
      `$__pswCmd = [System.Text.Encoding]::UTF8.GetString([System.Convert]::FromBase64String('${b64}')); ` +
      `Invoke-Expression $__pswCmd ` +
      `} catch { ` +
      `[Console]::Error.WriteLine($_.Exception.Message); ` +
      `$global:LASTEXITCODE = 1 ` +
      `}; ` +
      `try { [System.IO.Directory]::SetCurrentDirectory((Get-Location).ProviderPath) } catch {}; ` +
      `Write-Output "${DONE_MARKER}|$global:LASTEXITCODE|$((Get-Location).Path)"\n`;

    try {
      psProcess.stdin.write(singleLine);
      return { ok: true };
    } catch (err) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle("terminal:stop", async () => {
    stopPowerShellProcessOnly();
    startPowerShellSession();
    sendTerminalEvent({
      type: "stderr",
      text: "Выполнение прервано пользователем. Сессия PowerShell перезапущена.",
    });
    sendTerminalEvent({ type: "done", exitCode: 130, cwd: shellInfo.cwd });
  });

  ipcMain.handle("store:load", async () => {
    const configPath = getConfigPath();
    if (!fs.existsSync(configPath)) return null;
    try {
      const raw = fs.readFileSync(configPath, "utf8");
      return JSON.parse(raw);
    } catch (_) {
      return null;
    }
  });

  ipcMain.handle("store:save", async (_event, config) => {
    const configPath = getConfigPath();
    try {
      fs.writeFileSync(configPath, JSON.stringify(config, null, 2), "utf8");
    } catch (_) {
      // ignore write errors
    }
  });
});

app.on("window-all-closed", () => {
  stopPowerShellProcessOnly();
  if (process.platform !== "darwin") {
    app.quit();
  }
});
