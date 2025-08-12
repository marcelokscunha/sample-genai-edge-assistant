// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { ChatServiceType } from './chatService.js';
import { SageMakerChatService } from './sageMakerChatService.js';
import { LocalChatService } from './localChatService.js';

export class ChatServiceFactory {
  static createService(model) {
    if (model.type === 'sagemaker') {
      return new SageMakerChatService();
    } else {
      return new LocalChatService();
    }
  }
}