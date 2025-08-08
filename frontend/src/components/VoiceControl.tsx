import React, { useState, useEffect } from 'react';
import { voiceService, VoiceCommand } from '../services/voiceService';
import { useNavigate } from 'react-router-dom';

interface VoiceControlProps {
  className?: string;
}

export const VoiceControl: React.FC<VoiceControlProps> = ({ className = '' }) => {
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(false);
  const [lastCommand, setLastCommand] = useState<string>('');
  const [error, setError] = useState<string>('');
  const navigate = useNavigate();

  useEffect(() => {
    setIsSupported(voiceService.isSpeechRecognitionSupported());
  }, []);

  const handleStartListening = async () => {
    try {
      setError('');
      await voiceService.startListening();
      setIsListening(true);

      // Process the voice command
      const command = await voiceService.processVoiceCommand();
      if (command) {
        handleVoiceCommand(command);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
      setIsListening(false);
    }
  };

  const handleStopListening = () => {
    voiceService.stopListening();
    setIsListening(false);
  };

  const handleVoiceCommand = (command: VoiceCommand) => {
    setLastCommand(command.command);
    setIsListening(false);

    // Handle different intents
    switch (command.intent) {
      case 'navigate':
        if (command.params?.action) {
          navigate(command.params.action);
        }
        break;
      case 'action':
        if (command.params?.action === 'risk_report') {
          // Trigger risk report generation
          console.log('Triggering risk report generation...');
          // You would integrate with your risk service here
        }
        break;
      case 'help':
        showAvailableCommands();
        break;
      default:
        console.log('Unknown command:', command.command);
        setError(`Command not recognized: "${command.command}"`);
    }
  };

  const showAvailableCommands = () => {
    const commands = voiceService.getAvailableCommands();
    alert(`Available voice commands:\n${commands.join('\n')}`);
  };

  if (!isSupported) {
    return (
      <div className={`voice-control-unsupported ${className}`}>
        <p className="text-sm text-gray-500">
          Voice commands not supported in this browser
        </p>
      </div>
    );
  }

  return (
    <div className={`voice-control ${className}`}>
      <div className="flex items-center space-x-2">
        <button
          onClick={isListening ? handleStopListening : handleStartListening}
          className={`
            px-3 py-2 rounded-lg text-sm font-medium transition-colors
            ${isListening 
              ? 'bg-red-500 hover:bg-red-600 text-white' 
              : 'bg-blue-500 hover:bg-blue-600 text-white'
            }
          `}
          disabled={!isSupported}
        >
          {isListening ? (
            <>
              <span className="animate-pulse">🎤</span> Stop
            </>
          ) : (
            <>
              🎤 Voice
            </>
          )}
        </button>

        <button
          onClick={showAvailableCommands}
          className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700"
          title="Show available commands"
        >
          ?
        </button>
      </div>

      {isListening && (
        <div className="mt-2 p-2 bg-blue-50 rounded text-sm">
          <div className="flex items-center">
            <span className="animate-pulse text-red-500 mr-2">●</span>
            Listening...
          </div>
        </div>
      )}

      {lastCommand && (
        <div className="mt-2 p-2 bg-green-50 rounded text-sm">
          <span className="text-green-700">Last command: "{lastCommand}"</span>
        </div>
      )}

      {error && (
        <div className="mt-2 p-2 bg-red-50 rounded text-sm">
          <span className="text-red-700">{error}</span>
        </div>
      )}
    </div>
  );
};

export default VoiceControl;