import { useState } from 'react';
import { Sparkles, Settings2 } from 'lucide-react';
import ModelSelector from './ModelSelector';

const EXAMPLE_PROMPTS = [
  "Create a visualization of the Pythagorean theorem",
  "Animate a circle transforming into a square",
  "Show the graph of a sine wave",
  "Visualize the derivative of x^2",
  "Create a rotating 3D cube",
];

export default function GenerationForm({ onGenerate, isGenerating }) {
  const [prompt, setPrompt] = useState('');
  const [model, setModel] = useState('');
  const [temperature, setTemperature] = useState(0.7);
  const [maxTokens, setMaxTokens] = useState(2000);
  const [maxIterations, setMaxIterations] = useState(5);
  const [apiToken, setApiToken] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    onGenerate({
      prompt: prompt.trim(),
      model: model || undefined,
      temperature,
      max_tokens: maxTokens,
      max_iterations: maxIterations,
      api_token: apiToken || undefined,
    });
  };

  const handleExampleClick = (example) => {
    setPrompt(example);
  };

  return (
    <div className="card">
      <h2 className="text-2xl font-bold text-gray-900 mb-4 flex items-center gap-2">
        <Sparkles className="w-6 h-6 text-primary-600" />
        Generate Animation
      </h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Prompt Input */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Describe your animation
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="e.g., Create a visualization showing the Pythagorean theorem with animated squares..."
            disabled={isGenerating}
            rows={4}
            className="input-field resize-none disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        </div>

        {/* Example Prompts */}
        <div>
          <p className="text-xs text-gray-600 mb-2">Example prompts:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((example, index) => (
              <button
                key={index}
                type="button"
                onClick={() => handleExampleClick(example)}
                disabled={isGenerating}
                className="text-xs px-3 py-1 bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {example}
              </button>
            ))}
          </div>
        </div>

        {/* Advanced Settings Toggle */}
        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          disabled={isGenerating}
          className="flex items-center gap-2 text-sm text-primary-600 hover:text-primary-700 disabled:opacity-50"
        >
          <Settings2 className="w-4 h-4" />
          {showAdvanced ? 'Hide' : 'Show'} advanced settings
        </button>

        {/* Advanced Settings */}
        {showAdvanced && (
          <div className="border border-gray-200 rounded-lg p-4 space-y-4 bg-gray-50">
            {/* Model Selection */}
            <ModelSelector
              value={model}
              onChange={setModel}
              disabled={isGenerating}
            />

            {/* API Token */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Inference provider token
              </label>
              <input
                type="password"
                value={apiToken}
                onChange={(e) => setApiToken(e.target.value)}
                placeholder="LLM_API_TOKEN"
                disabled={isGenerating}
                className="input-field disabled:bg-gray-100 disabled:cursor-not-allowed"
              />
              <p className="text-xs text-gray-500 mt-1">
                Optional. Will override environment variables if provided.
              </p>
            </div>

            {/* Temperature */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Temperature: {temperature}
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(parseFloat(e.target.value))}
                disabled={isGenerating}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed accent-primary-600"
              />
              <p className="text-xs text-gray-500 mt-1">
                Lower values make output more focused and deterministic
              </p>
            </div>

            {/* Max Tokens */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Tokens: {maxTokens}
              </label>
              <input
                type="range"
                min="500"
                max="4000"
                step="100"
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value))}
                disabled={isGenerating}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed accent-primary-600"
              />
              <p className="text-xs text-gray-500 mt-1">
                Maximum length of generated code
              </p>
            </div>

            {/* Max Iterations */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Max Refinement Iterations: {maxIterations}
              </label>
              <input
                type="range"
                min="1"
                max="10"
                step="1"
                value={maxIterations}
                onChange={(e) => setMaxIterations(parseInt(e.target.value))}
                disabled={isGenerating}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed accent-primary-600"
              />
              <p className="text-xs text-gray-500 mt-1">
                Number of attempts to refine and fix errors
              </p>
            </div>
          </div>
        )}

        {/* Generate Button */}
        <button
          type="submit"
          disabled={isGenerating || !prompt.trim()}
          className="btn-primary w-full flex items-center justify-center gap-2"
        >
          {isGenerating ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
              Generating...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5" />
              Generate Animation Code
            </>
          )}
        </button>
      </form>
    </div>
  );
}
