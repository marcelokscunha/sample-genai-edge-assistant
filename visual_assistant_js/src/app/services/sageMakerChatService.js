// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { SageMakerRuntimeClient, InvokeEndpointCommand, InvokeEndpointWithResponseStreamCommand } from '@aws-sdk/client-sagemaker-runtime';
import { fromCognitoIdentityPool } from '@aws-sdk/credential-providers';
import { IChatService, ChatServiceType } from './chatService.js';

export class SageMakerChatService extends IChatService {
  constructor() {
    super();
    this.endpointName = process.env.NEXT_PUBLIC_CHAT_ENDPOINT_NAME;
    this.region = process.env.NEXT_PUBLIC_AWS_REGION || 'us-east-1';
    this.identityPoolId = process.env.NEXT_PUBLIC_IDENTITY_POOL_ID;
    
    // Initialize SageMaker client
    this.client = new SageMakerRuntimeClient({
      region: this.region,
      credentials: fromCognitoIdentityPool({
        identityPoolId: this.identityPoolId,
      }),
    });
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
    const command = new InvokeEndpointCommand({
      EndpointName: this.endpointName,
      Body: new TextEncoder().encode(body),
      ContentType: 'application/json',
      Accept: 'application/json',
    });

    const response = await this.client.send(command);
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
    const command = new InvokeEndpointWithResponseStreamCommand({
      EndpointName: this.endpointName,
      Body: new TextEncoder().encode(body),
      ContentType: 'application/json',
      Accept: 'application/json',
    });

    const response = await this.client.send(command);
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