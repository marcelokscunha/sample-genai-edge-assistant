// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: MIT-0
import { useEffect, useRef, useState } from 'react';
import { useMetaStore } from 'src/app/stores/metaStore';

export function useSpeechRecognition() {
  const recognition = useRef(null);
  const [isListening, setIsListening] = useState(false);
  const currentModeRef = useRef('playground');

  const voiceControlEnabled = useMetaStore(
    (state) => state.voiceControlEnabled,
  );
  const currentMode = useMetaStore((state) => state.currentMode);
  const setCurrentMode = useMetaStore((state) => state.setCurrentMode);

  useEffect(() => {
    currentModeRef.current = currentMode;
  }, [currentMode]);

  useEffect(() => {
    if (
      !('webkitSpeechRecognition' in window) ||
      !('speechSynthesis' in window)
    ) {
      console.log('This browser does not support the required speech APIs');
      return;
    }

    if (!recognition.current) {
      recognition.current = new webkitSpeechRecognition();
      recognition.current.lang = 'en-US';
      recognition.current.continuous = true;
      console.log('webkitSpeechRecognition is instantiated');

      recognition.current.onresult = function (event) {
        const command =
          event.results[event.results.length - 1][0].transcript.toLowerCase();

        let newMode = null;
        let modeText = '';

        // Handle specific mode commands
        if (command.includes('switch to playground') || command.includes('playground mode')) {
          newMode = 'playground';
          modeText = 'playground mode';
        } else if (command.includes('switch to navigation') || command.includes('navigation mode')) {
          newMode = 'navigation';
          modeText = 'navigation mode';
        } else if (command.includes('switch to chat') || command.includes('chat mode')) {
          newMode = 'chat';
          modeText = 'chat mode';
        } else if (command.includes('switch mode') || command.includes('change mode')) {
          // Cycle through modes: playground -> navigation -> chat -> playground
          const modes = ['playground', 'navigation', 'chat'];
          const currentIndex = modes.indexOf(currentModeRef.current);
          const nextIndex = (currentIndex + 1) % modes.length;
          newMode = modes[nextIndex];
          modeText = `${newMode} mode`;
        }

        if (newMode && newMode !== currentModeRef.current) {
          setCurrentMode(newMode);
          currentModeRef.current = newMode;

          if ('vibrate' in navigator) {
            navigator.vibrate(200);
          }

          const utterance = new SpeechSynthesisUtterance(
            `Switched to ${modeText}`,
          );
          utterance.lang = 'en-US';
          window.speechSynthesis.speak(utterance);
        }
      };

      recognition.current.onend = () => {
        if (isListening) {
          recognition.current.start();
        }
      };
    }

    return () => {
      if (recognition.current) {
        recognition.current.stop();
        setIsListening(false);
      }
    };
  }, []);

  useEffect(() => {
    if (voiceControlEnabled && recognition.current && !isListening) {
      recognition.current.start();
      setIsListening(true);
      const modeText = `${currentMode} mode`;
      const initialUtterance = new SpeechSynthesisUtterance(
        `Voice control enabled. Currently in ${modeText}. Say "switch to playground", "switch to navigation", "switch to chat", or "switch mode" to cycle through modes.`,
      );
      initialUtterance.lang = 'en-US';
      window.speechSynthesis.speak(initialUtterance);
    } else if (!voiceControlEnabled && recognition.current && isListening) {
      recognition.current.stop();
      setIsListening(false);
      const disabledUtterance = new SpeechSynthesisUtterance(
        'Voice control disabled.',
      );
      disabledUtterance.lang = 'en-US';
      window.speechSynthesis.speak(disabledUtterance);
    }
  }, [voiceControlEnabled, currentMode, isListening, setCurrentMode]);

  return;
}
