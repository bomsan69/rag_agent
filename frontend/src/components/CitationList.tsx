'use client';

import { Citation } from '@/types/chat';
import { FileText, ExternalLink } from 'lucide-react';
import { useState } from 'react';

interface CitationListProps {
  citations: Citation[];
}

export default function CitationList({ citations }: CitationListProps) {
  const [expanded, setExpanded] = useState(false);

  if (citations.length === 0) return null;

  const displayCitations = expanded ? citations : citations.slice(0, 2);

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
      <div className="flex items-center gap-2 mb-2">
        <FileText className="w-4 h-4 text-blue-600" />
        <h4 className="text-xs font-semibold text-blue-900">
          Sources ({citations.length})
        </h4>
      </div>

      <div className="space-y-2">
        {displayCitations.map((citation, index) => (
          <div
            key={index}
            className="flex items-start gap-2 text-xs bg-white rounded p-2 hover:bg-blue-50 transition-colors"
          >
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-blue-100 text-blue-700 flex items-center justify-center text-[10px] font-semibold">
              {index + 1}
            </span>
            <div className="flex-1">
              <p className="font-medium text-gray-900">
                {citation.section && citation.section !== 'Unknown'
                  ? citation.section
                  : '2026 Medicare Handbook'}
              </p>
              <p className="text-gray-600">
                Page {citation.page} • {citation.doc_version}
              </p>
            </div>
            <ExternalLink className="w-3 h-3 text-blue-600 flex-shrink-0 mt-0.5" />
          </div>
        ))}
      </div>

      {citations.length > 2 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-2 text-xs text-blue-600 hover:text-blue-700 font-medium"
        >
          {expanded ? 'Show less' : `Show ${citations.length - 2} more`}
        </button>
      )}
    </div>
  );
}
