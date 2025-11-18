import { Loader2, CheckCircle, XCircle, AlertCircle } from 'lucide-react';

export default function ProgressView({
  currentIteration,
  maxIterations,
  status,
  sessionId
}) {
  const progress = maxIterations > 0 ? (currentIteration / maxIterations) * 100 : 0;

  const getStatusIcon = () => {
    switch (status) {
      case 'generating':
        return <Loader2 className="w-5 h-5 text-primary-600 animate-spin" />;
      case 'validating':
        return <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />;
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-600" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-600" />;
      case 'max_iterations_reached':
        return <AlertCircle className="w-5 h-5 text-yellow-600" />;
      default:
        return null;
    }
  };

  const getStatusText = () => {
    switch (status) {
      case 'generating':
        return 'Generating code...';
      case 'validating':
        return 'Validating code...';
      case 'refining':
        return 'Refining code...';
      case 'success':
        return 'Code generation successful!';
      case 'failed':
        return 'Code generation failed';
      case 'max_iterations_reached':
        return 'Max iterations reached';
      default:
        return 'Initializing...';
    }
  };

  const getStatusColor = () => {
    switch (status) {
      case 'success':
        return 'text-green-700';
      case 'failed':
        return 'text-red-700';
      case 'max_iterations_reached':
        return 'text-yellow-700';
      default:
        return 'text-gray-700';
    }
  };

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          {getStatusIcon()}
          <h3 className={`font-medium ${getStatusColor()}`}>
            {getStatusText()}
          </h3>
        </div>
        {sessionId && (
          <div className="text-xs text-gray-500">
            Session: <span className="font-mono">{sessionId.slice(0, 8)}...</span>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      <div className="mb-3">
        <div className="flex justify-between text-sm text-gray-600 mb-1">
          <span>Iteration {currentIteration} of {maxIterations}</span>
          <span>{Math.round(progress)}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
          <div
            className="h-full bg-primary-600 transition-all duration-300 ease-out rounded-full"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {/* Status Message */}
      {status === 'max_iterations_reached' && (
        <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            Maximum iteration limit reached. The code may still have errors.
            You can edit it manually and validate.
          </p>
        </div>
      )}
    </div>
  );
}
