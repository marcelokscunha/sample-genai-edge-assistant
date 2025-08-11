// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import React from 'react';
import { render, screen } from '@testing-library/react';
import ChatMode from '../chatModeWidget';

describe('ChatMode', () => {
  test('renders chat mode placeholder correctly', () => {
    render(<ChatMode />);

    expect(screen.getByText('Chat Mode')).toBeInTheDocument();
    expect(screen.getByText(/Chat Mode is coming soon/)).toBeInTheDocument();
    expect(screen.getByText(/Text message input and display/)).toBeInTheDocument();
    expect(screen.getByText(/Image upload and sharing/)).toBeInTheDocument();
    expect(screen.getByText(/Audio recording and playback/)).toBeInTheDocument();
    expect(screen.getByText(/Integration with SageMaker LLM endpoint/)).toBeInTheDocument();
  });
});