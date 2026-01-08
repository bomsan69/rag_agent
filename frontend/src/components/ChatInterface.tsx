'use client';

import { useState, useRef, useEffect } from 'react';
import { Message } from '@/types/chat';
import { apiClient } from '@/lib/api';
import { generateSessionId } from '@/lib/utils';
import MessageBubble from './MessageBubble';
import ChatInput from './ChatInput';
import { AlertCircle } from 'lucide-react';

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState(() => generateSessionId());
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = async (content: string) => {
    setError(null);

    // Add user message
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // Create assistant message placeholder
      const assistantMessageId = `assistant-${Date.now()}`;
      const assistantMessage: Message = {
        id: assistantMessageId,
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };

      setMessages((prev) => [...prev, assistantMessage]);

      // Stream response
      let fullResponse = '';

      for await (const chunk of apiClient.chatStream({
        session_id: sessionId,
        user_query: content,
        doc_version: '2026',
        stream: true,
      })) {
        fullResponse += chunk;

        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantMessageId
              ? { ...msg, content: fullResponse }
              : msg
          )
        );
      }

      // Mark streaming as complete (no need for second API call)
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantMessageId
            ? {
                ...msg,
                isStreaming: false,
              }
            : msg
        )
      );
    } catch (err) {
      console.error('Error sending message:', err);
      setError(
        err instanceof Error ? err.message : 'Failed to send message. Please try again.'
      );

      // Remove the streaming placeholder on error
      setMessages((prev) => prev.filter((msg) => !msg.isStreaming));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-gradient-to-b from-gray-50 to-white">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-4 shadow-sm">
        <div className="max-w-4xl mx-auto">
          <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                <span className="text-3xl">🏥</span>
                Medicare AI Assistant
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                Your guide to Medicare Handbook 2026
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-gray-500 hidden sm:inline">Supported:</span>
              <div className="flex gap-1 flex-wrap">
                <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full whitespace-nowrap">
                  🇺🇸 English
                </span>
                <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs font-medium rounded-full whitespace-nowrap">
                  🇰🇷 한국어
                </span>
              </div>
            </div>
          </div>
        </div>
      </header>

      {/* Messages Area */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto px-4 py-6"
      >
        <div className="max-w-4xl mx-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-12">
              <div className="w-20 h-20 bg-primary-100 rounded-full flex items-center justify-center mb-4">
                <span className="text-4xl">💬</span>
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">
                Medicare 도우미에 오신 것을 환영합니다
              </h2>
              <p className="text-gray-600 max-w-md mb-6 text-base leading-relaxed">
                Medicare에 대해 궁금하신 것을 편하게 물어보세요.
                쉽게 설명해 드리겠습니다.
              </p>
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 max-w-md mb-4">
                <p className="text-sm text-blue-900 leading-relaxed">
                  <strong>✓</strong> 메디케어 핸드북 기반으로 답변<br />
                  <strong>✓</strong> 핸드북에 없는 내용은 일반 지식 활용<br />
                  <strong>✓</strong> 쉬운 말로 자세히 설명<br />
                  <strong>✓</strong> 출처를 명확히 표시
                </p>
              </div>
              <div className="bg-green-50 border border-green-200 rounded-lg p-4 max-w-md">
                <p className="text-sm text-green-900 font-medium mb-2">
                  🌍 영어와 한국어로 물어보세요
                </p>
                <p className="text-sm text-green-800">
                  <strong>English</strong>나 <strong>한국어</strong>로 질문하시면
                  같은 언어로 답변해 드립니다!
                </p>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message) => (
                <MessageBubble key={message.id} message={message} />
              ))}
              <div ref={messagesEndRef} />
            </>
          )}

          {/* Error Message */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
              <div>
                <h3 className="text-sm font-semibold text-red-900">Error</h3>
                <p className="text-sm text-red-700 mt-1">{error}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Area */}
      <ChatInput
        onSend={handleSendMessage}
        disabled={isLoading}
        isLoading={isLoading}
      />
    </div>
  );
}
