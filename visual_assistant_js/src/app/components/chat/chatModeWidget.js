// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
'use client';

import React, { useState, useEffect, useRef } from 'react';
import {
  Container,
  Header,
  Box,
  AppLayout,
  ContentLayout,
  SpaceBetween,
  Alert,
  Spinner,
  Button,
} from '@cloudscape-design/components';
import { getCurrentUser } from 'aws-amplify/auth';
import ConfigurationPanel from 'src/app/components/playground/configurationPanel';
import CustomHelpPanel from 'src/app/components/playground/helpPanel';
import { useMetaStore } from 'src/app/stores/metaStore';
import { useChatStore } from 'src/app/stores/chatStore';
import TopBar from 'src/app/components/topBar';
import ChatMessageList from './chatMessageList';
import ChatInput from './chatInput';


/**
 * ChatMode component - Main container for the chat interface
 * Provides authentication checks, error boundaries, and layout structure
 */
export default function ChatMode() {
  // Panel state management
  const configPanelOpen = useMetaStore((state) => state.configPanelOpen);
  const setConfigPanelOpen = useMetaStore((state) => state.setConfigPanelOpen);
  const [toolsOpen, setToolsOpen] = useState(false);

  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [authError, setAuthError] = useState(null);

  // Chat state
  const {
    messages,
    error: chatError,
    isLoading: chatLoading,
    clearChat,
    addMessage,
    retryMessage,
    hasMessages,
  } = useChatStore();

  // Ref for scrolling to latest messages
  const messagesContainerRef = useRef(null);

  // Check authentication status on mount
  useEffect(() => {
    const checkAuthentication = async () => {
      try {
        setIsCheckingAuth(true);
        await getCurrentUser();
        setIsAuthenticated(true);
        setAuthError(null);
      } catch (error) {
        console.error('Authentication check failed:', error);
        setIsAuthenticated(false);
        setAuthError('Authentication required. Please sign in to use Chat Mode.');
      } finally {
        setIsCheckingAuth(false);
      }
    };

    checkAuthentication();
  }, []);

  // Error boundary for chat errors
  const handleClearError = () => {
    setAuthError(null);
  };

  // Initialize with welcome message if no messages exist
  useEffect(() => {
    if (isAuthenticated && messages.length === 0) {
      const welcomeMessage = {
        type: 'assistant',
        content: {
          text: 'Hello! I\'m your AI assistant. I can help you with questions, analyze images, and process audio. What would you like to know?',
        },
        timestamp: new Date(),
        status: 'sent',
        metadata: {
          model: 'MODEL_PLACEHOLDER',
        },
      };
      addMessage(welcomeMessage);
    }
  }, [isAuthenticated, messages.length, addMessage]);

  // Handle sending messages
  const handleSendMessage = (message) => {
    // Generate ID for the message
    const messageId = `msg_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;

    // Add message to store with 'sending' status and ID
    const userMessage = { ...message, id: messageId, status: 'sending' };
    addMessage(userMessage);

    // Update user message to 'sent' after a short delay
    setTimeout(() => {
      const { updateMessage } = useChatStore.getState();
      updateMessage(messageId, { status: 'sent' });
    }, 200);

    // TODO: integrate with backend service to get AI response
    // For now, just add a placeholder response
    setTimeout(() => {
      const assistantMessage = {
        type: 'assistant',
        content: {
          text: 'This is a placeholder response.',
        },
        timestamp: new Date(),
        status: 'sent',
        metadata: {
          model: 'placeholder',
          processingTime: 500,
        },
      };
      addMessage(assistantMessage);
    }, 1000);
  };

  // Handle retrying failed messages
  const handleRetryMessage = (messageId) => {
    retryMessage(messageId);
    // TODO: In task 8, implement actual retry logic with SageMaker
  };

  // Handle clearing chat
  const handleClearChat = () => {
    clearChat();
  };

  // Loading state during authentication check
  if (isCheckingAuth) {
    return (
      <>
        <div
          style={{
            backgroundColor: '#000000',
          }}
          id="top-bar"
        >
          <TopBar />
        </div>
        <AppLayout
          navigation={
            <div style={{ padding: '16px' }}>
              <ConfigurationPanel />
            </div>
          }
          navigationWidth={350}
          navigationOpen={configPanelOpen}
          onNavigationChange={({ detail }) => setConfigPanelOpen(detail.open)}
          content={
            <ContentLayout>
              <Container>
                <Box textAlign="center" padding="xl">
                  <Spinner size="large" />
                  <Box variant="p" padding={{ top: 'm' }}>
                    Checking authentication...
                  </Box>
                </Box>
              </Container>
            </ContentLayout>
          }
          tools={<CustomHelpPanel />}
          toolsOpen={toolsOpen}
          onToolsChange={({ detail }) => setToolsOpen(detail.open)}
          contentType="default"
          toolsWidth={300}
        />
      </>
    );
  }

  // Authentication error state
  if (!isAuthenticated || authError) {
    return (
      <>
        <div
          style={{
            backgroundColor: '#000000',
          }}
          id="top-bar"
        >
          <TopBar />
        </div>
        <AppLayout
          navigation={
            <div style={{ padding: '16px' }}>
              <ConfigurationPanel />
            </div>
          }
          navigationWidth={350}
          navigationOpen={configPanelOpen}
          onNavigationChange={({ detail }) => setConfigPanelOpen(detail.open)}
          content={
            <ContentLayout>
              <Container>
                <Alert
                  type="error"
                  header="Authentication Required"
                  dismissible
                  onDismiss={handleClearError}
                >
                  {authError || 'You must be signed in to access Chat Mode. Please authenticate and try again.'}
                </Alert>
              </Container>
            </ContentLayout>
          }
          tools={<CustomHelpPanel />}
          toolsOpen={toolsOpen}
          onToolsChange={({ detail }) => setToolsOpen(detail.open)}
          contentType="default"
          toolsWidth={300}
        />
      </>
    );
  }

  // Main chat interface content
  const content = (
    <SpaceBetween direction="vertical" size="l">
      {/* Global error display */}
      {chatError && (
        <Alert
          type="error"
          header="Chat Error"
          dismissible
          onDismiss={() => useChatStore.getState().setError(null)}
        >
          {chatError}
        </Alert>
      )}

      {/* Chat container */}
      <Container
        header={
          <Header
            variant="h2"
            description="Interact with AI using text, images, and audio"
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                {hasMessages() && (
                  <Button
                    variant="normal"
                    iconName="refresh"
                    onClick={handleClearChat}
                    ariaLabel="Clear chat"
                  >
                    New conversation
                  </Button>
                )}
                {chatLoading && <Spinner />}
              </SpaceBetween>
            }
          >
            Visual Assistant chat
          </Header>
        }
      >
        <SpaceBetween direction="vertical" size="m">
          {/* Chat messages area with fixed height */}
          <div
            ref={messagesContainerRef}
            style={{
              height: '500px',
              border: '1px solid #e9ebed',
              borderRadius: '8px',
              padding: '16px',
              overflowY: 'auto',
              backgroundColor: '#fafbfc'
            }}
          >
            <ChatMessageList
              messages={messages}
              isLoading={chatLoading}
              onRetry={handleRetryMessage}
              messagesContainerRef={messagesContainerRef}
            />
          </div>

          {/* Chat input */}
          <ChatInput
            onSendMessage={handleSendMessage}
            disabled={chatLoading}
            placeholder="Ask me anything..."
          />
        </SpaceBetween>
      </Container>
    </SpaceBetween>
  );

  return (
    <>
      <div
        style={{
          backgroundColor: '#000000',
        }}
        id="top-bar"
      >
        <TopBar />
      </div>
      <AppLayout
        navigation={
          <div style={{ padding: '16px' }}>
            <ConfigurationPanel />
          </div>
        }
        navigationWidth={350}
        navigationOpen={configPanelOpen}
        onNavigationChange={({ detail }) => setConfigPanelOpen(detail.open)}
        content={<ContentLayout>{content}</ContentLayout>}
        tools={<CustomHelpPanel />}
        toolsOpen={toolsOpen}
        onToolsChange={({ detail }) => setToolsOpen(detail.open)}
        contentType="default"
        toolsWidth={300}
      />
    </>
  );
}