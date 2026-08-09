import { registerWebMCPTools } from '../WebMCP';

describe('registerWebMCPTools', () => {
  let mockProvideContext;
  let mockRegisterTool;
  let mockNavigator;

  beforeEach(() => {
    mockProvideContext = jest.fn();
    mockRegisterTool = jest.fn();
    mockNavigator = {
      modelContext: {
        provideContext: mockProvideContext,
        registerTool: mockRegisterTool,
      },
    };
  });

  it('should return null if navigator or modelContext is not present', () => {
    expect(registerWebMCPTools('http://test', 'token', null)).toBeNull();
    expect(registerWebMCPTools('http://test', 'token', {})).toBeNull();
  });

  it('should register tools using provideContext if available', () => {
    const controller = registerWebMCPTools('http://test', 'token', mockNavigator);
    expect(controller).toBeDefined();
    expect(mockProvideContext).toHaveBeenCalledTimes(1);
    const args = mockProvideContext.mock.calls[0][0];
    expect(args.tools).toHaveLength(2);
    expect(args.tools[0].name).toBe('get_aviary_status');
    expect(args.tools[1].name).toBe('get_alerts');
    expect(args.signal).toBe(controller.signal);
  });

  it('should fallback to registerTool if provideContext is not available', () => {
    mockNavigator.modelContext.provideContext = undefined;
    const controller = registerWebMCPTools('http://test', 'token', mockNavigator);
    expect(controller).toBeDefined();
    expect(mockRegisterTool).toHaveBeenCalledTimes(2);
    expect(mockRegisterTool.mock.calls[0][0].name).toBe('get_aviary_status');
    expect(mockRegisterTool.mock.calls[1][0].name).toBe('get_alerts');
  });
});
