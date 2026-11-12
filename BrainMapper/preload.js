const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  getIPs: () => ipcRenderer.invoke('get-ips'),
  getServerPort: () => ipcRenderer.invoke('get-server-port')
});
