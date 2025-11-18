import { useState } from 'react';
import { ChevronDown, ChevronRight, CheckCircle, XCircle, Code } from 'lucide-react';
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

  return (
    <div className="card">
      <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center gap-2">
        <Code className="w-5 h-5 text-primary-600" />
        Iteration History
      </h2>

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
