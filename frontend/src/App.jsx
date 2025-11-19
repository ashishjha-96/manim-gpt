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
  const [renderProgress, setRenderProgress] = useState([]);
  const [renderStatus, setRenderStatus] = useState(null);

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
    let cleanup = null;

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

      // Start async generation
      const result = await manimAPI.generateAsync(params);
      const newSessionId = result.session_id;
      setSessionId(newSessionId);

      console.log('Generation started:', result);

      // Connect to unified SSE stream for updates
      cleanup = await manimAPI.streamSessionUpdates(newSessionId, (event) => {
        console.log('SSE Event:', event);

        if (event.event === 'session_connected') {
          // Initial connection - get current state
          const state = event.state;
          if (state) {
            setCurrentIteration(state.current_iteration || 0);
            setMaxIterations(state.max_iterations || 5);
            setStatus(state.status || 'generating');

            if (state.final_code) {
              setGeneratedCode(state.final_code);
            }

            if (state.iterations_history) {
              setIterations(state.iterations_history);
            }
          }
        } else if (event.event === 'generation_progress') {
          // Generation progress update
          const state = event.state;
          if (state) {
            setCurrentIteration(state.current_iteration || 0);
            setStatus(state.status || 'generating');

            if (state.generated_code) {
              setGeneratedCode(state.generated_code);
            }

            if (state.iterations_history && state.iterations_history.length > 0) {
              setIterations(state.iterations_history);
              const lastIteration = state.iterations_history[state.iterations_history.length - 1];
              if (lastIteration.validation_result) {
                setValidationResult(lastIteration.validation_result);
              }
            }
          }
        } else if (event.event === 'generation_complete') {
          // Generation complete
          const state = event.state;
          if (state) {
            setStatus(state.status || 'success');
            setCurrentIteration(state.current_iteration || 0);

            if (state.final_code) {
              setGeneratedCode(state.final_code);
            }

            if (state.iterations_history && state.iterations_history.length > 0) {
              setIterations(state.iterations_history);
              const lastIteration = state.iterations_history[state.iterations_history.length - 1];
              if (lastIteration.validation_result) {
                setValidationResult(lastIteration.validation_result);
              }
            }
          }

          setIsGenerating(false);
        } else if (event.event === 'generation_error') {
          console.error('Generation error:', event);
          setStatus('failed');
          setIsGenerating(false);
        } else if (event.event === 'error' || event.event === 'fatal_error') {
          console.error('SSE error:', event.error);
          setStatus('failed');
          setIsGenerating(false);
        } else if (event.event === 'done') {
          // Stream closed normally
          setIsGenerating(false);
        }
      });
    } catch (error) {
      console.error('Generation failed:', error);
      setStatus('failed');
      setIsGenerating(false);

      // Clean up SSE connection on error
      if (cleanup) {
        cleanup();
      }
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

    let cleanup = null;

    try {
      setIsRendering(true);
      setVideoUrl(null);
      setRenderProgress([]);
      setRenderStatus('queued');

      // Start the render (returns immediately)
      const queueResult = await manimAPI.renderVideo(
        sessionId,
        renderSettings.format,
        renderSettings.quality,
        renderSettings.background_color,
        renderSettings.include_subtitles,
        renderSettings.subtitle_font_size || 24,
        renderSettings.subtitle_style || null,
        renderSettings.enable_audio || false,
        renderSettings.audio_language || 'EN',
        renderSettings.audio_speaker_id || 0,
        renderSettings.audio_speed || 1.0
      );

      if (queueResult.status !== 'queued') {
        console.error('Failed to queue render:', queueResult);
        alert('Failed to start render: ' + (queueResult.message || 'Unknown error'));
        setIsRendering(false);
        return;
      }

      console.log('Render started:', queueResult);

      // Connect to unified SSE stream for render updates
      cleanup = await manimAPI.streamSessionUpdates(sessionId, (event) => {
        console.log('Render SSE Event:', event);

        if (event.event === 'render_queued' || event.event === 'render_started' || event.event === 'render_progress') {
          const state = event.state;
          if (state) {
            setRenderStatus(state.render_status);
            setRenderProgress(state.render_progress || []);
          }
        } else if (event.event === 'render_complete') {
          const state = event.state;
          if (state) {
            setRenderStatus(state.render_status);
            setRenderProgress(state.render_progress || []);

            // Use stream URL for video playback in the UI
            const url = manimAPI.getVideoStreamUrl(sessionId);
            setVideoUrl(url);
            setVideoFormat(renderSettings.format);
            console.log('Rendering completed successfully!');
          }

          setIsRendering(false);

          // Clean up SSE connection
          if (cleanup) {
            cleanup();
          }
        } else if (event.event === 'render_error') {
          const state = event.state;
          if (state) {
            setRenderStatus(state.render_status);
            setRenderProgress(state.render_progress || []);
            console.error('Rendering failed:', state.render_error);
            alert('Rendering failed: ' + (state.render_error || 'Unknown error'));
          }

          setIsRendering(false);

          // Clean up SSE connection
          if (cleanup) {
            cleanup();
          }
        }
      });
    } catch (error) {
      console.error('Rendering error:', error);
      alert('Rendering failed. Please try again.');
      setIsRendering(false);

      // Clean up SSE connection on error
      if (cleanup) {
        cleanup();
      }
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
                renderStatus={renderStatus}
                renderProgress={renderProgress}
              />
            )}
          </div>

          {/* Middle Column - Code & Progress */}
          <div className="lg:col-span-2 space-y-6">
            {/* Iteration Logs */}
            {iterations.length > 0 && (
              <IterationLogs iterations={iterations} />
            )}

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
