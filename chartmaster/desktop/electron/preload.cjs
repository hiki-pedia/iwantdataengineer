const { contextBridge } = require("electron");

contextBridge.exposeInMainWorld("chartmasterDesktop", {
  platform: process.platform
});
