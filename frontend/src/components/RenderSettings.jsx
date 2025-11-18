import { useState } from 'react';
import { Film, ChevronDown } from 'lucide-react';

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

export default function RenderSettings({
  onRender,
  isRendering,
  canRender
}) {
  const [format, setFormat] = useState('mp4');
  const [quality, setQuality] = useState('medium');
  const [backgroundColor, setBackgroundColor] = useState('#000000');
  const [includeSubtitles, setIncludeSubtitles] = useState(true);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleRender = () => {
    onRender({
      format,
      quality,
      background_color: backgroundColor,
      include_subtitles: includeSubtitles,
    });
  };

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
