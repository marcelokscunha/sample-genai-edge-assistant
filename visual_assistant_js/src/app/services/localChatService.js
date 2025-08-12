// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { IChatService, ChatServiceType } from './chatService.js';

/**
 * Local browser-based chat service implementation
 * 
 * NOTE: This is a placeholder implementation. Full implementation will be done in a later task.
 */
export class LocalChatService extends IChatService {
  constructor(config = {}) {
    super();
    this.config = config;
  }

  /**
   * Send a message to local models and get a response
   * @param {import('../types/chat.js').ChatMessage} message - The message to send
   * @returns {Promise<import('../types/chat.js').ChatMessage>} - The response message
   */
  async sendMessage(message) {
    // TODO: Implement full local chat service in a later task
    throw new Error('Local chat service not yet implemented');
  }

  /**
   * Get the service type
   * @returns {string} - The service type
   */
  getServiceType() {
    return ChatServiceType.LOCAL_BROWSER;
  }
}