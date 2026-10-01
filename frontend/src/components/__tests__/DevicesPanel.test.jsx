import { describe, it, vi, beforeEach, afterEach, expect } from 'vitest';
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import DevicesPanel from '../DevicesPanel.jsx';

describe('DevicesPanel Fetch Error', () => {
  let originalFetch;
  let originalConsoleError;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
    originalConsoleError = console.error;

    // Mock console.error to avoid test output noise
    console.error = vi.fn();

    // Mock fetch to simulate failure
    globalThis.fetch = vi.fn(() => Promise.reject(new Error('Network Error')));
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    console.error = originalConsoleError;
    vi.restoreAllMocks();
  });

  it('should render QueryErrorState when device fetch fails', async () => {
    render(<DevicesPanel token="dummy" serverIP="localhost" />);

    // Wait for the QueryErrorState to be rendered, identified by its text
    await waitFor(() => {
      const errorHeading = screen.getByText('Erro de Conexão ou Consulta');
      expect(errorHeading).toBeDefined();
    });

    // Verify console.error was called
    expect(console.error).toHaveBeenCalled();
  });
});
