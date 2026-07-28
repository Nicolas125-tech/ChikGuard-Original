import { normalizeServerUrl } from '../../screens/ConfigScreen';

jest.mock('@react-native-async-storage/async-storage', () => ({
  setItem: jest.fn(),
  getItem: jest.fn(),
  removeItem: jest.fn(),
}));

describe('normalizeServerUrl', () => {
  it('should handle basic HTTP/HTTPS URLs', () => {
    expect(normalizeServerUrl('http://192.168.1.10')).toBe('http://192.168.1.10');
    expect(normalizeServerUrl('https://192.168.1.10')).toBe('https://192.168.1.10');
    expect(normalizeServerUrl('http://example.com')).toBe('http://example.com');
  });

  it('should assume http if no scheme is provided (except cloudflare)', () => {
    expect(normalizeServerUrl('192.168.1.10')).toBe('http://192.168.1.10');
    expect(normalizeServerUrl('example.com')).toBe('http://example.com');
  });

  it('should always use https for cloudflare quick tunnels', () => {
    expect(normalizeServerUrl('test.trycloudflare.com')).toBe('https://test.trycloudflare.com');
    expect(normalizeServerUrl('http://test.trycloudflare.com')).toBe('https://test.trycloudflare.com');
    expect(normalizeServerUrl('https://test.trycloudflare.com')).toBe('https://test.trycloudflare.com');
  });

  it('should remove trailing punctuation and paths', () => {
    expect(normalizeServerUrl('http://example.com/api')).toBe('http://example.com');
    expect(normalizeServerUrl('http://example.com/api/v1?test=1')).toBe('http://example.com');
    expect(normalizeServerUrl('http://example.com,')).toBe('http://example.com');
    expect(normalizeServerUrl('http://example.com;')).toBe('http://example.com');
    expect(normalizeServerUrl('http://example.com.')).toBe('http://example.com');
  });

  it('should handle empty or invalid inputs', () => {
    expect(normalizeServerUrl('')).toBe('');
    expect(normalizeServerUrl(null)).toBe('');
    expect(normalizeServerUrl(undefined)).toBe('');
    expect(normalizeServerUrl('   ')).toBe('');
  });

  it('should extract URL from a larger text', () => {
    expect(normalizeServerUrl('Please use https://example.com for access')).toBe('https://example.com');
    expect(normalizeServerUrl('My tunnel is test.trycloudflare.com today')).toBe('https://test.trycloudflare.com');
  });

  it('should fallback to regex parsing when URL is unavailable', () => {
    const originalURL = global.URL;
    global.URL = undefined;

    expect(normalizeServerUrl('192.168.1.10')).toBe('http://192.168.1.10');
    expect(normalizeServerUrl('https://example.com')).toBe('https://example.com');
    expect(normalizeServerUrl('test.trycloudflare.com')).toBe('https://test.trycloudflare.com');
    expect(normalizeServerUrl('http://example.com/test')).toBe('http://example.com');

    global.URL = originalURL;
  });
});
