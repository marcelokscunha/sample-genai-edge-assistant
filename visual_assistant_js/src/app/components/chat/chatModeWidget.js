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
  ButtonDropdown,
} from '@cloudscape-design/components';
import { getCurrentUser } from 'aws-amplify/auth';
import ConfigurationPanel from '../playground/configurationPanel';
import CustomHelpPanel from '../playground/helpPanel';
import { useMetaStore } from '../../stores/metaStore';
import { useChatStore } from '../../stores/chatStore';
import { useModelSelectionStore } from '../../stores/modelSelectionStore';
import { ChatServiceFactory } from '../../services/chatServiceFactory';
import TopBar from '../topBar';
import ChatMessageList from './chatMessageList';
import ChatInput from './chatInput';

/**
 * ChatMode component - Main container for the chat interface
 * Provides authentication checks, error boundaries, and layout structure
 */
export default function ChatMode() {
  const configPanelOpen = useMetaStore((state) => state.configPanelOpen);
  const setConfigPanelOpen = useMetaStore((state) => state.setConfigPanelOpen);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [authError, setAuthError] = useState(null);

  const [useStreaming, setUseStreaming] = useState(false);

  const { messages, error: chatError, isLoading: chatLoading, clearChat, addMessage, hasMessages } = useChatStore();
  const { currentModel, availableModels, setCurrentModel } = useModelSelectionStore();
  
  const messagesContainerRef = useRef(null);

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



  const handleSendMessage = async (message) => {
    const messageId = `msg_${Date.now()}_${Math.random().toString(36).slice(2, 11)}`;
    const userMessage = { ...message, id: messageId, status: 'sending' };
    addMessage(userMessage);

    try {
      // Create service based on current model
      const service = ChatServiceFactory.createService(currentModel);
      const response = await service.sendMessage(message, useStreaming);
      addMessage(response);
      
      // Update user message to sent
      const { updateMessage } = useChatStore.getState();
      updateMessage(messageId, { status: 'sent' });
    } catch (error) {
      console.error('Failed to send message:', error);
      
      // Update user message to error state
      const { updateMessage } = useChatStore.getState();
      updateMessage(messageId, { 
        status: 'error', 
        error: error.message 
      });
      
      // Add error message
      addMessage({
        type: 'assistant',
        content: { text: `Error: ${error.message}` },
        timestamp: new Date(),
        status: 'error',
      });
    }
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
                  onDismiss={() => setAuthError(null)}
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

  const content = (
    <SpaceBetween direction="vertical" size="l">
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

      <Container
        header={
          <Header
            variant="h2"
            description="Interact with AI using text, images, and audio"
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                <ButtonDropdown
                  items={availableModels.map(m => ({ id: m.id, text: m.name }))}
                  onItemClick={({ detail }) => {
                    const model = availableModels.find(m => m.id === detail.id);
                    setCurrentModel(model);
                  }}
                >
                  {currentModel?.name || 'Select Model'}
                </ButtonDropdown>

                <Button 
                  variant={useStreaming ? 'primary' : 'normal'}
                  onClick={() => setUseStreaming(!useStreaming)}
                >
                  {useStreaming ? 'Streaming ON' : 'Streaming OFF'}
                </Button>

                {hasMessages() && (
                  <Button variant="normal" iconName="refresh" onClick={clearChat}>
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
              onRetry={() => {}}
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