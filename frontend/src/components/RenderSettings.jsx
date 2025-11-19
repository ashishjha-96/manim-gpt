import { useState } from 'react';
import { Film, ChevronDown, Volume2 } from 'lucide-react';

const FORMATS = [
  { value: 'mp4', label: 'MP4' },
  { value: 'webm', label: 'WebM' },
  { value: 'gif', label: 'GIF' },
  { value: 'mov', label: 'MOV' },
];

const QUALITIES = [
  { value: 'low', label: 'Low (480p, 15fps)' },
  { value: 'medium', label: 'Medium (720p, 30fps)' },
  { value: 'high', label: 'High (1080p, 60fps)' },
  { value: '4k', label: '4K (2160p, 60fps)' },
];

const LANGUAGES = [
  { value: 'EN', label: 'English' },
  { value: 'ES', label: 'Spanish' },
  { value: 'FR', label: 'French' },
  { value: 'ZH', label: 'Chinese' },
  { value: 'JP', label: 'Japanese' },
  { value: 'KR', label: 'Korean' },
];

const SPEAKER_VOICES = {
  EN: [
    { value: 0, label: 'Default' },
    { value: 1, label: 'Female' },
    { value: 2, label: 'Male' },
  ],
  ES: [{ value: 0, label: 'Default' }],
  FR: [{ value: 0, label: 'Default' }],
  ZH: [{ value: 0, label: 'Default' }],
  JP: [{ value: 0, label: 'Default' }],
  KR: [{ value: 0, label: 'Default' }],
};


