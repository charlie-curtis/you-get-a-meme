const { app, BrowserWindow } = require("electron");
const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const BACKEND_HOST = "127.0.0.1";
const BACKEND_PORT = process.env.YGAM_BACKEND_PORT || "8765";
const BACKEND_URL = `http://${BACKEND_HOST}:${BACKEND_PORT}`;

let backendProcess = null;

function projectRoot() {
  return path.join(__dirname, "..");
}

function pythonCandidates() {
  const root = projectRoot();
  const venvPython =
    process.platform === "win32"
      ? path.join(root, ".venv", "Scripts", "python.exe")
      : path.join(root, ".venv", "bin", "python");

  const candidates = [];
  if (fs.existsSync(venvPython)) {
    candidates.push(venvPython);
  }

  if (process.env.YGAM_PYTHON) {
    candidates.push(process.env.YGAM_PYTHON);
  }

  if (process.platform === "win32") {
    candidates.push("python.exe", "py.exe");
  } else {
    candidates.push("python3", "python");
  }

  return candidates;
}

function startBackend() {
  const root = projectRoot();
  const env = {
    ...process.env,
    PYTHONPATH: path.join(root, "src"),
    YGAM_BACKEND_HOST: BACKEND_HOST,
    YGAM_BACKEND_PORT: BACKEND_PORT
  };

  for (const candidate of pythonCandidates()) {
    try {
      backendProcess = spawn(
        candidate,
        ["-m", "you_get_a_meme.server"],
        {
          cwd: root,
          env,
          stdio: ["ignore", "pipe", "pipe"]
        }
      );

      backendProcess.stdout.on("data", (data) => {
        console.log(`[python] ${data.toString().trim()}`);
      });

      backendProcess.stderr.on("data", (data) => {
        console.error(`[python] ${data.toString().trim()}`);
      });

      backendProcess.on("exit", (code) => {
        if (code !== 0 && code !== null) {
          console.error(`Python backend exited with code ${code}`);
        }
        backendProcess = null;
      });

      backendProcess.on("error", () => {
        backendProcess = null;
      });

      return;
    } catch {
      backendProcess = null;
    }
  }
}

async function waitForBackend(timeoutMs = 8000) {
  const deadline = Date.now() + timeoutMs;

  while (Date.now() < deadline) {
    try {
      const response = await fetch(`${BACKEND_URL}/api/health`);
      if (response.ok) {
        return true;
      }
    } catch {
      // The backend is still starting.
    }

    await new Promise((resolve) => setTimeout(resolve, 200));
  }

  return false;
}

async function createWindow() {
  const window = new BrowserWindow({
    width: 1180,
    height: 780,
    minWidth: 920,
    minHeight: 640,
    title: "You Get a Meme",
    backgroundColor: "#f7f3ec",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      additionalArguments: [`--backend-url=${BACKEND_URL}`]
    }
  });

  await waitForBackend();
  await window.loadFile(path.join(__dirname, "..", "renderer", "index.html"));
}

app.whenReady().then(async () => {
  startBackend();
  await createWindow();

  app.on("activate", async () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      await createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

app.on("before-quit", () => {
  if (backendProcess) {
    backendProcess.kill();
    backendProcess = null;
  }
});
