/**
 * Voice Command Service for Qenergyz Platform
 * 
 * Provides voice recognition capabilities using Web Speech API
 * Supports simple voice commands for navigation and actions
 */

export interface VoiceCommand {
  command: string;
  intent: string;
  confidence: number;
  params?: Record<string, any>;
}

export interface VoiceServiceConfig {
  language: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
}

class VoiceService {
  private recognition: SpeechRecognition | null = null;
  private isListening = false;
  private config: VoiceServiceConfig = {
    language: 'en-US',
    continuous: false,
    interimResults: true,
    maxAlternatives: 1,
  };

  private commandPatterns = [
    {
      pattern: /show dashboard/i,
      intent: 'navigate',
      action: '/dashboard'
    },
    {
      pattern: /run risk report/i,
      intent: 'action',
      action: 'risk_report'
    },
    {
      pattern: /show trading/i,
      intent: 'navigate',
      action: '/trading'
    },
    {
      pattern: /open portfolio/i,
      intent: 'navigate',
      action: '/portfolio'
    },
    {
      pattern: /check compliance/i,
      intent: 'navigate',
      action: '/compliance'
    },
    {
      pattern: /help|commands/i,
      intent: 'help',
      action: 'show_commands'
    }
  ];

  constructor() {
    this.initializeSpeechRecognition();
  }

  /**
   * Initialize the Speech Recognition API
   */
  private initializeSpeechRecognition(): void {
    if (!this.isSpeechRecognitionSupported()) {
      console.warn('Speech Recognition is not supported in this browser');
      return;
    }

    // @ts-ignore - SpeechRecognition may have vendor prefixes
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    this.recognition = new SpeechRecognition();
    
    this.recognition.lang = this.config.language;
    this.recognition.continuous = this.config.continuous;
    this.recognition.interimResults = this.config.interimResults;
    this.recognition.maxAlternatives = this.config.maxAlternatives;
  }

  /**
   * Check if Speech Recognition is supported
   */
  public isSpeechRecognitionSupported(): boolean {
    // @ts-ignore - SpeechRecognition may have vendor prefixes
    return 'SpeechRecognition' in window || 'webkitSpeechRecognition' in window;
  }

  /**
   * Start listening for voice commands
   */
  public async startListening(): Promise<void> {
    if (!this.recognition) {
      throw new Error('Speech Recognition not initialized');
    }

    if (this.isListening) {
      console.log('Already listening');
      return;
    }

    return new Promise((resolve, reject) => {
      if (!this.recognition) return reject(new Error('Recognition not available'));

      this.recognition.onstart = () => {
        this.isListening = true;
        console.log('Voice recognition started');
        resolve();
      };

      this.recognition.onerror = (event) => {
        this.isListening = false;
        console.error('Speech recognition error:', event.error);
        reject(new Error(`Speech recognition error: ${event.error}`));
      };

      this.recognition.onend = () => {
        this.isListening = false;
        console.log('Voice recognition ended');
      };

      this.recognition.start();
    });
  }

  /**
   * Stop listening for voice commands
   */
  public stopListening(): void {
    if (this.recognition && this.isListening) {
      this.recognition.stop();
      this.isListening = false;
    }
  }

  /**
   * Process voice command and return structured result
   */
  public async processVoiceCommand(): Promise<VoiceCommand | null> {
    if (!this.recognition) {
      throw new Error('Speech Recognition not initialized');
    }

    return new Promise((resolve, reject) => {
      if (!this.recognition) return reject(new Error('Recognition not available'));

      this.recognition.onresult = (event) => {
        const result = event.results[event.results.length - 1];
        const transcript = result[0].transcript.trim();
        const confidence = result[0].confidence;

        console.log('Voice input:', transcript, 'Confidence:', confidence);

        const command = this.parseCommand(transcript, confidence);
        resolve(command);
      };

      this.recognition.onerror = (event) => {
        reject(new Error(`Speech recognition error: ${event.error}`));
      };
    });
  }

  /**
   * Parse voice command and match to known patterns
   */
  private parseCommand(transcript: string, confidence: number): VoiceCommand | null {
    for (const pattern of this.commandPatterns) {
      const match = transcript.match(pattern.pattern);
      if (match) {
        return {
          command: transcript,
          intent: pattern.intent,
          confidence,
          params: {
            action: pattern.action,
            match: match[0]
          }
        };
      }
    }

    return {
      command: transcript,
      intent: 'unknown',
      confidence,
      params: {}
    };
  }

  /**
   * Get available voice commands
   */
  public getAvailableCommands(): string[] {
    return [
      'Show dashboard',
      'Run risk report',
      'Show trading',
      'Open portfolio',
      'Check compliance',
      'Help'
    ];
  }

  /**
   * Update service configuration
   */
  public updateConfig(config: Partial<VoiceServiceConfig>): void {
    this.config = { ...this.config, ...config };
    if (this.recognition) {
      this.recognition.lang = this.config.language;
      this.recognition.continuous = this.config.continuous;
      this.recognition.interimResults = this.config.interimResults;
      this.recognition.maxAlternatives = this.config.maxAlternatives;
    }
  }

  /**
   * Get current listening status
   */
  public getIsListening(): boolean {
    return this.isListening;
  }
}

export const voiceService = new VoiceService();
export default VoiceService;