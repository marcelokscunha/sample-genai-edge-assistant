// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { fetchAuthSession } from 'aws-amplify/auth';
import axios from 'axios';
import { IChatService, ChatServiceType } from './chatService.js';

/**
 * Simple SageMaker-based chat service implementation
 */
export class SageMakerChatService extends IChatService {
  constructor(config = {}) {
    super();
    this.endpoint = config.endpoint || process.env.NEXT_PUBLIC_API_GATEWAY_ENDPOINT;
    this.timeout = config.timeout || 30000;
  }

  /**
   * Send a message to the SageMaker chat endpoint
   * @param {import('../types/chat.js').ChatMessage} message - The message to send
   * @returns {Promise<import('../types/chat.js').ChatMessage>} - The response message
   */
  async sendMessage(message) {
    if (!message?.content) {
      throw new Error('Invalid message: content is required');
    }

    try {
      // Get auth token
      const session = await fetchAuthSession();
      const token = session.tokens?.idToken?.toString();
      
      if (!token) {
        throw new Error('Authentication required');
      }

      // Format request for SageMaker
      const requestData = await this.formatRequest(message);
      
      // Make request
      const response = await axios.post(
        `${this.endpoint}/invokesagemakerinference`,
        requestData,
        {
          headers: {
            'Authorization': token,
            'Content-Type': 'application/json',
          },
          timeout: this.timeout,
        }
      );

      // Format response
      return this.formatResponse(response.data, message);
      
    } catch (error) {
      throw new Error(`Chat request failed: ${error.message}`);
    }
  }

  /**
   * Get the service type
   * @returns {string} - The service type
   */
  getServiceType() {
    return ChatServiceType.SAGEMAKER;
  }

  /**
   * Format ChatMessage to SageMaker request
   * @param {import('../types/chat.js').ChatMessage} message - The message to format
   * @returns {Promise<Object>} - Formatted request
   * @private
   */
  async formatRequest(message) {
    const { content } = message;
    
    // Build basic request structure
    const request = {
      messages: [{
        role: 'user',
        content: []
      }],
      options: {
        max_new_tokens: 512,
        temperature: 0.7
      }
    };

    // Add text content
    if (content.text) {
      request.messages[0].content.push({
        type: 'text',
        text: content.text
      });
    }

    // Add image content
    if (content.image) {
      request.messages[0].content.push({
        type: 'image'
      });
      request.image_buffer = await this.processImage(content.image);
    }

    // Add audio content
    if (content.audio) {
      request.messages[0].content.push({
        type: 'audio'
      });
      request.audio_buffer = await this.processAudio(content.audio);
    }

    return request;
  }

  /**
   * Process image content for SageMaker
   * @param {Object} imageContent - Image content from ChatMessage
   * @returns {Promise<ArrayBuffer>} - Processed image buffer
   * @private
   */
  async processImage(imageContent) {
    if (imageContent.buffer) {
      return imageContent.buffer;
    }
    
    if (imageContent.file) {
      return await this.fileToArrayBuffer(imageContent.file);
    }
    
    if (imageContent.url) {
      const response = await fetch(imageContent.url);
      return await response.arrayBuffer();
    }
    
    throw new Error('No valid image data found');
  }

  /**
   * Process audio content for SageMaker
   * @param {Object} audioContent - Audio content from ChatMessage
   * @returns {Promise<ArrayBuffer>} - Processed audio buffer
   * @private
   */
  async processAudio(audioContent) {
    if (audioContent.buffer) {
      return audioContent.buffer;
    }
    
    if (audioContent.blob) {
      return await this.blobToArrayBuffer(audioContent.blob);
    }
    
    if (audioContent.url) {
      const response = await fetch(audioContent.url);
      return await response.arrayBuffer();
    }
    
    throw new Error('No valid audio data found');
  }

  /**
   * Convert File to ArrayBuffer
   * @param {File} file - File object
   * @returns {Promise<ArrayBuffer>} - ArrayBuffer
   * @private
   */
  async fileToArrayBuffer(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsArrayBuffer(file);
    });
  }

  /**
   * Convert Blob to ArrayBuffer
   * @param {Blob} blob - Blob object
   * @returns {Promise<ArrayBuffer>} - ArrayBuffer
   * @private
   */
  async blobToArrayBuffer(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(new Error('Failed to read blob'));
      reader.readAsArrayBuffer(blob);
    });
  }

  /**
   * Convert SageMaker response to ChatMessage format
   * @param {Object} responseData - SageMaker response
   * @param {import('../types/chat.js').ChatMessage} originalMessage - Original user message
   * @returns {import('../types/chat.js').ChatMessage} - Formatted response message
   * @private
   */
  formatResponse(responseData, originalMessage) {
    return {
      id: `response-${Date.now()}-${Math.random().toString(36).substring(2, 9)}`,
      type: 'assistant',
      content: {
        text: responseData.generated_text || 'No response generated'
      },
      timestamp: new Date(),
      status: 'sent',
      metadata: {
        model: responseData.model || 'sagemaker-chat',
        processingTime: responseData.processing_time_ms || 0,
        tokens: responseData.usage?.total_tokens || 0
      }
    };
  }
}