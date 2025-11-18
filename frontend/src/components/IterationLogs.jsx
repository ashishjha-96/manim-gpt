import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle, XCircle, Code, Clock, Zap } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

export default function IterationLogs({ iterations }) {
  const [expandedIterations, setExpandedIterations] = useState(new Set());

  const toggleIteration = (index) => {
    const newExpanded = new Set(expandedIterations);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedIterations(newExpanded);
  };

  if (!iterations || iterations.length === 0) {
    return null;
  }

  // Calculate aggregate metrics
  const totalGenerationTime = iterations.reduce((sum, iter) =>
    sum + (iter.generation_metrics?.time_taken || 0), 0
  );
  const totalValidationTime = iterations.reduce((sum, iter) =>
    sum + (iter.validation_metrics?.time_taken || 0), 0
  );
  const totalTokens = iterations.reduce((sum, iter) =>
    sum + (iter.generation_metrics?.total_tokens || 0), 0
  );
  const successCount = iterations.filter(iter =>
    iter.validation_result?.is_valid
  ).length;

  return (
    <div className="card">
      <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
        <Code className="w-5 h-5 text-primary-600" />
        Iteration History
      </h2>

      {/* Summary Metrics */}
      <div className="mb-4 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-gray-200">
        <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-1">
          <Zap className="w-4 h-4 text-primary-600" />
          Overall Performance
        </h3>
        <div className="grid grid-cols-4 gap-4">
          <div className="text-center">
            <div className="text-2xl font-bold text-primary-600">{iterations.length}</div>
            <div className="text-xs text-gray-600 mt-1">Total Iterations</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">{successCount}</div>
            <div className="text-xs text-gray-600 mt-1">Successful</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">
              {(totalGenerationTime + totalValidationTime).toFixed(1)}s
            </div>
            <div className="text-xs text-gray-600 mt-1">Total Time</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {totalTokens.toLocaleString()}
            </div>
            <div className="text-xs text-gray-600 mt-1">Total Tokens</div>
          </div>
        </div>
        <div className="mt-3 pt-3 border-t border-gray-200 grid grid-cols-2 gap-4 text-xs">
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Avg Generation:</span>
            <span className="font-medium text-blue-700">
              {(totalGenerationTime / iterations.length).toFixed(2)}s
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-gray-600">Avg Validation:</span>
            <span className="font-medium text-purple-700">
              {(totalValidationTime / iterations.length).toFixed(2)}s
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-2">
        {iterations.map((iteration, index) => {
          const isExpanded = expandedIterations.has(index);
          const isValid = iteration.validation_result?.is_valid;
          const hasErrors = iteration.validation_result?.errors?.length > 0;
          const hasWarnings = iteration.validation_result?.warnings?.length > 0;

          return (
            <div key={index} className="border border-gray-200 rounded-lg overflow-hidden">
              {/* Header */}
              <button
                onClick={() => toggleIteration(index)}
                className="w-full px-4 py-3 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors"
              >
                <div className="flex items-center gap-3">
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4 text-gray-500" />
                  ) : (
                    <ChevronRight className="w-4 h-4 text-gray-500" />
                  )}
                  <span className="font-medium text-gray-900">
                    Iteration {iteration.iteration_number}
                  </span>
                  {iteration.status && (
                    <span className={`text-xs px-2 py-1 rounded-full ${
                      iteration.status === 'success'
                        ? 'bg-green-100 text-green-700'
                        : iteration.status === 'failed'
                        ? 'bg-red-100 text-red-700'
                        : 'bg-yellow-100 text-yellow-700'
                    }`}>
                      {iteration.status}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  {isValid ? (
                    <CheckCircle className="w-5 h-5 text-green-500" />
                  ) : hasErrors ? (
                    <XCircle className="w-5 h-5 text-red-500" />
                  ) : null}
                  <span className="text-xs text-gray-500">
                    {new Date(iteration.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              </button>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="p-4 space-y-4 bg-white">
                  {/* Validation Result */}
                  {iteration.validation_result && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">
                        Validation Result
                      </h4>
                      <div className={`p-3 rounded-lg border ${
                        isValid
                          ? 'bg-green-50 border-green-200'
                          : 'bg-red-50 border-red-200'
                      }`}>
                        <p className={`text-sm font-medium ${
                          isValid ? 'text-green-800' : 'text-red-800'
                        }`}>
                          {isValid ? 'Valid' : 'Invalid'}
                        </p>
                        {hasErrors && (
                          <ul className="mt-2 space-y-1 text-sm text-red-700">
                            {iteration.validation_result.errors.map((error, idx) => (
                              <li key={idx} className="flex gap-1">
                                <span>•</span>
                                <span>{error}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                        {hasWarnings && (
                          <ul className="mt-2 space-y-1 text-sm text-yellow-700">
                            {iteration.validation_result.warnings.map((warning, idx) => (
                              <li key={idx} className="flex gap-1">
                                <span>⚠</span>
                                <span>{warning}</span>
                              </li>
                            ))}
                          </ul>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Metrics */}
                  {(iteration.generation_metrics || iteration.validation_metrics) && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2 flex items-center gap-1">
                        <Zap className="w-4 h-4" />
                        Performance Metrics
                      </h4>
                      <div className="grid grid-cols-2 gap-3">
                        {/* Generation Metrics */}
                        {iteration.generation_metrics && (
                          <div className="p-3 rounded-lg border border-blue-200 bg-blue-50">
                            <div className="flex items-center gap-1 mb-2">
                              <Code className="w-3.5 h-3.5 text-blue-600" />
                              <h5 className="text-xs font-semibold text-blue-800">Code Generation</h5>
                            </div>
                            <div className="space-y-1.5 text-xs">
                              <div className="flex items-center justify-between">
                                <span className="text-blue-700 flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  Time:
                                </span>
                                <span className="font-medium text-blue-900">
                                  {iteration.generation_metrics.time_taken?.toFixed(2)}s
                                </span>
                              </div>
                              {iteration.generation_metrics.total_tokens && (
                                <>
                                  <div className="flex items-center justify-between">
                                    <span className="text-blue-700">Total Tokens:</span>
                                    <span className="font-medium text-blue-900">
                                      {iteration.generation_metrics.total_tokens?.toLocaleString()}
                                    </span>
                                  </div>
                                  <div className="flex items-center justify-between">
                                    <span className="text-blue-700 text-[10px]">Prompt:</span>
                                    <span className="font-medium text-blue-900 text-[10px]">
                                      {iteration.generation_metrics.prompt_tokens?.toLocaleString()}
                                    </span>
                                  </div>
                                  <div className="flex items-center justify-between">
                                    <span className="text-blue-700 text-[10px]">Completion:</span>
                                    <span className="font-medium text-blue-900 text-[10px]">
                                      {iteration.generation_metrics.completion_tokens?.toLocaleString()}
                                    </span>
                                  </div>
                                </>
                              )}
                              {iteration.generation_metrics.model && (
                                <div className="pt-1 border-t border-blue-200">
                                  <span className="text-blue-600 text-[10px]">
                                    {iteration.generation_metrics.model}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        )}

                        {/* Validation Metrics */}
                        {iteration.validation_metrics && (
                          <div className="p-3 rounded-lg border border-purple-200 bg-purple-50">
                            <div className="flex items-center gap-1 mb-2">
                              <CheckCircle className="w-3.5 h-3.5 text-purple-600" />
                              <h5 className="text-xs font-semibold text-purple-800">Validation</h5>
                            </div>
                            <div className="space-y-1.5 text-xs">
                              <div className="flex items-center justify-between">
                                <span className="text-purple-700 flex items-center gap-1">
                                  <Clock className="w-3 h-3" />
                                  Time:
                                </span>
                                <span className="font-medium text-purple-900">
                                  {iteration.validation_metrics.time_taken?.toFixed(2)}s
                                </span>
                              </div>
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Generated Code */}
                  {iteration.generated_code && (
                    <div>
                      <h4 className="text-sm font-medium text-gray-700 mb-2">
                        Generated Code
                      </h4>
                      <div className="rounded-lg overflow-hidden border border-gray-200">
                        <SyntaxHighlighter
                          language="python"
                          style={vscDarkPlus}
                          customStyle={{
                            margin: 0,
                            fontSize: '0.75rem',
                            maxHeight: '300px',
                          }}
                          showLineNumbers
                        >
                          {iteration.generated_code}
                        </SyntaxHighlighter>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
