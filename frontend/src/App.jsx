import { useState, useEffect } from 'react';
import { Activity, AlertCircle } from 'lucide-react';
import manimAPI from './services/api';
import GenerationForm from './components/GenerationForm';
import ProgressView from './components/ProgressView';
import CodeEditor from './components/CodeEditor';
import IterationLogs from './components/IterationLogs';
import RenderSettings from './components/RenderSettings';
import VideoPlayer from './components/VideoPlayer';

function App() {
  // API Health
  const [apiHealthy, setApiHealthy] = useState(null);

  // Generation State
  const [isGenerating, setIsGenerating] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [currentIteration, setCurrentIteration] = useState(0);
  const [maxIterations, setMaxIterations] = useState(5);
  const [status, setStatus] = useState('');
  const [generatedCode, setGeneratedCode] = useState('');
  const [validationResult, setValidationResult] = useState(null);
  const [iterations, setIterations] = useState([]);

  // Rendering State
  const [isRendering, setIsRendering] = useState(false);
  const [videoUrl, setVideoUrl] = useState(null);
  const [videoFormat, setVideoFormat] = useState('mp4');

  // Code Update State
  const [isValidating, setIsValidating] = useState(false);

  // Check API health on mount
  useEffect(() => {
    checkAPIHealth();
  }, []);

  const checkAPIHealth = async () => {
    try {
      await manimAPI.checkHealth();
      setApiHealthy(true);
    } catch (error) {
      setApiHealthy(false);
      console.error('API health check failed:', error);
    }
  };

  const handleGenerate = async (params) => {
    try {
      setIsGenerating(true);
      setSessionId(null);
      setGeneratedCode('');
      setValidationResult(null);
      setIterations([]);
      setVideoUrl(null);
      setCurrentIteration(0);
      setMaxIterations(params.max_iterations || 5);
      setStatus('generating');

      await manimAPI.generateWithStreaming(params, (event) => {
        console.log('SSE Event:', event);

        if (event.event === 'start') {
          setSessionId(event.session_id);
          setMaxIterations(event.max_iterations || 5);
        } else if (event.event === 'progress') {
          setCurrentIteration(event.current_iteration || 0);
          setStatus(event.status || 'generating');

          if (event.generated_code) {
            setGeneratedCode(event.generated_code);
          }

          if (event.validation_result) {
            setValidationResult(event.validation_result);
          }

          if (event.iterations_history) {
            setIterations(event.iterations_history);
          }
        } else if (event.event === 'complete') {
          setStatus(event.status || 'success');
          setCurrentIteration(event.current_iteration || 0);

          if (event.generated_code) {
            setGeneratedCode(event.generated_code);
          }

          if (event.validation_result) {
            setValidationResult(event.validation_result);
          }

          setIsGenerating(false);
        } else if (event.event === 'error') {
          console.error('Generation error:', event.error);
          setStatus('failed');
          setIsGenerating(false);
        }
      });
    } catch (error) {
      console.error('Generation failed:', error);
      setStatus('failed');
      setIsGenerating(false);
    }
  };

  const handleCodeUpdate = async (code) => {
    if (!sessionId) return;

    try {
      setIsValidating(true);
      const result = await manimAPI.updateSessionCode(sessionId, code, true);

      setGeneratedCode(code);
      setValidationResult(result.validation_result);

      // Refresh session status to get updated iterations
      const sessionStatus = await manimAPI.getSessionStatus(sessionId);
      if (sessionStatus.iterations) {
        setIterations(sessionStatus.iterations);
      }
    } catch (error) {
      console.error('Code update failed:', error);
    } finally {
      setIsValidating(false);
    }
  };

  const handleRender = async (renderSettings) => {
    if (!sessionId) return;

    try {
      setIsRendering(true);
      setVideoUrl(null);

      const result = await manimAPI.renderVideo(
        sessionId,
        renderSettings.format,
        renderSettings.quality,
        renderSettings.background_color,
        renderSettings.include_subtitles
      );

      if (result.status === 'success') {
        // Use stream URL for video playback in the UI
        const url = manimAPI.getVideoStreamUrl(sessionId);
        setVideoUrl(url);
        setVideoFormat(renderSettings.format);
      } else {
        console.error('Rendering failed:', result.message);
        alert('Rendering failed: ' + result.message);
      }
    } catch (error) {
      console.error('Rendering error:', error);
      alert('Rendering failed. Please try again.');
    } finally {
      setIsRendering(false);
    }
  };

  const canRender = sessionId && validationResult?.is_valid && !isGenerating;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Manim GPT
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                AI-powered mathematical animation generator
              </p>
            </div>
            <div className="flex items-center gap-2">
              {apiHealthy === null ? (
                <div className="flex items-center gap-2 text-gray-500">
                  <Activity className="w-4 h-4 animate-pulse" />
                  <span className="text-sm">Checking API...</span>
                </div>
              ) : apiHealthy ? (
                <div className="flex items-center gap-2 text-green-600">
                  <Activity className="w-4 h-4" />
                  <span className="text-sm font-medium">API Connected</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-red-600">
                  <AlertCircle className="w-4 h-4" />
                  <span className="text-sm font-medium">API Offline</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column - Input & Settings */}
          <div className="space-y-6">
            <GenerationForm
              onGenerate={handleGenerate}
              isGenerating={isGenerating}
            />

            {sessionId && (
              <RenderSettings
                onRender={handleRender}
                isRendering={isRendering}
                canRender={canRender}
              />
            )}
          </div>

          {/* Middle Column - Code & Progress */}
          <div className="lg:col-span-2 space-y-6">
            {/* Progress */}
            {sessionId && (
              <ProgressView
                currentIteration={currentIteration}
                maxIterations={maxIterations}
                status={status}
                sessionId={sessionId}
              />
            )}

            {/* Code Editor */}
            <CodeEditor
              code={generatedCode}
              onUpdate={handleCodeUpdate}
              validationResult={validationResult}
              isValidating={isValidating}
              sessionId={sessionId}
            />

            {/* Video Player */}
            {(videoUrl || sessionId) && (
              <VideoPlayer
                videoUrl={videoUrl}
                sessionId={sessionId}
                format={videoFormat}
              />
            )}

            {/* Iteration Logs */}
            {iterations.length > 0 && (
              <IterationLogs iterations={iterations} />
            )}
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-center text-sm text-gray-500">
            Powered by <span className="font-medium">Manim</span> and{' '}
            <span className="font-medium">Large Language Models</span>
          </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
