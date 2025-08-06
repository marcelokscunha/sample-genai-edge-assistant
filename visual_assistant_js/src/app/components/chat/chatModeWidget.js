// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
'use client';

import React from 'react';
import { Container, Header, Box } from '@cloudscape-design/components';

/**
 * ChatMode component - placeholder implementation
 * This component will be fully implemented in later tasks
 */
export default function ChatMode() {
  return (
    <Container
      header={
        <Header variant="h2">
          Chat Mode
        </Header>
      }
    >
      <Box padding="l">
        <p>Chat Mode is coming soon! This is a placeholder component that will be fully implemented in upcoming tasks.</p>
        <p>Features to be implemented:</p>
        <ul>
          <li>Text message input and display</li>
          <li>Image upload and sharing</li>
          <li>Audio recording and playback</li>
          <li>Integration with SageMaker LLM endpoint</li>
        </ul>
      </Box>
    </Container>
  );
}