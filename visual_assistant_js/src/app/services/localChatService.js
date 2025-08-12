// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

import { IChatService, ChatServiceType } from './chatService.js';

export class LocalChatService extends IChatService {
  async sendMessage(message) {
    throw new Error('Local model not configured, make sure you have a working deployed model');
  }

  getServiceType() {
    return ChatServiceType.LOCAL_BROWSER;
  }
}