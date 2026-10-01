import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import LoginScreen from './LoginScreen.jsx';
import { supabase } from '../utils/supabaseClient';

vi.mock('../utils/supabaseClient', () => ({
  supabase: {
    auth: {
      signInWithPassword: vi.fn(),
      signInWithOAuth: vi.fn(),
    },
    from: vi.fn(() => ({
      select: vi.fn().mockReturnThis(),
      eq: vi.fn().mockReturnThis(),
      single: vi.fn(),
    })),
  },
}));

describe('LoginScreen Error Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const setupAndSubmit = async () => {
      render(<LoginScreen onBack={() => {}} onLogin={() => {}} />);
      fireEvent.change(screen.getByLabelText(/E-mail/i), { target: { value: 'test@example.com' } });
      const passwordInputs = screen.getAllByLabelText(/Senha/i);
      fireEvent.change(passwordInputs[0], { target: { value: 'password123' } });

      const form = screen.getByLabelText(/E-mail/i).closest('form');
      fireEvent.submit(form);
  };

  it('displays error message when login fails with invalid credentials', async () => {
    supabase.auth.signInWithPassword.mockResolvedValueOnce({
        data: { session: null, user: null },
        error: { message: 'invalid_credentials' },
    });

    await setupAndSubmit();

    await waitFor(() => {
      expect(screen.queryByText(/Credenciais inválidas/i)).not.toBeNull();
    });
  });

  it('displays error message for unconfirmed email', async () => {
    supabase.auth.signInWithPassword.mockResolvedValueOnce({
        data: { session: null, user: null },
        error: { message: 'Email not confirmed' },
    });

    await setupAndSubmit();

    await waitFor(() => {
      expect(screen.queryByText(/Confirme seu e-mail/i)).not.toBeNull();
    });
  });

  it('displays generic error message as fallback', async () => {
    supabase.auth.signInWithPassword.mockResolvedValueOnce({
        data: { session: null, user: null },
        error: { message: 'Some random API failure' },
    });

    await setupAndSubmit();

    await waitFor(() => {
      expect(screen.queryByText(/Some random API failure/i)).not.toBeNull();
    });
  });
});
