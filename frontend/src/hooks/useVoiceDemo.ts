import { voiceService, VoiceCommand } from '../services/voiceService';

/**
 * Voice Command Demo Hook
 * Provides demo functionality for voice commands
 */
export const useVoiceDemo = () => {
  const runDemo = async () => {
    if (!voiceService.isSpeechRecognitionSupported()) {
      alert('Voice commands are not supported in this browser. Please use Chrome or a WebKit-based browser.');
      return;
    }

    try {
      // Demo flow
      alert('Voice Command Demo\n\nClick OK to start listening for voice commands.\n\nTry saying:\n- "Show dashboard"\n- "Run risk report"\n- "Open portfolio"\n- "Help"');
      
      await voiceService.startListening();
      console.log('Demo: Started listening for voice commands');

      // Process command
      const command = await voiceService.processVoiceCommand();
      
      if (command) {
        handleDemoCommand(command);
      }
    } catch (error) {
      console.error('Voice demo error:', error);
      alert(`Voice command error: ${error instanceof Error ? error.message : 'Unknown error'}`);
    }
  };

  const handleDemoCommand = (command: VoiceCommand) => {
    const message = `
Voice Command Detected!

Command: "${command.command}"
Intent: ${command.intent}
Confidence: ${(command.confidence * 100).toFixed(1)}%
Action: ${command.params?.action || 'None'}

${getIntentDescription(command.intent)}
    `;

    alert(message);

    // Simulate the action
    console.log('Demo command processed:', command);
  };

  const getIntentDescription = (intent: string): string => {
    switch (intent) {
      case 'navigate':
        return 'This would navigate to the requested page.';
      case 'action':
        return 'This would execute the requested action.';
      case 'help':
        return 'This would show available commands.';
      default:
        return 'This command was not recognized. Try one of the suggested commands.';
    }
  };

  const showCommands = () => {
    const commands = voiceService.getAvailableCommands();
    alert(`Available Voice Commands:\n\n${commands.map(cmd => `• ${cmd}`).join('\n')}`);
  };

  return {
    runDemo,
    showCommands,
    isSupported: voiceService.isSpeechRecognitionSupported()
  };
};