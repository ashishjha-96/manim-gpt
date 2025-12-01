// In development with Vite proxy, use /api prefix
// In production or IDX preview, the proxy handles routing to localhost:8000
const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

/**
 * API service for Manim GPT backend
 */
class ManimAPI {
  constructor(baseURL = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  /**
   * Health check
   */
  async checkHealth() {
    const response = await fetch(`${this.baseURL}/health`);
    return response.json();
  }

  /**
   * Get all LLM providers
   */
  async getProviders() {
    const response = await fetch(`${this.baseURL}/models/providers`);
    return response.json();
  }

  /**
   * Get models for a specific provider
   */
  async getModelsForProvider(provider) {
    const response = await fetch(`${this.baseURL}/models/providers/${provider}`);
    return response.json();
  }

  /**
   * Start a generation session asynchronously (background task)
   * @param {Object} params - Generation parameters
   * @returns {Promise<Object>} - Response with session_id and status "queued"
   */
  async generateAsync(params) {
    const response = await fetch(`${this.baseURL}/session/generate-async`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Connect to unified SSE stream for session updates using EventSource API
   * Provides real-time updates for both generation AND render progress
   * Note: EventSource automatically handles SSE format ('data:' prefix)
   * @param {string} sessionId - Session ID to stream
   * @param {Function} onEvent - Callback for each event
   * @returns {Function} - Cleanup function to close the connection
   */
  connectToSessionSSE(sessionId, onEvent) {
    const url = `${this.baseURL}/session/${sessionId}/sse`;
    const eventSource = new EventSource(url);

    // EventSource automatically strips 'data:' prefix and parses SSE format
    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (onEvent) {
          onEvent(data);
        }
      } catch (error) {
        console.error('Error parsing SSE data:', error);
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE error:', error);
      eventSource.close();
      if (onEvent) {
        onEvent({ event: 'error', error: 'SSE connection error' });
      }
    };

    // Return cleanup function
    return () => {
      eventSource.close();
    };
  }

  /**
   * Manually stream SSE from session SSE endpoint
   * Handles Server-Sent Events format with 'data:' prefix
   * @param {string} sessionId - Session ID to stream
   * @param {Function} onEvent - Callback for each event
   * @returns {Promise<Function>} - Cleanup function to abort the stream
   */
  async streamSessionUpdates(sessionId, onEvent) {
    const response = await fetch(`${this.baseURL}/session/${sessionId}/sse`);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let isActive = true;

    // Start reading stream
    (async () => {
      try {
        while (isActive) {
          const { done, value } = await reader.read();

          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            const trimmedLine = line.trim();
            if (trimmedLine) {
              try {
                // Handle SSE format: strip 'data: ' prefix if present
                let jsonData = trimmedLine;
                if (jsonData.startsWith('data: ')) {
                  jsonData = jsonData.substring(6); // Remove 'data: ' prefix
                }

                if (jsonData) {
                  const data = JSON.parse(jsonData);
                  if (onEvent) {
                    onEvent(data);
                  }
                }
              } catch (error) {
                console.error('Error parsing SSE line:', error, line);
              }
            }
          }
        }
      } catch (error) {
        if (isActive) {
          console.error('Stream error:', error);
          if (onEvent) {
            onEvent({ event: 'error', error: error.message });
          }
        }
      }
    })();

    // Return cleanup function
    return () => {
      isActive = false;
      reader.cancel();
    };
  }

  /**
   * Get session status
   */
  async getSessionStatus(sessionId) {
    const response = await fetch(`${this.baseURL}/session/status/${sessionId}`);
    return response.json();
  }

  /**
   * Update session code manually
   */
  async updateSessionCode(sessionId, code, validate = true) {
    const response = await fetch(`${this.baseURL}/session/update-code`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        session_id: sessionId,
        code,
        validate,
      }),
    });
    return response.json();
  }

  /**
   * Render video from session (async - returns immediately, use pollRenderStatus to track progress)
   */
  async renderVideo(
    sessionId,
    format = 'mp4',
    quality = 'medium',
    backgroundColor = null,
    includeSubtitles = true,
    subtitleFontSize = 12,
    subtitleStyle = null,
    enableAudio = false,
    audioLanguage = 'EN',
    audioSpeakerId = 0,
    audioSpeed = 1.0
  ) {
    const body = {
      session_id: sessionId,
      format,
      quality,
      include_subtitles: includeSubtitles,
      subtitle_font_size: subtitleFontSize,
      enable_audio: enableAudio,
      audio_language: audioLanguage,
      audio_speaker_id: audioSpeakerId,
      audio_speed: audioSpeed,
    };

    if (backgroundColor) {
      body.background_color = backgroundColor;
    }

    if (subtitleStyle) {
      body.subtitle_style = subtitleStyle;
    }

    const response = await fetch(`${this.baseURL}/session/render`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    });
    return response.json();
  }

  /**
   * Poll unified session status (generation + render) until completion or failure
   * Use this as an alternative to SSE streaming
   * @param {string} sessionId - Session ID
   * @param {Function} onProgress - Callback for progress updates (receives SessionStatusResponse)
   * @param {number} pollInterval - Polling interval in milliseconds (default: 2000)
   * @returns {Promise<Object>} - Final session status
   */
  async pollSessionStatus(sessionId, onProgress, pollInterval = 2000) {
    while (true) {
      const status = await this.getSessionStatus(sessionId);

      if (onProgress) {
        onProgress(status);
      }

      // Check if both generation and render are complete (or never started)
      const generationComplete = ['success', 'max_iterations_reached', 'failed'].includes(status.status);
      const renderComplete = !status.render_status || ['completed', 'failed'].includes(status.render_status);

      if (generationComplete && renderComplete) {
        return status;
      }

      // Wait before polling again
      await new Promise(resolve => setTimeout(resolve, pollInterval));
    }
  }

  /**
   * Get video download URL
   */
  getVideoDownloadUrl(sessionId) {
    return `${this.baseURL}/session/download?session_id=${sessionId}`;
  }

  /**
   * Get video stream URL for playback in UI
   */
  getVideoStreamUrl(sessionId) {
    return `${this.baseURL}/session/stream?session_id=${sessionId}`;
  }

  /**
   * List all sessions
   */
  async listSessions() {
    const response = await fetch(`${this.baseURL}/session/list`);
    return response.json();
  }

  /**
   * Delete a session
   */
  async deleteSession(sessionId) {
    const response = await fetch(`${this.baseURL}/session/${sessionId}`, {
      method: 'DELETE',
    });
    return response.json();
  }
}

export const manimAPI = new ManimAPI();
export default manimAPI;
