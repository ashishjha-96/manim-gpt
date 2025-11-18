import { useState, useEffect } from 'react';
import { Code, Save, CheckCircle, AlertCircle, Copy, Check } from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

export default function CodeEditor({
  code,
  onUpdate,
  validationResult,
  isValidating,
  sessionId
}) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedCode, setEditedCode] = useState(code || '');
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    setEditedCode(code || '');
  }, [code]);

  const handleSave = () => {
    if (onUpdate && sessionId) {
      onUpdate(editedCode);
      setIsEditing(false);
    }
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isValid = validationResult?.is_valid;
  const hasErrors = validationResult?.errors && validationResult.errors.length > 0;
  const hasWarnings = validationResult?.warnings && validationResult.warnings.length > 0;

  return (
    <div className="card">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
          <Code className="w-5 h-5 text-primary-600" />
          Generated Code
          {validationResult && (
            <span className="ml-2">
              {isValid ? (
                <CheckCircle className="w-5 h-5 text-green-500" />
              ) : (
                <AlertCircle className="w-5 h-5 text-red-500" />
              )}
            </span>
          )}
        </h2>

        <div className="flex gap-2">
          <button
            onClick={handleCopy}
            className="btn-secondary text-sm flex items-center gap-1"
            disabled={!code}
          >
            {copied ? (
              <>
                <Check className="w-4 h-4" />
                Copied!
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copy
              </>
            )}
          </button>
          {!isEditing ? (
            <button
              onClick={() => setIsEditing(true)}
              className="btn-secondary text-sm"
              disabled={!code}
            >
              Edit Code
            </button>
          ) : (
            <button
              onClick={handleSave}
              className="btn-primary text-sm flex items-center gap-1"
              disabled={isValidating}
            >
              <Save className="w-4 h-4" />
              {isValidating ? 'Validating...' : 'Save & Validate'}
            </button>
          )}
        </div>
      </div>

      {/* Validation Status */}
      {validationResult && (
        <div className={`mb-4 p-3 rounded-lg ${
          isValid
            ? 'bg-green-50 border border-green-200'
            : 'bg-red-50 border border-red-200'
        }`}>
          <div className="flex items-start gap-2">
            {isValid ? (
              <CheckCircle className="w-5 h-5 text-green-600 mt-0.5 flex-shrink-0" />
            ) : (
              <AlertCircle className="w-5 h-5 text-red-600 mt-0.5 flex-shrink-0" />
            )}
            <div className="flex-1">
              <p className={`font-medium ${isValid ? 'text-green-800' : 'text-red-800'}`}>
                {isValid ? 'Code is valid!' : 'Validation failed'}
              </p>
              {hasErrors && (
                <ul className="mt-2 space-y-1 text-sm text-red-700">
                  {validationResult.errors.map((error, idx) => (
                    <li key={idx} className="flex gap-1">
                      <span className="font-medium">•</span>
                      <span>{error}</span>
                    </li>
                  ))}
                </ul>
              )}
              {hasWarnings && (
                <ul className="mt-2 space-y-1 text-sm text-yellow-700">
                  {validationResult.warnings.map((warning, idx) => (
                    <li key={idx} className="flex gap-1">
                      <span className="font-medium">⚠</span>
                      <span>{warning}</span>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Code Display/Editor */}
      {isEditing ? (
        <textarea
          value={editedCode}
          onChange={(e) => setEditedCode(e.target.value)}
          className="input-field font-mono text-sm w-full min-h-[400px] resize-y"
          spellCheck={false}
        />
      ) : (
        <div className="rounded-lg overflow-hidden border border-gray-200">
          {code ? (
            <SyntaxHighlighter
              language="python"
              style={vscDarkPlus}
              customStyle={{
                margin: 0,
                borderRadius: 0,
                fontSize: '0.875rem',
              }}
              showLineNumbers
            >
              {code}
            </SyntaxHighlighter>
          ) : (
            <div className="p-8 text-center text-gray-400">
              <Code className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>No code generated yet</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
