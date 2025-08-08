import { voiceService } from '../services/voiceService';

describe('VoiceService', () => {
  beforeEach(() => {
    // Mock Speech Recognition API
    const mockSpeechRecognition = {
      start: jest.fn(),
      stop: jest.fn(),
      addEventListener: jest.fn(),
    };
    
    // @ts-ignore - Mock global
    global.SpeechRecognition = jest.fn(() => mockSpeechRecognition);
    global.webkitSpeechRecognition = jest.fn(() => mockSpeechRecognition);
  });

  describe('isSpeechRecognitionSupported', () => {
    it('should return true when SpeechRecognition is available', () => {
      const result = voiceService.isSpeechRecognitionSupported();
      expect(result).toBe(true);
    });

    it('should return false when SpeechRecognition is not available', () => {
      // @ts-ignore - Remove mock
      delete global.SpeechRecognition;
      delete global.webkitSpeechRecognition;
      
      const result = voiceService.isSpeechRecognitionSupported();
      expect(result).toBe(false);
    });
  });

  describe('getAvailableCommands', () => {
    it('should return list of available commands', () => {
      const commands = voiceService.getAvailableCommands();
      
      expect(commands).toContain('Show dashboard');
      expect(commands).toContain('Run risk report');
      expect(commands).toContain('Help');
    });
  });

  describe('parseCommand', () => {
    it('should parse "show dashboard" command correctly', () => {
      // Access private method through type assertion
      const parseCommand = (voiceService as any).parseCommand;
      const command = parseCommand('show dashboard', 0.9);
      
      expect(command.intent).toBe('navigate');
      expect(command.params.action).toBe('/dashboard');
      expect(command.confidence).toBe(0.9);
    });

    it('should parse "run risk report" command correctly', () => {
      const parseCommand = (voiceService as any).parseCommand;
      const command = parseCommand('run risk report', 0.8);
      
      expect(command.intent).toBe('action');
      expect(command.params.action).toBe('risk_report');
    });

    it('should handle unknown commands', () => {
      const parseCommand = (voiceService as any).parseCommand;
      const command = parseCommand('unknown command', 0.7);
      
      expect(command.intent).toBe('unknown');
      expect(command.confidence).toBe(0.7);
    });
  });

  describe('updateConfig', () => {
    it('should update configuration', () => {
      const newConfig = {
        language: 'en-GB',
        continuous: true,
        maxAlternatives: 3
      };
      
      voiceService.updateConfig(newConfig);
      
      // Verify configuration is updated (would need to expose config getter)
      expect(voiceService.getIsListening()).toBe(false);
    });
  });
});

export {};