// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { ChatServiceType } from './chatService.js';
import { SageMakerChatService } from './sageMakerChatService.js';
import { LocalChatService } from './localChatService.js';

/**
 * Simple factory for creating chat service instances
 */
export class ChatServiceFactory {
  /**
   * Create a chat service instance based on the specified type
   * @param {string} serviceType - Type from ChatServiceType enum
   * @param {Object} [config] - Optional configuration for the service
   * @returns {import('./chatService.js').IChatService} - Chat service instance
   */
  static createService(serviceType, config = {}) {
    switch (serviceType) {
      case ChatServiceType.SAGEMAKER:
        return new SageMakerChatService(config);
      
      case ChatServiceType.LOCAL_BROWSER:
        return new LocalChatService(config);
      
      default:
        throw new Error(`Unsupported chat service type: ${serviceType}`);
    }
  }
}