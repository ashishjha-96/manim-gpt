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
   * Start a generation session with SSE streaming
   * @param {Object} params - Generation parameters
   * @param {Function} onProgress - Callback for progress events
   * @returns {Promise<Object>} - Final session data
   */
  async generateWithStreaming(params, onProgress) {
    const response = await fetch(`${this.baseURL}/session/generate-stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(params),
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let finalData = null;

    while (true) {
      const { done, value } = await reader.read();

      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = JSON.parse(line.slice(6));

          if (data.event === 'complete' || data.event === 'error') {
            finalData = data;
          }

          if (onProgress) {
            onProgress(data);
          }
        }
      }
    }

    return finalData;
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
    subtitleFontSize = 24,
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
   * Get render status for a session
   */
  async getRenderStatus(sessionId) {
    const response = await fetch(`${this.baseURL}/session/render-status/${sessionId}`);
    return response.json();
  }

  /**
   * Poll render status until completion or failure
   * @param {string} sessionId - Session ID
   * @param {Function} onProgress - Callback for progress updates (receives RenderStatusResponse)
   * @param {number} pollInterval - Polling interval in milliseconds (default: 4000)
   * @returns {Promise<Object>} - Final render status
   */
  async pollRenderStatus(sessionId, onProgress, pollInterval = 4000) {
    while (true) {
      const status = await this.getRenderStatus(sessionId);

      if (onProgress) {
        onProgress(status);
      }

      // Check if render is complete
      if (status.render_status === 'completed' || status.render_status === 'failed') {
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
