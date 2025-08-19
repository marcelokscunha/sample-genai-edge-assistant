// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0

/**
 * Utility for processing multimodal content (text, images, audio) for backend services
 */

/**
 * Convert file to base64 data URI efficiently
 * @param {File|ArrayBuffer|Blob} source - Source to convert
 * @param {string} mimeType - MIME type for the data URI
 * @returns {Promise<string>} Base64 data URI
 */
async function toBase64DataUri(source, mimeType) {
  let arrayBuffer;
  
  if (source instanceof ArrayBuffer) {
    arrayBuffer = source;
  } else if (source instanceof File || source instanceof Blob) {
    arrayBuffer = await source.arrayBuffer();
  } else {
    throw new Error('Unsupported source type for base64 conversion');
  }
  
  // More efficient conversion for large files
  const uint8Array = new Uint8Array(arrayBuffer);
  const chunkSize = 8192;
  let binaryString = '';
  
  for (let i = 0; i < uint8Array.length; i += chunkSize) {
    const chunk = uint8Array.slice(i, i + chunkSize);
    binaryString += String.fromCharCode(...chunk);
  }
  
  const base64 = btoa(binaryString);
  return `data:${mimeType};base64,${base64}`;
}

/**
 * Process images for backend consumption
 * @param {Array} images - Array of image objects with buffer, url, file properties
 * @returns {Promise<Array>} Array of processed image content items
 */
export async function processImagesForBackend(images) {
  const content = [];
  
  for (const image of images) {
    try {
      let dataUri;
      
      // Try buffer first (most reliable)
      if (image.buffer) {
        dataUri = await toBase64DataUri(image.buffer, image.file.type);
      }
      // Fallback to existing data URI
      else if (image.url?.startsWith('data:')) {
        dataUri = image.url;
      }
      // Fallback to converting from blob URL
      else if (image.url && image.file) {
        const response = await fetch(image.url);
        const blob = await response.blob();
        dataUri = await toBase64DataUri(blob, image.file.type);
      }
      else {
        throw new Error('No valid image source found');
      }
      
      content.push({
        type: "image",
        value: dataUri
      });
      
    } catch (error) {
      console.error('Failed to process image:', error);
      // Skip this image rather than failing the entire request
    }
  }
  
  return content;
}

/**
 * Process multimodal message content for backend services
 * Converts images to base64 data URIs and formats text for backend consumption
 * @param {Object} messageContent - Message content with text, images, audios properties
 * @param {string} [messageContent.text] - Text content
 * @param {Array} [messageContent.images] - Array of image objects with buffer/url/file
 * @param {Array} [messageContent.audios] - Array of audio objects (future use)
 * @returns {Promise<Array>} Array of content items formatted for backend
 */
export async function processMultimodalContent(messageContent) {
  const content = [];
  
  // Add images first (order matters for some models)
  if (messageContent.images?.length > 0) {
    const imageContent = await processImagesForBackend(messageContent.images);
    content.push(...imageContent);
  }
  
  // Add text content
  if (messageContent.text?.trim()) {
    content.push({
      type: "text",
      value: messageContent.text.trim()
    });
  }
  
  // TODO: Add audio processing when needed
  // if (messageContent.audios?.length > 0) {
  //   const audioContent = await processAudiosForBackend(messageContent.audios);
  //   content.push(...audioContent);
  // }
  
  return content;
}