'use client';

import { Message } from '@/types/chat';
import { formatTimestamp } from '@/lib/utils';
import { User, Bot, CheckCircle2, AlertCircle, Info } from 'lucide-react';

interface MessageBubbleProps {
  message: Message;
}

// URL을 링크로 변환하는 함수
function linkifyContent(text: string): React.ReactNode[] {
  // split용 정규식 (캡처 그룹으로 URL도 결과에 포함)
  const splitRegex = /(https?:\/\/[^\s<]+[^\s<.,;:!?)\]'"」』】》>])/g;
  const parts = text.split(splitRegex);

  return parts.map((part, index) => {
    // URL 체크용 정규식 (g 플래그 없이 사용)
    const isUrl = /^https?:\/\//.test(part);
    if (isUrl) {
      return (
        <a
          key={index}
          href={part}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 underline break-all"
        >
          {part}
        </a>
      );
    }
    return part;
  });
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  const getConfidenceColor = (confidence?: string) => {
    switch (confidence) {
      case 'high':
        return 'text-green-600';
      case 'medium':
        return 'text-yellow-600';
      case 'low':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  const getConfidenceIcon = (confidence?: string) => {
    switch (confidence) {
      case 'high':
        return <CheckCircle2 className="w-4 h-4" />;
      case 'medium':
        return <Info className="w-4 h-4" />;
      case 'low':
        return <AlertCircle className="w-4 h-4" />;
      default:
        return null;
    }
  };

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : 'flex-row'} mb-6`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
          isUser ? 'bg-primary-600' : 'bg-gray-700'
        }`}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>

      {/* Message Content */}
      <div className={`flex-1 max-w-[85%] md:max-w-[75%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-primary-600 text-white rounded-tr-sm'
              : 'bg-gray-100 text-gray-900 rounded-tl-sm'
          }`}
        >
          <div className="prose prose-sm max-w-none">
            <p className="whitespace-pre-wrap leading-relaxed">
              {linkifyContent(message.content)}
            </p>
          </div>

          {message.isStreaming && (
            <div className="flex items-center gap-1 mt-2">
              <div className="w-2 h-2 bg-current rounded-full animate-pulse" />
              <div className="w-2 h-2 bg-current rounded-full animate-pulse delay-75" />
              <div className="w-2 h-2 bg-current rounded-full animate-pulse delay-150" />
            </div>
          )}
        </div>

        {/* Metadata */}
        {!isUser && (
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-500 px-2">
            <span>{formatTimestamp(message.timestamp)}</span>
            {message.confidence && (
              <>
                <span>•</span>
                <div className={`flex items-center gap-1 ${getConfidenceColor(message.confidence)}`}>
                  {getConfidenceIcon(message.confidence)}
                  <span className="capitalize">{message.confidence} confidence</span>
                </div>
              </>
            )}
          </div>
        )}

        {/* Disclaimer for assistant messages */}
        {!isUser && !message.isStreaming && (
          <div className="mt-3 px-3 py-2 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-800">
            <strong>💡 참고하세요:</strong> 이 정보는 도움을 드리기 위한 안내입니다.
            중요한 결정을 하실 때는 Medicare 공식 기관(1-800-MEDICARE)이나 전문가와 상담하시는 것이 좋습니다.
          </div>
        )}
      </div>
    </div>
  );
}
