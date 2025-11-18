import { useState, useEffect } from 'react';
import { ChevronDown } from 'lucide-react';
import manimAPI from '../services/api';

export default function ModelSelector({ value, onChange, disabled = false }) {
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [models, setModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [customModel, setCustomModel] = useState('');
  const [useCustom, setUseCustom] = useState(false);

  // Load providers on mount
  useEffect(() => {
    loadProviders();
  }, []);

  // Load models when provider changes
  useEffect(() => {
    if (selectedProvider && !useCustom) {
      loadModels(selectedProvider);
    }
  }, [selectedProvider, useCustom]);

  const loadProviders = async () => {
    try {
      setLoading(true);
      const data = await manimAPI.getProviders();
      setProviders(data.providers || []);
      if (data.providers && data.providers.length > 0) {
        setSelectedProvider(data.providers[0]);
      }
    } catch (error) {
      console.error('Failed to load providers:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadModels = async (provider) => {
    try {
      setLoading(true);
      const data = await manimAPI.getModelsForProvider(provider);
      setModels(data.models || []);
      if (data.models && data.models.length > 0 && !value) {
        onChange(data.models[0]);
      }
    } catch (error) {
      console.error('Failed to load models:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleProviderChange = (e) => {
    const provider = e.target.value;
    setSelectedProvider(provider);
    setUseCustom(false);
  };

  const handleModelChange = (e) => {
    onChange(e.target.value);
  };

  const handleCustomModelChange = (e) => {
    const custom = e.target.value;
    setCustomModel(custom);
    onChange(custom);
  };

  const toggleCustomModel = () => {
    setUseCustom(!useCustom);
    if (!useCustom) {
      onChange(customModel);
    } else if (models.length > 0) {
      onChange(models[0]);
    }
  };

  return (
    <div className="space-y-3">
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">
          Provider
        </label>
        <div className="relative">
          <select
            value={selectedProvider}
            onChange={handleProviderChange}
            disabled={disabled || loading || useCustom}
            className="input-field appearance-none pr-10 disabled:bg-gray-100 disabled:cursor-not-allowed"
          >
            {providers.map((provider) => (
              <option key={provider} value={provider}>
                {provider}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
        </div>
      </div>

      <div>
        <div className="flex items-center justify-between mb-1">
          <label className="block text-sm font-medium text-gray-700">
            Model
          </label>
          <button
            type="button"
            onClick={toggleCustomModel}
            disabled={disabled}
            className="text-xs text-primary-600 hover:text-primary-700 disabled:opacity-50"
          >
            {useCustom ? 'Use preset' : 'Use custom model'}
          </button>
        </div>

        {useCustom ? (
          <input
            type="text"
            value={customModel}
            onChange={handleCustomModelChange}
            placeholder="Enter custom model name"
            disabled={disabled}
            className="input-field disabled:bg-gray-100 disabled:cursor-not-allowed"
          />
        ) : (
          <div className="relative">
            <select
              value={value || ''}
              onChange={handleModelChange}
              disabled={disabled || loading || models.length === 0}
              className="input-field appearance-none pr-10 disabled:bg-gray-100 disabled:cursor-not-allowed"
            >
              {models.length === 0 ? (
                <option>No models available</option>
              ) : (
                models.map((model) => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))
              )}
            </select>
            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400 pointer-events-none" />
          </div>
        )}
      </div>

      {loading && (
        <p className="text-xs text-gray-500 italic">Loading models...</p>
      )}
    </div>
  );
}
