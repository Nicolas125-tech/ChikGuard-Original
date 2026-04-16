import { create } from 'zustand';

export const useAppStore = create((set) => ({
  status: { temperatura: 0, status: 'INICIANDO' },
  devices: { ventilacao: false, aquecedor: false, umidificador: false, alimentador: false },
  count: 0,
  history: [],
  alerts: [],
  systemInfo: null,

  setStatus: (status) => set({ status }),
  setDevices: (devices) => set({ devices }),
  setCount: (count) => set({ count }),
  setHistory: (history) => set({ history }),
  setAlerts: (alerts) => set({ alerts }),
  setSystemInfo: (systemInfo) => set({ systemInfo }),

  updateTelemetry: (data) => set((state) => ({
    status: data.status || state.status,
    devices: data.devices || state.devices,
    count: data.count !== undefined ? data.count : state.count,
  })),
}));
