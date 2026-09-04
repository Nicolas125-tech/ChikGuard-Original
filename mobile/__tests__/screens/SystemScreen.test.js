import React from 'react';
import { render, waitFor, screen, act } from '@testing-library/react-native';
import SystemScreen from '../../screens/SystemScreen';

global.fetch = jest.fn();

describe('SystemScreen', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  const mockSummary = {
    media_temperatura: 25.5,
    contagem_aves: 100,
    total_aves_vistas: 500,
    total_alertas: 5,
  };

  const mockSystemInfo = {
    camera_thread_alive: true,
    yolo_loaded: true,
    uptime_seconds: 3665, // 1h 1m
  };

  it('renders loading state initially', async () => {
    global.fetch.mockResolvedValue(new Promise(resolve => {})); // pending promise

    const { getByTestId } = render(<SystemScreen serverUrl="http://test" token="token" />);

    // In RNTL, we can use testID if we added it, or we can check what's rendered
    // Since there's no testID, let's just make sure it doesn't render "Sistema" yet
    expect(screen.queryByText('Sistema')).toBeNull();
  });

  it('fetches data and renders correctly', async () => {
    global.fetch.mockImplementation((url) => {
      if (url.includes('/api/summary')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSummary)
        });
      }
      if (url.includes('/api/system-info')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockSystemInfo)
        });
      }
      return Promise.reject(new Error('not found'));
    });

    render(<SystemScreen serverUrl="http://test" token="token" />);

    // Wait for the fetch promises to resolve
    await waitFor(() => {
      expect(screen.getByText('Sistema')).toBeTruthy();
    });

    expect(screen.getByText('ATIVA')).toBeTruthy(); // camera_thread_alive
    expect(screen.getByText('PRONTO')).toBeTruthy(); // yolo_loaded
    expect(screen.getByText('1h 1m')).toBeTruthy(); // uptime
    expect(screen.getByText('25.5°C')).toBeTruthy(); // media_temperatura
    expect(screen.getByText('100')).toBeTruthy(); // contagem_aves
    expect(screen.getByText('500')).toBeTruthy(); // total_aves_vistas
    expect(screen.getByText('5')).toBeTruthy(); // total_alertas
  });

  it('handles empty server URL without fetching', async () => {
    render(<SystemScreen serverUrl="" token="token" />);

    await waitFor(() => {
      expect(screen.getByText('Sistema')).toBeTruthy();
    });

    expect(global.fetch).not.toHaveBeenCalled();
    const dashes = screen.getAllByText('--');
    expect(dashes.length).toBeGreaterThan(0); // Should show default values
  });

  it('handles fetch errors gracefully', async () => {
    global.fetch.mockRejectedValue(new Error('Network error'));

    const consoleSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});

    render(<SystemScreen serverUrl="http://test" token="token" />);

    await waitFor(() => {
      expect(screen.getByText('Sistema')).toBeTruthy();
    });

    expect(consoleSpy).toHaveBeenCalledWith('Error loading system data:', expect.any(Error));
    expect(screen.getAllByText('--').length).toBeGreaterThan(0);

    consoleSpy.mockRestore();
  });

  it('cleans up interval on unmount', () => {
    render(<SystemScreen serverUrl="http://test" token="token" />);

    const clearIntervalSpy = jest.spyOn(global, 'clearInterval');

    screen.unmount();

    expect(clearIntervalSpy).toHaveBeenCalled();
  });
});
