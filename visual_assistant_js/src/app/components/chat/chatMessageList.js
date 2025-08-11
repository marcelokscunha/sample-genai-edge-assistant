// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
'use client';

import React, { useEffect } from 'react';
import {
  Box,
  SpaceBetween,
  Button,
  StatusIndicator,
  TextContent,
  FileTokenGroup,
  LiveRegion,
  Container,
} from '@cloudscape-design/components';

/**
 * Create avatar component for chat messages using basic CloudScape components
 */
function ChatBubbleAvatar({ type, loading = false }) {
  const avatarStyle = {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: '14px',
    fontWeight: 'bold',
    flexShrink: 0,
  };

  if (type === 'assistant') {
    return (
      <Box
        style={{
          ...avatarStyle,
          backgroundColor: '#0972d3',
          color: 'white',
        }}
      >
        {loading ? '⏳' : '🤖'}
      </Box>
    );
  }

  return (
    <Box
      style={{
        ...avatarStyle,
        backgroundColor: '#e9ebed',
        color: '#414d5c',
      }}
    >
      👤
    </Box>
  );
}

/**
 * Individual chat message component using basic CloudScape components
 */
function ChatMessage({ message, onRetry }) {
  const isUser = message.type === 'user';
  const hasError = message.status === 'error';
  const isRetrying = message.status === 'retry';
  const isSending = message.status === 'sending';

  // Format timestamp
  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Render message content
  const renderContent = () => {
    const { content } = message;

    return (
      <SpaceBetween direction="vertical" size="xs">
        {/* Text content */}
        {content.text && (
          <div>{content.text}</div>
        )}

        {/* Image content - support multiple images */}
        {content.images && content.images.length > 0 && (
          <SpaceBetween direction="vertical" size="xs">
            {content.images.map((image, index) => (
              <Box key={`image-${index}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={image.url}
                  alt={`Shared image ${index + 1}${image.name ? ` - ${image.name}` : ''}`}
                  style={{
                    maxWidth: '300px',
                    maxHeight: '200px',
                    borderRadius: '8px',
                    objectFit: 'cover',
                  }}
                  onError={(e) => {
                    console.error('Image failed to load:', image.url);
                    e.target.style.display = 'none';
                  }}
                />
                {image.name && (
                  <Box variant="small" color="text-body-secondary" padding={{ top: 'xxs' }}>
                    {image.name}
                  </Box>
                )}
              </Box>
            ))}
          </SpaceBetween>
        )}

        {/* Legacy single image support */}
        {content.image && content.image.url && !content.images && (
          <Box>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={content.image.url}
              alt="Shared image"
              style={{
                maxWidth: '300px',
                maxHeight: '200px',
                borderRadius: '8px',
                objectFit: 'cover',
              }}
              onError={(e) => {
                console.error('Image failed to load:', content.image.url);
                e.target.style.display = 'none';
              }}
            />
          </Box>
        )}

        {/* Audio content - support multiple audio files */}
        {content.audios && content.audios.length > 0 && (
          <SpaceBetween direction="vertical" size="xs">
            {content.audios.map((audio, index) => (
              <Box key={`audio-${index}`}>
                <audio
                  controls
                  style={{ maxWidth: '300px' }}
                  preload="metadata"
                >
                  <source src={audio.url} type="audio/wav" />
                  <source src={audio.url} type="audio/mp3" />
                  <source src={audio.url} type="audio/m4a" />
                  Your browser does not support the audio element.
                </audio>
                <Box variant="small" color="text-body-secondary" padding={{ top: 'xxs' }}>
                  {audio.name}
                  {audio.duration && ` • Duration: ${Math.round(audio.duration)}s`}
                </Box>
              </Box>
            ))}
          </SpaceBetween>
        )}

        {/* Legacy single audio support */}
        {content.audio && content.audio.url && !content.audios && (
          <Box>
            <audio
              controls
              style={{ maxWidth: '300px' }}
              preload="metadata"
            >
              <source src={content.audio.url} type="audio/wav" />
              <source src={content.audio.url} type="audio/mp3" />
              Your browser does not support the audio element.
            </audio>
            {content.audio.duration && (
              <Box variant="small" color="text-body-secondary" padding={{ top: 'xxs' }}>
                Duration: {Math.round(content.audio.duration)}s
              </Box>
            )}
          </Box>
        )}

        {/* Files if any */}
        {content.files && content.files.length > 0 && (
          <Box>
            <Box variant="small" color="text-body-secondary" padding={{ bottom: 'xs' }}>
              Attached files:
            </Box>
            <FileTokenGroup
              readOnly
              items={content.files.map((fileData, index) => ({
                file: fileData.file || fileData,
                key: `file-${index}-${fileData.name || 'unknown'}`
              }))}
              limit={3}
              onDismiss={() => {/* read only */ }}
              alignment="horizontal"
              showFileThumbnail={false} // Disable thumbnails to avoid empty src issues
              i18nStrings={{
                removeFileAriaLabel: index => `Remove file ${index + 1}`,
                limitShowFewer: 'Show fewer files',
                limitShowMore: 'Show more files',
                errorIconAriaLabel: 'Error',
                warningIconAriaLabel: 'Warning',
              }}
            />
          </Box>
        )}
      </SpaceBetween>
    );
  };

  // Chat bubble container style
  const bubbleStyle = {
    maxWidth: '80%',
    marginBottom: '16px',
    marginLeft: isUser ? 'auto' : '0',
    marginRight: isUser ? '0' : 'auto',
  };

  // Show loading state for sending/retrying messages
  if (isSending || isRetrying) {
    return (
      <Box style={bubbleStyle}>
        <SpaceBetween direction="horizontal" size="s" alignItems="flex-start">
          <ChatBubbleAvatar type={isUser ? 'user' : 'assistant'} loading={true} />
          <Container
            variant="stacked"
            disableHeaderPaddings
            disableContentPaddings
          >
            <Box padding="s">
              <Box color="text-status-inactive">
                {isRetrying ? 'Retrying...' : 'Sending...'}
              </Box>
            </Box>
          </Container>
        </SpaceBetween>
      </Box>
    );
  }

  return (
    <Box style={bubbleStyle}>
      <SpaceBetween direction="horizontal" size="s" alignItems="flex-start">
        {!isUser && <ChatBubbleAvatar type="assistant" />}

        <Container
          variant={isUser ? 'default' : 'stacked'}
          disableHeaderPaddings
          disableContentPaddings
        >
          <Box padding="s">
            <SpaceBetween direction="vertical" size="xs">
              {/* Message header */}
              <Box display="flex" justifyContent="space-between" alignItems="center">
                <TextContent>
                  <small><strong>{isUser ? 'You' : 'AI Assistant'}</strong></small>
                </TextContent>
                <Box variant="small" color="text-body-secondary">
                  {formatTime(message.timestamp)}
                </Box>
              </Box>

              {/* Message content */}
              {renderContent()}

              {/* Error message */}
              {hasError && message.error && (
                <StatusIndicator type="error">
                  {message.error}
                </StatusIndicator>
              )}

              {/* Actions */}
              {hasError && (
                <Box display="flex" justifyContent="flex-end">
                  <Button
                    variant="link"
                    iconName="refresh"
                    onClick={() => onRetry(message.id)}
                    ariaLabel={`Retry message ${message.id}`}
                  >
                    Retry
                  </Button>
                </Box>
              )}

              {/* Metadata for assistant messages */}
              {!isUser && message.metadata && (
                <Box variant="small" color="text-body-secondary">
                  {message.metadata.processingTime && (
                    <span>Processing: {message.metadata.processingTime}ms</span>
                  )}
                  {message.metadata.tokens && (
                    <span> • Tokens: {message.metadata.tokens}</span>
                  )}
                  {message.metadata.model && (
                    <span> • Model: {message.metadata.model}</span>
                  )}
                </Box>
              )}
            </SpaceBetween>
          </Box>
        </Container>

        {isUser && <ChatBubbleAvatar type="user" />}
      </SpaceBetween>
    </Box>
  );
}

/**
 * Chat message list component using CloudScape demo pattern
 */
export default function ChatMessageList({ messages = [], isLoading = false, onRetry, messagesContainerRef }) {
  const latestMessage = messages[messages.length - 1];

  // Auto-scroll to latest messages - using the ref passed from parent
  useEffect(() => {
    const scrollToBottom = () => {
      if (messagesContainerRef?.current) {
        const container = messagesContainerRef.current;
        container.scrollTop = container.scrollHeight;
      }
    };

    // Use requestAnimationFrame for smoother scrolling
    const timeoutId = setTimeout(() => {
      requestAnimationFrame(scrollToBottom);
    }, 50);

    return () => clearTimeout(timeoutId);
  }, [messages, isLoading, messagesContainerRef]);

  // Handle retry function
  const handleRetry = (messageId) => {
    if (onRetry) {
      onRetry(messageId);
    }
  };

  return (
    <div className="messages" role="region" aria-label="Chat">

      {/* Live region for screen readers */}
      <LiveRegion hidden={true} assertive={latestMessage?.type === 'alert'}>
        {latestMessage?.type === 'alert' && latestMessage.header}
        {latestMessage?.content?.text}
      </LiveRegion>

      {/* Empty state */}
      {messages.length === 0 && !isLoading ? (
        <Box textAlign="center" padding="xl">
          <TextContent>
            <h3>No messages yet</h3>
            <p>Start a conversation by sending a message below.</p>
          </TextContent>
        </Box>
      ) : (
        <SpaceBetween size="xs">
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              message={message}
              onRetry={handleRetry}
            />
          ))}

          {/* Loading indicator for new messages */}
          {isLoading && (
            <Box style={{ maxWidth: '80%', marginBottom: '16px' }}>
              <SpaceBetween direction="horizontal" size="s" alignItems="flex-start">
                <ChatBubbleAvatar type="assistant" loading={true} />
                <Container variant="stacked" disableHeaderPaddings disableContentPaddings>
                  <Box padding="s">
                    <Box color="text-status-inactive">Generating a response</Box>
                  </Box>
                </Container>
              </SpaceBetween>
            </Box>
          )}
        </SpaceBetween>
      )}
    </div>
  );
}