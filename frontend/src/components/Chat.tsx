'use client';

import { useState, useRef, useEffect } from 'react';
import { Message, Conversation } from '@/types/chat';
import Sidebar from './Sidebar';

const STORAGE_KEY = 'chat_conversations';

function generateId(): string {
  return Math.random().toString(36).substring(2) + Date.now().toString(36);
}

function createNewConversation(): Conversation {
  return {
    id: generateId(),
    title: 'New Chat',
    messages: [],
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };
}

export default function Chat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] =
    useState<Conversation | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [editingMessageId, setEditingMessageId] = useState<number | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Load conversations from local storage
  useEffect(() => {
    const savedConversations = localStorage.getItem(STORAGE_KEY);
    if (savedConversations) {
      const parsed = JSON.parse(savedConversations);
      setConversations(parsed);
      if (parsed.length > 0) {
        setCurrentConversation(parsed[0]);
      }
    } else {
      const newConversation = createNewConversation();
      setConversations([newConversation]);
      setCurrentConversation(newConversation);
    }
  }, []);

  // Save conversations to local storage
  useEffect(() => {
    if (conversations.length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
    }
  }, [conversations]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [currentConversation?.messages]);

  const updateConversation = (conversation: Conversation) => {
    setConversations((prev) =>
      prev.map((conv) => (conv.id === conversation.id ? conversation : conv))
    );
    setCurrentConversation(conversation);
  };

  const handleNewChat = () => {
    const newConversation = createNewConversation();
    setConversations((prev) => [newConversation, ...prev]);
    setCurrentConversation(newConversation);
    setInput('');
    setEditingMessageId(null);
  };

  const handleDeleteConversation = (conversationId: string) => {
    setConversations((prev) =>
      prev.filter((conv) => conv.id !== conversationId)
    );
    if (currentConversation?.id === conversationId) {
      const remaining = conversations.filter(
        (conv) => conv.id !== conversationId
      );
      setCurrentConversation(
        remaining.length > 0 ? remaining[0] : createNewConversation()
      );
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading || !currentConversation) return;

    const newMessage: Message = {
      id: currentConversation.messages.length,
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };

    const updatedConversation = {
      ...currentConversation,
      messages: [...currentConversation.messages, newMessage],
      updatedAt: Date.now(),
      title:
        currentConversation.messages.length === 0
          ? input.slice(0, 30)
          : currentConversation.title,
    };

    updateConversation(updatedConversation);
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8002/api/v1/qa/answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: input }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();
      const assistantMessage: Message = {
        id: updatedConversation.messages.length,
        role: 'assistant',
        content: data.answer,
        timestamp: Date.now(),
      };

      updateConversation({
        ...updatedConversation,
        messages: [...updatedConversation.messages, assistantMessage],
        updatedAt: Date.now(),
      });
    } catch (error) {
      const errorMessage: Message = {
        id: updatedConversation.messages.length,
        role: 'assistant',
        content: 'Sorry, there was an error processing your request.',
        timestamp: Date.now(),
      };

      updateConversation({
        ...updatedConversation,
        messages: [...updatedConversation.messages, errorMessage],
        updatedAt: Date.now(),
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleEdit = (messageId: number) => {
    if (!currentConversation) return;
    const message = currentConversation.messages.find(
      (m) => m.id === messageId
    );
    if (message && message.role === 'user') {
      setEditingMessageId(messageId);
      setInput(message.content);
    }
  };

  const handleUpdate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (
      !input.trim() ||
      isLoading ||
      editingMessageId === null ||
      !currentConversation
    )
      return;

    const updatedMessages = currentConversation.messages.filter(
      (m) => m.id <= editingMessageId && m.role === 'user'
    );

    const newMessage: Message = {
      id: editingMessageId,
      role: 'user',
      content: input,
      timestamp: Date.now(),
    };

    const updatedConversation = {
      ...currentConversation,
      messages: [...updatedMessages, newMessage],
      updatedAt: Date.now(),
    };

    updateConversation(updatedConversation);
    setInput('');
    setEditingMessageId(null);
    setIsLoading(true);

    try {
      const response = await fetch('http://localhost:8002/api/v1/qa/answer', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ question: input }),
      });

      if (!response.ok) {
        throw new Error('Failed to get response');
      }

      const data = await response.json();
      const assistantMessage: Message = {
        id: updatedConversation.messages.length,
        role: 'assistant',
        content: data.answer,
        timestamp: Date.now(),
      };

      updateConversation({
        ...updatedConversation,
        messages: [...updatedConversation.messages, assistantMessage],
        updatedAt: Date.now(),
      });
    } catch (error) {
      const errorMessage: Message = {
        id: updatedConversation.messages.length,
        role: 'assistant',
        content: 'Sorry, there was an error processing your request.',
        timestamp: Date.now(),
      };

      updateConversation({
        ...updatedConversation,
        messages: [...updatedConversation.messages, errorMessage],
        updatedAt: Date.now(),
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-[#202123]">
      <Sidebar
        conversations={conversations}
        currentConversation={currentConversation}
        onNewChat={handleNewChat}
        onSelectConversation={setCurrentConversation}
        onDeleteConversation={handleDeleteConversation}
      />

      <div className="flex-1 flex flex-col bg-[#343541]">
        {/* Header */}
        <div className="h-12 border-b border-white/10 flex items-center justify-between px-4 bg-[#343541]/90 backdrop-blur">
          <h1 className="text-white/90 text-sm font-medium">AI Assistant</h1>
          <div className="flex items-center gap-2">
            <button className="p-2 hover:bg-white/10 rounded-lg">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                className="text-white/80"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                />
              </svg>
            </button>
            <button className="p-2 hover:bg-white/10 rounded-lg">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                className="text-white/80"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 6v6m0 0v6m0-6h6m-6 0H6"
                />
              </svg>
            </button>
          </div>
        </div>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto">
          {currentConversation?.messages.length === 0 ? (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-3">
                <h2 className="text-2xl font-semibold text-white/80">
                  How can I help you today?
                </h2>
                <p className="text-sm text-white/50">
                  Ask me anything about the documents you've shared
                </p>
              </div>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto py-4 space-y-6">
              {currentConversation?.messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  <div
                    className={`max-w-[85%] p-4 rounded-2xl ${
                      message.role === 'user'
                        ? 'bg-[#2970FF] text-white'
                        : 'bg-[#444654] text-white/90'
                    }`}
                  >
                    <div className="flex justify-between items-start gap-2">
                      <p className="whitespace-pre-wrap text-sm leading-relaxed">
                        {message.content}
                      </p>
                      {message.role === 'user' && (
                        <button
                          onClick={() => handleEdit(message.id)}
                          className="opacity-0 group-hover:opacity-100 text-xs text-white/60 hover:text-white ml-2 -mt-1"
                        >
                          Edit
                        </button>
                      )}
                    </div>
                    <div className="mt-2 text-[10px] text-white/40">
                      {new Date(message.timestamp).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>
                </div>
              ))}
              {isLoading && (
                <div className="flex justify-start">
                  <div className="bg-[#444654] p-4 rounded-2xl max-w-[85%]">
                    <div className="flex items-center gap-2">
                      <div className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce" />
                      <div
                        className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce"
                        style={{ animationDelay: '0.2s' }}
                      />
                      <div
                        className="w-1.5 h-1.5 bg-white/40 rounded-full animate-bounce"
                        style={{ animationDelay: '0.4s' }}
                      />
                    </div>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="border-t border-white/10 p-4 bg-[#343541]">
          <div className="max-w-3xl mx-auto">
            <form
              onSubmit={editingMessageId !== null ? handleUpdate : handleSubmit}
              className="flex gap-2 items-end"
            >
              <div className="flex-1 bg-[#40414F] rounded-xl">
                <input
                  type="text"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder={
                    editingMessageId !== null
                      ? 'Edit your question...'
                      : 'Message AI Assistant...'
                  }
                  className="w-full bg-transparent text-white/90 text-sm px-4 py-3 focus:outline-none"
                  disabled={isLoading}
                />
              </div>
              <button
                type="submit"
                disabled={isLoading || !input.trim()}
                className={`p-3 rounded-xl ${
                  isLoading || !input.trim()
                    ? 'bg-[#40414F] text-white/40 cursor-not-allowed'
                    : 'bg-[#2970FF] text-white hover:bg-[#2970FF]/90'
                }`}
              >
                <svg
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 12h14M12 5l7 7-7 7"
                  />
                </svg>
              </button>
              {editingMessageId !== null && (
                <button
                  type="button"
                  onClick={() => {
                    setEditingMessageId(null);
                    setInput('');
                  }}
                  className="p-3 bg-[#40414F] text-white/90 rounded-xl hover:bg-[#40414F]/90"
                >
                  Cancel
                </button>
              )}
            </form>
          </div>
        </div>
      </div>
    </div>
  );
}
