// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Service type enumeration for chat backends
 */
export const ChatServiceType = {
  SAGEMAKER: 'sagemaker',
  LOCAL_BROWSER: 'local_browser'
};

/**
 * Simple interface for chat service implementations
 */
export class IChatService {
  /**
   * Send a message to the chat service and get a response
   * @param {import('../types/chat.js').ChatMessage} message - The message to send
   * @returns {Promise<import('../types/chat.js').ChatMessage>} - The response message
   */
  async sendMessage(message) {
    throw new Error('sendMessage method must be implemented by subclass');
  }

  /**
   * Get the service type
   * @returns {string} - The service type from ChatServiceType enum
   */
  getServiceType() {
    throw new Error('getServiceType method must be implemented by subclass');
  }
}