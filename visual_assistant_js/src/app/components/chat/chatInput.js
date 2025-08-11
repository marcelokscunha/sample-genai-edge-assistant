// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
'use client';

import React, { useState, useRef } from 'react';
import {
  Box,
  SpaceBetween,
  PromptInput,
  FileInput,
  FileTokenGroup,
  FileDropzone,
  Link,
  Icon,
} from '@cloudscape-design/components';
import { useFilesDragging } from '@cloudscape-design/components/file-dropzone';

/**
 * File token group i18n strings
 */
const fileTokenGroupI18nStrings = {
  removeFileAriaLabel: index => `Remove file ${index + 1}`,
  limitShowFewer: 'Show fewer files',
  limitShowMore: 'Show more files',
  errorIconAriaLabel: 'Error',
  warningIconAriaLabel: 'Warning',
};

/**
 * Chat input component using CloudScape PromptInput
 */
export default function ChatInput({
  onSendMessage,
  disabled = false,
  placeholder = 'Ask a question',
}) {
  const [prompt, setPrompt] = useState('');
  const [files, setFiles] = useState([]);
  const promptInputRef = useRef(null);
  const { areFilesDragging } = useFilesDragging();

  // Handle prompt send
  const onPromptSend = ({ detail: { value } }) => {
    // Allow sending if there's either text or files
    if ((!value || value.trim().length === 0) && files.length === 0) {
      return;
    }

    if (disabled) {
      return;
    }

    // Process files to create URLs for display
    const processedFiles = files.map(file => {
      const url = URL.createObjectURL(file);
      return {
        file,
        url,
        name: file.name,
        type: file.type,
        size: file.size,
      };
    });

    // Create message content
    const content = {};

    // Only add text if it's not empty
    if (value && value.trim().length > 0) {
      content.text = value.trim();
    }

    // Add image content if there are image files
    const imageFiles = processedFiles.filter(f => f.type.startsWith('image/'));
    if (imageFiles.length > 0) {
      // For now, just show the first image
      content.image = {
        url: imageFiles[0].url,
        file: imageFiles[0].file,
      };
    }

    // Add audio content if there are audio files
    const audioFiles = processedFiles.filter(f => f.type.startsWith('audio/'));
    if (audioFiles.length > 0) {
      // For now, just show the first audio file
      content.audio = {
        url: audioFiles[0].url,
        file: audioFiles[0].file,
        duration: null, // Duration will be determined when the audio loads
      };
    }

    // Create message object
    const chatMessage = {
      type: 'user',
      content,
      timestamp: new Date(),
      status: 'sending',
      files: processedFiles.length > 0 ? processedFiles : undefined,
    };

    // Send message
    if (onSendMessage) {
      onSendMessage(chatMessage);
    }

    // Clear input
    setPrompt('');
    setFiles([]);
  };

  return (
    <>
      {/* During loading, action button looks enabled but functionality is disabled. */}
      {/* This will be fixed once prompt input receives an update where the action button can receive focus while being disabled. */}
      {/* In the meantime, changing aria labels of prompt input and action button to reflect this. */}
      <PromptInput
        ref={promptInputRef}
        onChange={({ detail }) => setPrompt(detail.value)}
        onAction={onPromptSend}
        value={prompt}
        actionButtonAriaLabel={disabled ? 'Send message button - suppressed' : 'Send message'}
        actionButtonIconName="send"
        ariaLabel={disabled ? 'Prompt input - suppressed' : 'Prompt input'}
        placeholder={placeholder}
        autoFocus
        disableSecondaryActionsPaddings
        secondaryActions={
          <Box padding={{ left: 'xxs', top: 'xs' }}>
            <FileInput
              ariaLabel="Upload images (JPEG, PNG) or audio files (MP3, WAV, M4A)"
              variant="icon"
              multiple={true}
              value={files}
              accept=".jpg,.jpeg,.png,.mp3,.wav,.m4a"
              onChange={({ detail }) => {
                // Filter files to only allow JPEG, PNG, MP3, WAV, M4A
                const allowedFiles = detail.value.filter(file => {
                  const type = file.type.toLowerCase();
                  const name = file.name.toLowerCase();

                  return type === 'image/jpeg' ||
                    type === 'image/png' ||
                    type === 'audio/mpeg' ||
                    type === 'audio/mp3' ||
                    type === 'audio/wav' ||
                    type === 'audio/m4a' ||
                    name.match(/\.(jpg|jpeg|png|mp3|wav|m4a)$/);
                });

                if (allowedFiles.length !== detail.value.length) {
                  console.warn('Some files were filtered out. Only JPEG, PNG, MP3, WAV, and M4A files are allowed.');
                }

                setFiles(prev => [...prev, ...allowedFiles]);
              }}
            />
          </Box>
        }
        secondaryContent={
          areFilesDragging ? (
            <FileDropzone
              accept=".jpg,.jpeg,.png,.mp3,.wav,.m4a"
              onChange={({ detail }) => {
                // Filter files to only allow JPEG, PNG, MP3, WAV, M4A
                const allowedFiles = detail.value.filter(file => {
                  const type = file.type.toLowerCase();
                  const name = file.name.toLowerCase();

                  return type === 'image/jpeg' ||
                    type === 'image/png' ||
                    type === 'audio/mpeg' ||
                    type === 'audio/mp3' ||
                    type === 'audio/wav' ||
                    type === 'audio/m4a' ||
                    name.match(/\.(jpg|jpeg|png|mp3|wav|m4a)$/);
                });

                if (allowedFiles.length !== detail.value.length) {
                  console.warn('Some files were filtered out. Only JPEG, PNG, MP3, WAV, and M4A files are allowed.');
                }

                setFiles(prev => [...prev, ...allowedFiles]);
              }}
            >
              <SpaceBetween size="xs" alignItems="center">
                <Icon name="upload" />
                <Box>Drop JPEG, PNG, MP3, WAV, or M4A files here</Box>
              </SpaceBetween>
            </FileDropzone>
          ) : (
            files.length > 0 && (
              <FileTokenGroup
                items={files.map((file, index) => ({
                  file,
                  key: `input-file-${index}-${file.name}`
                }))}
                onDismiss={({ detail }) => {
                  setFiles(files => files.filter((_, index) => index !== detail.fileIndex));
                  if (files.length === 1) {
                    promptInputRef.current?.focus();
                  }
                }}
                limit={3}
                alignment="horizontal"
                showFileThumbnail={false} // Disable thumbnails to avoid empty src issues
                i18nStrings={fileTokenGroupI18nStrings}
              />
            )
          )
        }
      />
      <Box color="text-body-secondary" margin={{ top: 'xs' }} fontSize="body-s">
        Use of this service is subject to the{' '}
        <Link href="#" external variant="primary" fontSize="inherit">
          AWS Responsible AI Policy
        </Link>
        .
      </Box>
    </>
  );
}