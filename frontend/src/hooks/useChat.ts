// Chat hook for managing conversation state
import { useState, useCallback } from 'react';
import { chatApi } from '../api/client';
import { getCountryCode } from '../services/location';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  workflow?: string;
  serviceUnavailable?: boolean;
  supportUrl?: string;
}

interface ChatState {
  messages: Message[];
  isLoading: boolean;
  error: string | null;
}

export function useChat() {
  const [state, setState] = useState<ChatState>({
    messages: [],
    isLoading: false,
    error: null,
  });

  const sendMessage = useCallback(async (content: string) => {
    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content,
    };

    setState(s => ({
      ...s,
      messages: [...s.messages, userMessage],
      isLoading: true,
      error: null,
    }));

    try {
      const response = await chatApi.send(content, getCountryCode());

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message,
        workflow: response.workflow,
        serviceUnavailable: response.service_unavailable,
        supportUrl: response.support_url,
      };

      setState(s => ({
        ...s,
        messages: [
          ...s.messages.map(message =>
            message.id === userMessage.id
              ? { ...message, workflow: response.workflow }
              : message
          ),
          assistantMessage,
        ],
        isLoading: false,
      }));

      return response;
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to send message';
      setState(s => ({
        ...s,
        isLoading: false,
        error: message,
      }));
    }
  }, []);

  const clearMessages = useCallback(() => {
    setState({
      messages: [],
      isLoading: false,
      error: null,
    });
  }, []);

  return {
    ...state,
    sendMessage,
    clearMessages,
  };
}