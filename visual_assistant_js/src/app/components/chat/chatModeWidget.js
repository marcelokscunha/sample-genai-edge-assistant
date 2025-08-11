// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
'use client';

import React, { useState } from 'react';
import { 
  Container, 
  Header, 
  Box, 
  AppLayout, 
  ContentLayout,
  SpaceBetween 
} from '@cloudscape-design/components';
import ConfigurationPanel from 'src/app/components/playground/configurationPanel';
import CustomHelpPanel from 'src/app/components/playground/helpPanel';
import { useMetaStore } from 'src/app/stores/metaStore';
import TopBar from 'src/app/components/topBar';

/**
 * ChatMode component - placeholder implementation
 * This component will be fully implemented in later tasks
 */
export default function ChatMode() {
  // Panel state management
  const configPanelOpen = useMetaStore((state) => state.configPanelOpen);
  const setConfigPanelOpen = useMetaStore((state) => state.setConfigPanelOpen);
  const [toolsOpen, setToolsOpen] = useState(false);

  const content = (
    <SpaceBetween direction="vertical" size="l">
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