export default function RenderSettings({
  onRender,
  isRendering,
  canRender,
  renderStatus,
  renderProgress
}) {
  const [format, setFormat] = useState('mp4');
  const [quality, setQuality] = useState('medium');
  const [backgroundColor, setBackgroundColor] = useState('#000000');
  const [includeSubtitles, setIncludeSubtitles] = useState(true);
  const [subtitleFontSize, setSubtitleFontSize] = useState(24);
  const [enableAudio, setEnableAudio] = useState(false);
  const [audioLanguage, setAudioLanguage] = useState('EN');
  const [audioSpeakerId, setAudioSpeakerId] = useState(0);
  const [audioSpeed, setAudioSpeed] = useState(1.0);
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Format render status for display
  const formatStatus = (status) => {
    if (!status) return '';

    // Special formatting for audio-related statuses
    const statusEmojis = {
      'generating_audio': '🎙️ Generating Audio',
      'mixing_audio': '🔊 Mixing Audio',
      'generating_subtitles': '📝 Generating Subtitles',
      'creating_srt': '📄 Creating Subtitles',
      'stitching_subtitles': '🎬 Adding Subtitles',
      'rendering_video': '🎥 Rendering Video',
      'preparing': '⚙️ Preparing',
      'completed': '✅ Completed',
      'failed': '❌ Failed',
    };

    return statusEmojis[status] || status.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
  };

  // Get latest progress message
  const getLatestMessage = () => {
    if (!renderProgress || renderProgress.length === 0) return null;
    return renderProgress[renderProgress.length - 1].message;
  };

  const handleRender = () => {
    onRender({
      format,
      quality,
      background_color: backgroundColor,
      include_subtitles: includeSubtitles,
      subtitle_style: null, // Use default style
      subtitle_font_size: subtitleFontSize,
      enable_audio: enableAudio,
      audio_language: audioLanguage,
      audio_speaker_id: audioSpeakerId,
      audio_speed: audioSpeed,
    });
  };

  // Get available speaker voices for selected language
  const availableSpeakers = SPEAKER_VOICES[audioLanguage] || SPEAKER_VOICES.EN;

  return (
    <div className="card">
      <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
        <Film className="w-5 h-5 text-primary-600" />
        Render Video
      </h2>

      <div className="space-y-4">
        {/* Format Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Output Format
          </label>
          <div className="relative">
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              disabled={isRendering}
              className="input-field appearance-none pr-10 disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              {FORMATS.map((fmt) => (
                <option key={fmt.value} value={fmt.value}>
                  {fmt.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Quality Selection */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Quality
          </label>
          <div className="relative">
            <select
              value={quality}
              onChange={(e) => setQuality(e.target.value)}
              disabled={isRendering}
              className="input-field appearance-none pr-10 disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              {QUALITIES.map((qual) => (
                <option key={qual.value} value={qual.value}>
                  {qual.label}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
          </div>
        </div>

        {/* Subtitle Toggle */}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="includeSubtitles"
            checked={includeSubtitles}
            onChange={(e) => setIncludeSubtitles(e.target.checked)}
            disabled={isRendering}
            className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500 focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <label
            htmlFor="includeSubtitles"
            className="text-sm font-medium text-gray-700 cursor-pointer select-none"
          >
            Include AI-Generated Subtitles
          </label>
        </div>
        <p className="text-xs text-gray-500 -mt-2 ml-6">
          Add educational narration that explains the animation
        </p>

        {/* Subtitle Font Size (shown when subtitles are enabled) */}
        {includeSubtitles && (
          <div className="ml-6 p-3 bg-gray-50 rounded-lg border border-gray-200">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Subtitle Font Size: {subtitleFontSize}px
            </label>
            <input
              type="range"
              min="12"
              max="48"
              step="2"
              value={subtitleFontSize}
              onChange={(e) => setSubtitleFontSize(parseInt(e.target.value))}
              disabled={isRendering}
              className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            />
            <div className="flex justify-between text-xs text-gray-500 mt-1">
              <span>Small (12px)</span>
              <span>Large (48px)</span>
            </div>
          </div>
        )}

        {/* Audio Narration Toggle */}
        <div className="flex items-center gap-2">
          <input
            type="checkbox"
            id="enableAudio"
            checked={enableAudio}
            onChange={(e) => setEnableAudio(e.target.checked)}
            disabled={isRendering || !includeSubtitles}
            className="w-4 h-4 text-primary-600 bg-gray-100 border-gray-300 rounded focus:ring-primary-500 focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <label
            htmlFor="enableAudio"
            className="text-sm font-medium text-gray-700 cursor-pointer select-none flex items-center gap-2"
          >
            <Volume2 className="w-4 h-4" />
            Enable Audio Narration (TTS)
          </label>
          {!includeSubtitles && (
            <span className="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded">
              Requires subtitles
            </span>
          )}
        </div>
        <p className="text-xs text-gray-500 -mt-2 ml-6">
          Generate synchronized text-to-speech audio using Piper TTS
        </p>

        {/* Audio Settings (shown when audio is enabled) */}
        {enableAudio && includeSubtitles && (
          <div className="ml-6 p-4 bg-gradient-to-br from-purple-50 to-blue-50 rounded-lg border border-purple-200">
            <div className="space-y-4">
              {/* Language Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Audio Language
                </label>
                <div className="relative">
                  <select
                    value={audioLanguage}
                    onChange={(e) => {
                      setAudioLanguage(e.target.value);
                      // Reset speaker ID when language changes
                      setAudioSpeakerId(0);
                    }}
                    disabled={isRendering}
                    className="input-field appearance-none pr-10 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    {LANGUAGES.map((lang) => (
                      <option key={lang.value} value={lang.value}>
                        {lang.label}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
                </div>
              </div>

              {/* Speaker Voice Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Speaker Voice
                </label>
                <div className="relative">
                  <select
                    value={audioSpeakerId}
                    onChange={(e) => setAudioSpeakerId(parseInt(e.target.value))}
                    disabled={isRendering}
                    className="input-field appearance-none pr-10 disabled:bg-gray-100 disabled:cursor-not-allowed"
                  >
                    {availableSpeakers.map((speaker) => (
                      <option key={speaker.value} value={speaker.value}>
                        {speaker.label}
                      </option>
                    ))}
                  </select>
                  <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
                </div>
                {audioLanguage !== 'EN' && (
                  <p className="text-xs text-gray-500 mt-1">
                    Only default voice available for {LANGUAGES.find(l => l.value === audioLanguage)?.label}
                  </p>
                )}
              </div>

              {/* Speech Speed Control */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Speech Speed: {audioSpeed}x
                </label>
                <input
                  type="range"
                  min="0.5"
                  max="2.0"
                  step="0.1"
                  value={audioSpeed}
                  onChange={(e) => setAudioSpeed(parseFloat(e.target.value))}
                  disabled={isRendering}
                  className="w-full h-2 bg-gradient-to-r from-blue-200 to-purple-200 rounded-lg appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
                />
                <div className="flex justify-between text-xs text-gray-500 mt-1">
                  <span>Slow (0.5x)</span>
                  <span>Normal (1.0x)</span>
                  <span>Fast (2.0x)</span>
                </div>
              </div>

              {/* Info Alert */}
              <div className="bg-blue-100 border border-blue-300 rounded p-2">
                <p className="text-xs text-blue-800">
                  <strong>Note:</strong> Piper TTS must be installed on the server for audio generation.
                  See TTS_INSTALLATION.md for setup instructions.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Advanced Settings */}
        <div>
          <button
            type="button"
            onClick={() => setShowAdvanced(!showAdvanced)}
            disabled={isRendering}
            className="text-sm text-primary-600 hover:text-primary-700 disabled:opacity-50"
          >
            {showAdvanced ? 'Hide' : 'Show'} advanced options
          </button>

          {showAdvanced && (
            <div className="mt-3 p-4 border border-gray-200 rounded-lg bg-gray-50">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Background Color
              </label>
              <div className="flex gap-2 items-center">
                <input
                  type="color"
                  value={backgroundColor}
                  onChange={(e) => setBackgroundColor(e.target.value)}
                  disabled={isRendering}
                  className="w-12 h-10 rounded border border-gray-300 cursor-pointer disabled:opacity-50"
                />
                <input
                  type="text"
                  value={backgroundColor}
                  onChange={(e) => setBackgroundColor(e.target.value)}
                  disabled={isRendering}
                  placeholder="#000000"
                  className="input-field flex-1 font-mono text-sm disabled:bg-gray-100"
                />
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Hex color code or Manim color name
              </p>
            </div>
          )}
        </div>

        {/* Render Progress */}
        {isRendering && renderStatus && (
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center gap-2 mb-2">
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
              <span className="text-sm font-medium text-blue-900">
                {formatStatus(renderStatus)}
              </span>
            </div>
            {getLatestMessage() && (
              <p className="text-xs text-blue-700 ml-6">
                {getLatestMessage()}
              </p>
            )}
          </div>
        )}

        {/* Render Button */}
        <button
          onClick={handleRender}
          disabled={isRendering || !canRender}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {isRendering ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Rendering...
            </>
          ) : (
            <>
              <Film className="w-5 h-5" />
              Render Video
            </>
          )}
        </button>

        {!canRender && (
          <p className="text-sm text-gray-500 text-center">
            Generate valid code first to enable rendering
          </p>
        )}
      </div>
    </div>
  );
}
