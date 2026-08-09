import re

with open("frontend/src/components/AdminPanel.jsx", "r") as f:
    content = f.read()

content = content.replace(
    "setActionLoading(userId);",
    "setActionLoading(`${userId}-approve`);",
    1
)

content = content.replace(
    "setActionLoading(userId);",
    "setActionLoading(`${userId}-suspend`);",
    1
)

content = content.replace(
    "setActionLoading(userId);",
    "setActionLoading(`${userId}-reactivate`);",
    1
)

content = content.replace(
    "setActionLoading(userId);",
    "setActionLoading(`${userId}-delete`);",
    1
)

content = content.replace(
    "const isActioning = actionLoading === u.id;",
    """const isActioning = actionLoading?.startsWith(`${u.id}-`);
                  const isApproving = actionLoading === `${u.id}-approve`;
                  const isSuspending = actionLoading === `${u.id}-suspend`;
                  const isReactivating = actionLoading === `${u.id}-reactivate`;
                  const isDeleting = actionLoading === `${u.id}-delete`;"""
)

content = content.replace(
    """<select
                              aria-label="Selecionar função do usuário\"""",
    """<label htmlFor={`role-select-${u.id}`} className="sr-only">Selecionar função do usuário</label>
                            <select"""
)

content = content.replace(
    "{isActioning ? <RefreshCw size={13} className=\"animate-spin\" /> : <UserCheck size={13} />}",
    "{isApproving ? <RefreshCw size={13} className=\"animate-spin\" /> : <UserCheck size={13} />}"
)

content = content.replace(
    "{isActioning ? 'Aprovando...' : 'Aprovar'}",
    "{isApproving ? 'Aprovando...' : 'Aprovar'}"
)


content = content.replace(
    "{isActioning ? <RefreshCw size={13} className=\"animate-spin\" /> : <ShieldCheck size={13} />}",
    "{isReactivating ? <RefreshCw size={13} className=\"animate-spin\" /> : <ShieldCheck size={13} />}"
)
content = content.replace(
    "{isActioning ? 'Reativando...' : 'Reativar'}",
    "{isReactivating ? 'Reativando...' : 'Reativar'}"
)


content = content.replace(
    "{isSuperadmin ? <ShieldOff size={13} /> : (isActioning ? <RefreshCw size={13} className=\"animate-spin\" /> : <UserX size={13} />)}",
    "{isSuperadmin ? <ShieldOff size={13} /> : (isSuspending ? <RefreshCw size={13} className=\"animate-spin\" /> : <UserX size={13} />)}"
)
content = content.replace(
    "{isSuperadmin ? 'Protegido' : (isActioning ? 'Suspendendo...' : 'Suspender')}",
    "{isSuperadmin ? 'Protegido' : (isSuspending ? 'Suspendendo...' : 'Suspender')}"
)


content = content.replace(
    "{isActioning ? <RefreshCw size={13} className=\"animate-spin\" /> : <UserX size={13} />}",
    "{isDeleting ? <RefreshCw size={13} className=\"animate-spin\" /> : <UserX size={13} />}"
)
content = content.replace(
    "{isActioning ? 'Excluindo...' : 'Excluir'}",
    "{isDeleting ? 'Excluindo...' : 'Excluir'}"
)

with open("frontend/src/components/AdminPanel.jsx", "w") as f:
    f.write(content)
