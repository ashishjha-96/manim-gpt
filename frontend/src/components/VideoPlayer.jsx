import { Download, Video } from 'lucide-react';

export default function VideoPlayer({ videoUrl, sessionId, format = 'mp4' }) {
  if (!videoUrl) {
    return (
      <div className="card">
        <div className="text-center py-12">
          <Video className="w-16 h-16 mx-auto text-gray-300 mb-3" />
          <p className="text-gray-500">No video rendered yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Generate code and click "Render Video" to see your animation
          </p>
        </div>
      </div>
    );
  }

  const isGif = format === 'gif';

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Video className="w-5 h-5 text-primary-600" />
          Rendered Video
        </h2>
        <a
          href={videoUrl}
          download
          className="btn-secondary text-sm flex items-center gap-1"
        >
          <Download className="w-4 h-4" />
          Download
        </a>
      </div>

      <div className="bg-black rounded-lg overflow-hidden">
        {isGif ? (
          <img
            src={videoUrl}
            alt="Rendered animation"
            className="w-full h-auto"
          />
        ) : (
          <video
            src={videoUrl}
            controls
            loop
            autoPlay
            className="w-full h-auto"
          >
            Your browser does not support the video tag.
          </video>
        )}
      </div>

      {sessionId && (
        <p className="text-xs text-gray-500 mt-3">
          Session ID: <span className="font-mono">{sessionId}</span>
        </p>
      )}
    </div>
  );
}
