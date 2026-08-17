export function registerWebMCPTools(normalizedServerUrl, token, navigatorOverride) {
  const nav = navigatorOverride || (typeof navigator !== 'undefined' ? navigator : null);
  if (!nav || !nav.modelContext) return null;

  const tools = [
    {
      name: 'get_aviary_status',
      description: 'Obtém o status em tempo real do aviário (temperatura, umidade, amônia).',
      inputSchema: {
        type: 'object',
        properties: {}
      },
      execute: async () => {
        try {
          const res = await fetch(`${normalizedServerUrl}/api/status`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {}
          });
          return res.ok ? await res.json() : { error: 'Failed to fetch status' };
        } catch (e) {
          return { error: 'Erro interno do servidor' };
        }
      }
    },
    {
      name: 'get_alerts',
      description: 'Retorna a lista de alertas ativos do galpão.',
      inputSchema: {
        type: 'object',
        properties: {}
      },
      execute: async () => {
        try {
          const res = await fetch(`${normalizedServerUrl}/api/alerts`, {
            headers: token ? { Authorization: `Bearer ${token}` } : {}
          });
          return res.ok ? await res.json() : { error: 'Failed to fetch alerts' };
        } catch (e) {
          return { error: 'Erro interno do servidor' };
        }
      }
    }
  ];

  const abortController = new AbortController();

  if (typeof nav.modelContext.provideContext === 'function') {
    try {
      nav.modelContext.provideContext({
        tools,
        signal: abortController.signal
      });
    } catch (err) {
      console.error('[WebMCP] provideContext error:', err);
    }
  } else if (typeof nav.modelContext.registerTool === 'function') {
    tools.forEach(tool => {
      try {
        nav.modelContext.registerTool(tool, { signal: abortController.signal });
      } catch (err) {
        console.error('[WebMCP] registerTool error:', err);
      }
    });
  }

  return abortController;
}
