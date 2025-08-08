# Voice Commands Documentation

## Overview

The Qenergyz platform includes voice command functionality to enhance user productivity and accessibility. Users can navigate the application and trigger actions using natural language voice commands.

## Features

### Supported Voice Commands

| Command | Intent | Action | Example |
|---------|--------|---------|---------|
| "Show dashboard" | Navigate | Go to dashboard page | "Show dashboard" |
| "Run risk report" | Action | Generate risk analysis | "Run risk report" |
| "Show trading" | Navigate | Go to trading module | "Show trading" |
| "Open portfolio" | Navigate | Go to portfolio view | "Open portfolio" |
| "Check compliance" | Navigate | Go to compliance module | "Check compliance" |
| "Help" | Help | Show available commands | "Help" or "Commands" |

### Browser Compatibility

- **Chrome**: Full support
- **Safari**: Full support (macOS only)
- **Firefox**: Partial support
- **Edge**: Full support
- **Mobile browsers**: Limited support

## Implementation

### Voice Service Architecture

```typescript
VoiceService
├── Speech Recognition API integration
├── Command pattern matching
├── Intent classification
├── Error handling and fallbacks
└── Configuration management
```

### Key Components

1. **VoiceService** (`src/services/voiceService.ts`)
   - Core voice recognition functionality
   - Command parsing and intent matching
   - Browser compatibility detection

2. **VoiceControl** (`src/components/VoiceControl.tsx`)
   - React component for voice interaction UI
   - Visual feedback for listening state
   - Error display and command history

3. **useVoiceDemo** (`src/hooks/useVoiceDemo.ts`)
   - Demo functionality for testing voice commands
   - Command simulation and validation

## Usage

### Basic Usage

```typescript
import { voiceService } from './services/voiceService';

// Check if voice commands are supported
if (voiceService.isSpeechRecognitionSupported()) {
  // Start listening
  await voiceService.startListening();
  
  // Process command
  const command = await voiceService.processVoiceCommand();
  console.log('Command:', command);
}
```

### React Component Integration

```tsx
import { VoiceControl } from './components/VoiceControl';

function MyComponent() {
  return (
    <div>
      <VoiceControl className="my-voice-control" />
    </div>
  );
}
```

### Demo Mode

```typescript
import { useVoiceDemo } from './hooks/useVoiceDemo';

function VoiceDemo() {
  const { runDemo, showCommands, isSupported } = useVoiceDemo();
  
  return (
    <div>
      {isSupported ? (
        <button onClick={runDemo}>Start Voice Demo</button>
      ) : (
        <p>Voice commands not supported</p>
      )}
    </div>
  );
}
```

## Configuration

### Language Configuration

```typescript
voiceService.updateConfig({
  language: 'en-US',      // Language code
  continuous: false,      // Continuous listening
  interimResults: true,   // Show interim results
  maxAlternatives: 1      // Number of alternatives
});
```

### Custom Commands

To add new voice commands, update the `commandPatterns` array in `voiceService.ts`:

```typescript
{
  pattern: /show reports/i,
  intent: 'navigate',
  action: '/reports'
}
```

## Security Considerations

1. **Permissions**: Voice commands require microphone permissions
2. **Privacy**: Audio is processed locally, not sent to external servers
3. **Fallbacks**: Always provide alternative input methods

## Testing

### Manual Testing

1. Open the application in a supported browser
2. Grant microphone permissions when prompted
3. Click the voice button in the sidebar
4. Speak one of the supported commands
5. Verify the correct action is triggered

### Automated Testing

```typescript
// Example Jest test
describe('VoiceService', () => {
  it('should detect supported commands', () => {
    const command = voiceService.parseCommand('show dashboard', 0.9);
    expect(command.intent).toBe('navigate');
    expect(command.params.action).toBe('/dashboard');
  });
});
```

## Troubleshooting

### Common Issues

1. **Microphone not working**
   - Check browser permissions
   - Ensure microphone is not blocked by other applications

2. **Commands not recognized**
   - Speak clearly and at normal pace
   - Check supported command list
   - Ensure good audio quality

3. **Browser compatibility**
   - Use Chrome or Safari for best experience
   - Check console for error messages

### Error Messages

- `"Speech Recognition not initialized"`: Browser doesn't support the API
- `"Recognition not available"`: Microphone permissions denied
- `"Speech recognition error: network"`: Internet connection required

## Performance Optimization

1. **Lazy Loading**: Voice service is only loaded when needed
2. **Efficient Pattern Matching**: Uses regex for fast command matching
3. **Error Handling**: Graceful degradation when voice features unavailable

## Future Enhancements

1. **Multi-language Support**: Support for Arabic, French, Spanish
2. **Custom Wake Words**: "Hey Qenergyz" activation
3. **Advanced NLP**: Better intent understanding
4. **Voice Feedback**: Audio responses to commands
5. **Offline Mode**: Local speech recognition models

## API Reference

### VoiceService Methods

```typescript
class VoiceService {
  isSpeechRecognitionSupported(): boolean
  startListening(): Promise<void>
  stopListening(): void
  processVoiceCommand(): Promise<VoiceCommand | null>
  getAvailableCommands(): string[]
  updateConfig(config: Partial<VoiceServiceConfig>): void
  getIsListening(): boolean
}
```

### VoiceCommand Interface

```typescript
interface VoiceCommand {
  command: string;     // Original spoken text
  intent: string;      // Parsed intent (navigate, action, help)
  confidence: number;  // Recognition confidence (0-1)
  params?: Record<string, any>; // Additional parameters
}
```

## Deployment Notes

1. **HTTPS Required**: Voice recognition only works over HTTPS in production
2. **Permissions**: Users will be prompted for microphone access
3. **Fallback UI**: Always provide non-voice alternatives
4. **Analytics**: Track voice command usage and success rates

## Support

For issues or questions regarding voice commands:

1. Check browser console for error messages
2. Verify microphone permissions in browser settings
3. Test with different commands from the supported list
4. Contact support with browser version and error details