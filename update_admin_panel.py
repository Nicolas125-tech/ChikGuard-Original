import re

file_path = 'frontend/src/components/AdminPanel.jsx'
with open(file_path, 'r') as f:
    content = f.read()

content = content.replace(
    '<button aria-label="Editar perfil do utilizador" onClick={onEdit} disabled={isAnyActioning}',
    '<button aria-label={`Editar perfil de ${u.full_name || u.email}`} onClick={onEdit} disabled={isAnyActioning}'
)

content = content.replace(
    '<button disabled={isAnyActioning} onClick={() => onApprove(approveRole)}\n                className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500',
    '<button aria-label={`Aprovar utilizador ${u.full_name || u.email}`} disabled={isAnyActioning} onClick={() => onApprove(approveRole)}\n                className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500'
)

content = content.replace(
    '<button aria-label="Rejeitar utilizador" disabled={isAnyActioning} onClick={onReject}',
    '<button aria-label={`Rejeitar utilizador ${u.full_name || u.email}`} disabled={isAnyActioning} onClick={onReject}'
)

content = content.replace(
    '<button disabled={isAnyActioning} onClick={onReactivate}\n                className="flex items-center gap-1.5 bg-emerald-600/20 hover:bg-emerald-600/40',
    '<button aria-label={`Reativar utilizador ${u.full_name || u.email}`} disabled={isAnyActioning} onClick={onReactivate}\n                className="flex items-center gap-1.5 bg-emerald-600/20 hover:bg-emerald-600/40'
)

content = content.replace(
    '<button aria-label="Suspender utilizador" disabled={isAnyActioning} onClick={onSuspend}',
    '<button aria-label={`Suspender utilizador ${u.full_name || u.email}`} disabled={isAnyActioning} onClick={onSuspend}'
)

with open(file_path, 'w') as f:
    f.write(content)
