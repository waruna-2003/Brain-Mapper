const { app, BrowserWindow, ipcMain, utilityProcess } = require('electron');
const os = require('os');
const path = require('path');

app.commandLine.appendSwitch('disable-gpu-shader-disk-cache');
app.commandLine.appendSwitch('disable-http-cache');

const PORT = Number(process.env.PORT) || 3000;
const userDataPath = app.getPath('userData');
let mainWindow = null;
let serverProcess = null;

function getLocalIPv4Addresses() {
  const nets = os.networkInterfaces();
  const results = [];

  for (const name of Object.keys(nets)) {
    const lower = name.toLowerCase();
    const skip =
      lower.includes('vmware') ||
      lower.includes('virtual') ||
      lower.includes('hyper') ||
      lower.includes('vbox') ||
      lower.includes('loopback');
    if (skip) continue;

    for (const net of nets[name] || []) {
      if (net.family === 'IPv4' && !net.internal) {
        results.push({ name, address: net.address });
      }
    }
  }
  return results;
}

function startServer() {
  if (serverProcess) return;
  serverProcess = utilityProcess.fork(path.join(__dirname, 'server.js'), [], {
    serviceName: 'BrainMapper HTTP Server',
    stdio: 'inherit',
    env: {
      ...process.env,
      PORT: String(PORT),
      BRAINMAPPER_DATA_DIR: path.join(userDataPath, 'data')
    }
  });

  serverProcess.on('exit', () => {
    serverProcess = null;
  });
}

async function waitForServer(url, retries = 30) {
  for (let i = 0; i < retries; i++) {
    try {
      const res = await fetch(`${url}/api/health`);
      if (res.ok) return true;
    } catch (_) {
      // Server still booting
    }
    await new Promise((resolve) => setTimeout(resolve, 150));
  }
  return false;
}

async function createMainWindow() {
  startServer();
  const serverUrl = `http://127.0.0.1:${PORT}`;
  await waitForServer(serverUrl);

  mainWindow = new BrowserWindow({
    width: 1280,
    height: 900,
    minWidth: 900,
    minHeight: 680,
    title: 'BrainMapper',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadURL(serverUrl);
  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

ipcMain.handle('get-ips', () => getLocalIPv4Addresses());
ipcMain.handle('get-server-port', () => PORT);

app.whenReady().then(createMainWindow);

app.on('window-all-closed', () => {
  if (serverProcess) serverProcess.kill();
  app.quit();
});

app.on('before-quit', () => {
  if (serverProcess) serverProcess.kill();
});
