import re

with open('frontend/src/App.jsx', 'r') as f:
    content = f.read()

# Make sure imports are there
if 'import io from' not in content:
    content = content.replace("import React, { useCallback, useEffect, useMemo, useState } from 'react';",
    "import React, { useCallback, useEffect, useMemo, useState } from 'react';\nimport io from 'socket.io-client';\nimport jsPDF from 'jspdf';\nimport 'jspdf-autotable';\nimport * as XLSX from 'xlsx';")

# Replace Dashboard Socket.io Logic
dash_old = '''function Dashboard({ token, role, username, serverIP, prefs, onSavePrefs, onSaveServer, onLogout }) {'''
dash_new = '''function Dashboard({ token, role, username, serverIP, prefs, onSavePrefs, onSaveServer, onLogout }) {
  const [telemetry, setTelemetry] = useState(null);

  useEffect(() => {
    const baseUrl = getBaseUrl(serverIP);
    const socket = io(baseUrl);
    socket.on('telemetry_update', (data) => {
       setTelemetry(data);
    });
    return () => socket.disconnect();
  }, [serverIP]);'''
if 'const [telemetry, setTelemetry] = useState(null);' not in content:
    content = content.replace(dash_old, dash_new)

# Replace Overview panel tags
content = content.replace("<OverviewPanel token={token} serverIP={serverIP} prefs={prefs} canControlDevices={canControlDevices} />",
"<OverviewPanel token={token} serverIP={serverIP} prefs={prefs} canControlDevices={canControlDevices} telemetry={telemetry} />")

# Update OverviewPanel Implementation
ov_old = '''function OverviewPanel({ token, serverIP, prefs, canControlDevices }) {'''
ov_new = '''function OverviewPanel({ token, serverIP, prefs, canControlDevices, telemetry }) {'''
content = content.replace(ov_old, ov_new)

ov_hook_old = '''  const fetchStatus = useCallback(async () => {'''
ov_hook_new = '''  const [hwStats, setHwStats] = useState(null);

  useEffect(() => {
    if (telemetry) {
      setDados({
        temperatura: telemetry.temperatura_atual,
        status: telemetry.status_atual,
        mensagem: telemetry.behavior?.message
      });
      setContagem(telemetry.contagem_aves);
      setDispositivos(telemetry.dispositivos);
      setSummary((prev) => ({ ...prev, comfort_score: telemetry.comfort_score }));
    }
  }, [telemetry]);

  const exportPDF = () => {
    try {
      const doc = new jsPDF();
      doc.text('Relatorio de Sensores e Metricas', 14, 20);
      const tableRows = [];
      historico.forEach(item => {
        tableRows.push([item.status, item.temp, item.hora, item.data]);
      });
      doc.autoTable({
        head: [["Status", "Temp (C)", "Hora", "Data"]],
        body: tableRows,
        startY: 30,
      });
      doc.save(`relatorio_historico_${new Date().toISOString()}.pdf`);
    } catch (e) { console.error('Error generating PDF', e); }
  };

  const exportExcel = () => {
    try {
      const ws = XLSX.utils.json_to_sheet(historico);
      const wb = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(wb, ws, "Historico");
      XLSX.writeFile(wb, `relatorio_historico_${new Date().toISOString()}.xlsx`);
    } catch (e) { console.error('Error generating Excel', e); }
  };

  const fetchStatus = useCallback(async () => {'''
if 'setHwStats(null)' not in content and 'exportPDF' not in content:
    content = content.replace(ov_hook_old, ov_hook_new)


# Fetch HW stats
fetch_old = '''    fetchStatus(); fetchHistory(); fetchDevices(); fetchCount(); fetchCarcassAndSummary();'''
fetch_new = '''    fetchStatus(); fetchHistory(); fetchDevices(); fetchCount(); fetchCarcassAndSummary();
    fetch(`${baseUrl}/api/hardware`).then(r => r.json()).then(d => setHwStats(d)).catch(e => {});'''
content = content.replace(fetch_old, fetch_new)


# History card Export Buttons
hist_card_old = '''        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <h3 className="text-slate-400 text-xs font-bold uppercase mb-4 flex items-center gap-2 tracking-widest"><LayoutDashboard size={14} /> Historico</h3>'''
hist_card_new = '''        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-slate-400 text-xs font-bold uppercase flex items-center gap-2 tracking-widest"><LayoutDashboard size={14} /> Historico</h3>
            <div className="flex gap-2">
              <button onClick={exportPDF} className="bg-red-600 hover:bg-red-500 text-white text-xs px-2 py-1 rounded">PDF</button>
              <button onClick={exportExcel} className="bg-emerald-600 hover:bg-emerald-500 text-white text-xs px-2 py-1 rounded">Excel</button>
            </div>
          </div>'''
if 'exportPDF' in content and 'onClick={exportPDF}' not in content:
    content = content.replace(hist_card_old, hist_card_new)


# Hardware Stats Panel
hw_panel = '''
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-4">
          <div className="text-xs uppercase tracking-wider text-slate-400 mb-1">Hardware (Mini PC)</div>
          {hwStats ? (
             <div className="text-sm space-y-2 mt-2">
                <div className="flex justify-between"><span>CPU</span> <span>{hwStats.cpu_percent}%</span></div>
                <div className="w-full bg-slate-800 h-2 rounded"><div className="bg-emerald-500 h-2 rounded" style={{width: `${hwStats.cpu_percent}%`}}></div></div>
                <div className="flex justify-between mt-2"><span>RAM</span> <span>{hwStats.ram_percent}%</span></div>
                <div className="w-full bg-slate-800 h-2 rounded"><div className="bg-blue-500 h-2 rounded" style={{width: `${hwStats.ram_percent}%`}}></div></div>
                <div className="flex justify-between mt-2"><span>Disco</span> <span>{hwStats.disk_percent}%</span></div>
             </div>
          ) : <div className="text-slate-500 text-sm">Carregando hardware...</div>}
        </div>
'''
if 'Hardware (Mini PC)' not in content:
    content = content.replace('</div>\n\n      <div className="lg:col-span-2">', hw_panel + '      </div>\n\n      <div className="lg:col-span-2">')

with open('frontend/src/App.jsx', 'w') as f:
    f.write(content)
