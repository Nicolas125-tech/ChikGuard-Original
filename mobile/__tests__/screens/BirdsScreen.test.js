import React from 'react';
import { render, waitFor, fireEvent } from '@testing-library/react-native';
import BirdsScreen from '../../screens/BirdsScreen';

// Mock Lucide icons
jest.mock('lucide-react-native', () => ({
  Bird: 'Bird',
  Activity: 'Activity'
}));

// Mock fetch
global.fetch = jest.fn();

describe('BirdsScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const defaultProps = {
    serverUrl: 'http://example.com',
    token: 'test-token',
    enviarComandoVoz: jest.fn(),
    canControlDevices: true
  };

  it('renders loading indicator initially', () => {
    // Keep fetch pending to see the loading state
    global.fetch.mockImplementation(() => new Promise(() => {}));

    const { root, queryByText } = render(<BirdsScreen {...defaultProps} />);

    // We expect loading state while fetch is pending
    expect(root.findAllByType('ActivityIndicator').length).toBeGreaterThan(0);
    expect(queryByText('Aves Vistas')).toBeNull();
  });

  it('displays visitor warning when canControlDevices is false', async () => {
    global.fetch.mockResolvedValue({
      ok: true,
      json: async () => ({ count: 0, items: [] })
    });

    const { getByText, queryAllByText } = render(<BirdsScreen {...defaultProps} canControlDevices={false} />);

    await waitFor(() => {
      expect(getByText('Perfil visitante: controles desativados.')).toBeTruthy();
    });
  });

  it('loads and displays live birds and registry data', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/birds/live')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            count: 1,
            items: [{ bird_uid: 'live-1', confidence: 0.95, track_id: 10 }]
          })
        });
      }
      if (url.includes('/api/birds/registry')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            count: 2,
            items: [
              { bird_uid: 'reg-1', sightings: 5, max_confidence: 0.99, last_seen: '2023-01-01' },
              { bird_uid: 'reg-2', sightings: 2, max_confidence: 0.85, last_seen: '2023-01-02' }
            ]
          })
        });
      }
      return Promise.reject(new Error('not mocked'));
    });

    const { getByText, getAllByText } = render(<BirdsScreen {...defaultProps} />);

    await waitFor(() => {
      expect(getByText('Aves Vistas')).toBeTruthy();
      expect(getByText('1')).toBeTruthy(); // live count
      expect(getByText('2')).toBeTruthy(); // registry count
      expect(getByText('ID live-1')).toBeTruthy();
      expect(getByText('ID reg-1')).toBeTruthy();
      expect(getByText('ID reg-2')).toBeTruthy();
    });
  });

  it('loads and displays bird path when a bird is selected', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/birds/live')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            count: 1,
            items: [{ bird_uid: 'bird-to-select', confidence: 0.95, track_id: 10 }]
          })
        });
      }
      if (url.includes('/api/birds/registry')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ count: 0, items: [] })
        });
      }
      if (url.includes('/api/birds/path/bird-to-select')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            items: [
              { id: 1, x: 100, y: 200, timestamp: '12:00:00' },
              { id: 2, x: 105, y: 205, timestamp: '12:00:01' }
            ]
          })
        });
      }
      return Promise.reject(new Error('not mocked: ' + url));
    });

    const { getByText } = render(<BirdsScreen {...defaultProps} />);

    await waitFor(() => {
      expect(getByText('ID bird-to-select')).toBeTruthy();
    });

    fireEvent.press(getByText('ID bird-to-select'));

    await waitFor(() => {
      expect(getByText('(100, 200)')).toBeTruthy();
      expect(getByText('(105, 205)')).toBeTruthy();
    });
  });
});

describe('BirdsScreen Error Handling', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  const defaultProps = {
    serverUrl: 'http://example.com',
    token: 'test-token',
    enviarComandoVoz: jest.fn(),
    canControlDevices: true
  };

  it('handles error when loading birds gracefully', async () => {
    const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    global.fetch.mockRejectedValue(new Error('Network error'));

    const { getByText, queryAllByType } = render(<BirdsScreen {...defaultProps} />);

    await waitFor(() => {
      expect(getByText('Aves Vistas')).toBeTruthy();
      expect(getByText('Nenhuma ave visível.')).toBeTruthy();
      expect(getByText('Sem aves registradas.')).toBeTruthy();
    });

    expect(consoleWarnSpy).toHaveBeenCalledWith('Error loading birds:', expect.any(Error));
    consoleWarnSpy.mockRestore();
  });

  it('handles error when loading path gracefully', async () => {
    const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/birds/live')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({
            count: 1,
            items: [{ bird_uid: 'bird-to-select', confidence: 0.95, track_id: 10 }]
          })
        });
      }
      if (url.includes('/api/birds/registry')) {
        return Promise.resolve({
          ok: true,
          json: async () => ({ count: 0, items: [] })
        });
      }
      if (url.includes('/api/birds/path/bird-to-select')) {
        return Promise.reject(new Error('Failed to load path'));
      }
      return Promise.reject(new Error('not mocked'));
    });

    const { getByText } = render(<BirdsScreen {...defaultProps} />);

    await waitFor(() => {
      expect(getByText('ID bird-to-select')).toBeTruthy();
    });

    fireEvent.press(getByText('ID bird-to-select'));

    await waitFor(() => {
      expect(getByText('Sem trilha para o ID bird-to-select.')).toBeTruthy();
    });

    expect(consoleWarnSpy).toHaveBeenCalledWith('Error loading path:', expect.any(Error));
    consoleWarnSpy.mockRestore();
  });
});
