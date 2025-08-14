// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { SageMakerRuntimeClient, InvokeEndpointCommand, InvokeEndpointWithResponseStreamCommand } from '@aws-sdk/client-sagemaker-runtime';
import { fetchAuthSession } from 'aws-amplify/auth';
import { IChatService, ChatServiceType } from './chatService.js';

export class SageMakerChatService extends IChatService {
  constructor() {
    super();
    this.endpointName = process.env.NEXT_PUBLIC_CHAT_ENDPOINT_NAME;
    this.region = process.env.NEXT_PUBLIC_AWS_REGION || 'us-east-1';
    this.client = null; // Will be initialized with credentials when needed
  }

  async getClient() {
    if (!this.client) {
      const session = await fetchAuthSession();
      
      if (!session.credentials) {
        throw new Error('No credentials found in auth session. Make sure you are signed in and the identity pool is configured correctly.');
      }
      
      this.client = new SageMakerRuntimeClient({
        region: this.region,
        credentials: session.credentials,
      });
    }
    return this.client;
  }

  async sendMessage(message, streaming = false) {
    if (!this.endpointName) {
      throw new Error('SageMaker endpoint name not configured, make sure you have a working deployed model');
    }

    // Simple payload - just send the text content
    const payload = {
      inputs: message.content.text || '',
      parameters: {
        max_new_tokens: 512,
        temperature: 0.7,
      }
    };

    const body = JSON.stringify(payload);

    if (streaming) {
      return this.invokeEndpointStreaming(body);
    } else {
      return this.invokeEndpoint(body);
    }
  }

  async invokeEndpoint(body) {
    const client = await this.getClient();
    const command = new InvokeEndpointCommand({
      EndpointName: this.endpointName,
      Body: new TextEncoder().encode(body),
      ContentType: 'application/json',
      Accept: 'application/json',
    });

    const response = await client.send(command);
    const responseBody = JSON.parse(new TextDecoder().decode(response.Body));

    return {
      id: `response-${Date.now()}`,
      type: 'assistant',
      content: {
        text: responseBody.generated_text || responseBody[0]?.generated_text || 'No response generated'
      },
      timestamp: new Date(),
      status: 'sent',
      metadata: {
        model: 'sagemaker',
        processingTime: 0,
      }
    };
  }

  async invokeEndpointStreaming(body) {
    const client = await this.getClient();
    const command = new InvokeEndpointWithResponseStreamCommand({
      EndpointName: this.endpointName,
      Body: new TextEncoder().encode(body),
      ContentType: 'application/json',
      Accept: 'application/json',
    });

    const response = await client.send(command);
    let fullText = '';

    // Process the streaming response
    for await (const chunk of response.Body) {
      if (chunk.PayloadPart?.Bytes) {
        const chunkText = new TextDecoder().decode(chunk.PayloadPart.Bytes);
        try {
          const chunkData = JSON.parse(chunkText);
          if (chunkData.token?.text) {
            fullText += chunkData.token.text;
          }
        } catch (e) {
          // If not JSON, treat as plain text
          fullText += chunkText;
        }
      }
    }

    return {
      id: `response-${Date.now()}`,
      type: 'assistant',
      content: {
        text: fullText || 'No response generated'
      },
      timestamp: new Date(),
      status: 'sent',
      metadata: {
        model: 'sagemaker-streaming',
        processingTime: 0,
      }
    };
  }

  getServiceType() {
    return ChatServiceType.SAGEMAKER;
  }
}