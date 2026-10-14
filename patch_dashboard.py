import re

with open('frontend/src/pages/Dashboard.jsx', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace "Close mobile menu"
content = content.replace(
    'aria-label="Close mobile menu" onClick={() => setMobileMenuOpen(false)} className="p-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors"',
    'aria-label="Fechar menu" onClick={() => setMobileMenuOpen(false)} className="p-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none"'
)
content = content.replace('<X size={20} />', '<X size={20} aria-hidden="true" />')

# Replace "Open mobile menu"
content = re.sub(
    r'aria-label="Open mobile menu"[ \n]*onClick=\{\(\) => setMobileMenuOpen\(true\)\}[ \n]*className="md:hidden p-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors border border-slate-800"',
    'aria-label="Abrir menu"\n          onClick={() => setMobileMenuOpen(true)}\n          className="md:hidden p-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors border border-slate-800 focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none"',
    content
)

content = content.replace('<Menu size={20} />', '<Menu size={20} aria-hidden="true" />')

# Replace "View alerts"
content = re.sub(
    r'aria-label="View alerts"[ \n]*onClick=\{\(\) => handleTabChange\(\'alerts\'\)\}[ \n]*className="relative p-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors border border-slate-800/50 hover:border-slate-700"',
    'aria-label="Ver alertas"\n          onClick={() => handleTabChange(\'alerts\')}\n          className="relative p-2 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors border border-slate-800/50 hover:border-slate-700 focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none"',
    content
)

content = content.replace('<Bell size={18} />', '<Bell size={18} aria-hidden="true" />')

# Replace "Logout"
content = content.replace(
    'aria-label="Logout" onClick={onLogout} className="md:hidden p-2 border border-slate-800 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors"',
    'aria-label="Sair" onClick={onLogout} className="md:hidden p-2 border border-slate-800 rounded-lg text-slate-400 hover:bg-slate-800 transition-colors focus-visible:ring-2 focus-visible:ring-emerald-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900 focus:outline-none"'
)
content = content.replace('<LogOut size={18} />', '<LogOut size={18} aria-hidden="true" />')

with open('frontend/src/pages/Dashboard.jsx', 'w', encoding='utf-8') as f:
    f.write(content)
