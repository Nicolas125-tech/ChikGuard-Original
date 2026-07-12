import assert from 'node:assert';
import { describe, it, beforeEach, mock } from 'node:test';
import esmock from 'esmock';

describe('authService', () => {
  let authService;
  let mockSupabase;

  beforeEach(async () => {
    mockSupabase = {
      auth: {
        signInWithPassword: mock.fn(),
        signOut: mock.fn(),
        signUp: mock.fn(),
        getSession: mock.fn()
      },
      from: mock.fn()
    };

    const module = await esmock('./authService.js', {
      './supabaseClient.js': {
        supabase: mockSupabase,
        isSupabaseConfigured: true
      }
    });
    authService = module.authService;
  });

  describe('hasAccess', () => {
    it('correctly checks roles', () => {
      assert.strictEqual(authService.hasAccess('admin', ['viewer']), true);
      assert.strictEqual(authService.hasAccess('superadmin', ['operator']), true);
      assert.strictEqual(authService.hasAccess('viewer', ['viewer', 'operator']), true);
      assert.strictEqual(authService.hasAccess('viewer', ['operator']), false);
      assert.strictEqual(authService.hasAccess(null, ['viewer']), false);
    });
  });

  describe('login', () => {
    it('should login and return session and profile', async () => {
      mockSupabase.auth.signInWithPassword.mock.mockImplementationOnce(async () => {
        return { data: { session: { user: { id: 'user1' } } }, error: null };
      });

      const mockSingle = mock.fn(async () => ({ data: { role: 'admin', status: 'ACTIVE', tenant_id: 1, full_name: 'Admin', email: 'admin@test.com' }, error: null }));
      mockSupabase.from.mock.mockImplementationOnce(() => ({
        select: () => ({
          eq: () => ({ single: mockSingle })
        })
      }));

      const result = await authService.login('admin@test.com', 'password123');

      assert.strictEqual(mockSupabase.auth.signInWithPassword.mock.calls.length, 1);
      assert.deepStrictEqual(result.session.user.id, 'user1');
      assert.strictEqual(result.profile.role, 'admin');
    });

    it('should throw an error if signInWithPassword fails', async () => {
      mockSupabase.auth.signInWithPassword.mock.mockImplementationOnce(async () => ({ data: null, error: new Error('Invalid credentials') }));

      await assert.rejects(
        authService.login('admin@test.com', 'wrong_password'),
        { message: 'Invalid credentials' }
      );
    });

    it('should throw an error if session is empty', async () => {
      mockSupabase.auth.signInWithPassword.mock.mockImplementationOnce(async () => ({ data: { session: null }, error: null }));

      await assert.rejects(
        authService.login('admin@test.com', 'password'),
        { message: 'Não foi possível estabelecer uma sessão de login.' }
      );
    });
  });

  describe('logout', () => {
    it('should call auth.signOut', async () => {
      mockSupabase.auth.signOut.mock.mockImplementationOnce(async () => ({ error: null }));
      await authService.logout();
      assert.strictEqual(mockSupabase.auth.signOut.mock.calls.length, 1);
    });
  });

  describe('signUp', () => {
    it('should create a user account', async () => {
      mockSupabase.auth.signUp.mock.mockImplementationOnce(async () => ({ data: { user: { id: 'newUser' } }, error: null }));

      const result = await authService.signUp('new@test.com', 'pass123', { fullName: 'New User', age: '30' });

      assert.strictEqual(mockSupabase.auth.signUp.mock.calls.length, 1);
      assert.deepStrictEqual(mockSupabase.auth.signUp.mock.calls[0].arguments[0].email, 'new@test.com');
      assert.deepStrictEqual(mockSupabase.auth.signUp.mock.calls[0].arguments[0].options.data.full_name, 'New User');
      assert.strictEqual(mockSupabase.auth.signUp.mock.calls[0].arguments[0].options.data.age, 30);
      assert.deepStrictEqual(result.user.id, 'newUser');
    });

    it('should throw error on signUp failure', async () => {
      mockSupabase.auth.signUp.mock.mockImplementationOnce(async () => ({ data: null, error: new Error('Registration failed') }));

      await assert.rejects(
        authService.signUp('fail@test.com', 'pass'),
        { message: 'Registration failed' }
      );
    });
  });

  describe('getUserProfile', () => {
    it('should fetch user profile', async () => {
      const mockSingle = mock.fn(async () => ({ data: { role: 'admin' }, error: null }));
      mockSupabase.from.mock.mockImplementationOnce(() => ({
        select: () => ({
          eq: () => ({ single: mockSingle })
        })
      }));

      const result = await authService.getUserProfile('user1');

      assert.strictEqual(mockSingle.mock.calls.length, 1);
      assert.strictEqual(result.role, 'admin');
    });

    it('should return default profile on error', async () => {
      const mockSingle = mock.fn(async () => ({ data: null, error: new Error('DB Error') }));
      mockSupabase.from.mock.mockImplementationOnce(() => ({
        select: () => ({
          eq: () => ({ single: mockSingle })
        })
      }));

      const result = await authService.getUserProfile('user1');
      assert.deepStrictEqual(result, { role: 'viewer', status: 'PENDING', tenant_id: 1 });
    });
  });

  describe('getSession', () => {
    it('should return session data', async () => {
      mockSupabase.auth.getSession.mock.mockImplementationOnce(async () => ({ data: { session: { user: { id: 'user1' } } }, error: null }));

      const result = await authService.getSession();

      assert.strictEqual(mockSupabase.auth.getSession.mock.calls.length, 1);
      assert.deepStrictEqual(result.session.user.id, 'user1');
    });

    it('should return null session on error', async () => {
      mockSupabase.auth.getSession.mock.mockImplementationOnce(async () => ({ data: null, error: new Error('Session error') }));

      const result = await authService.getSession();
      assert.deepStrictEqual(result, { session: null });
    });
  });
});
