import React, { useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import { logError } from '@edx/frontend-platform/logging';
import { useIntl } from '@edx/frontend-platform/i18n';
import {
  Button,
  Alert,
  Dropdown,
  ModalLayer,
  ButtonGroup,
  Icon,
  Scrollable,
  Spinner,
  Card,
  Form,
} from '@openedx/paragon';
import {
  Send,
  CheckCircle,
  Warning,
  Close,
  Settings,
  ExpandLess,
} from '@openedx/paragon/icons';

// Import AI services
import {
  callWorkflowService,
  prepareContextData,
  formatErrorMessage,
} from '../services';
import { AIChatMessage, AIModelResponse, PluginContext } from '../types';
import { WORKFLOW_ACTIONS } from '../constants';
import { NO_RESPONSE_MSG } from '../services/constants';

import messages from '../messages';
import './sidebar.scss';

/**
 * AI Sidebar Response Component
 * Displays AI responses in a floating right sidebar
 */

interface AISidebarResponseProps {
  response: string;
  error: string;
  isLoading: boolean;
  onClear: () => void;
  onError: (errorMsg: string) => void;
  showActions?: boolean;
  customMessage?: string;
  contextData?: PluginContext;
}

const AISidebarResponse = ({
  response,
  error,
  isLoading,
  onClear,
  onError,
  showActions = true,
  customMessage,
  contextData = {},
}: AISidebarResponseProps) => {
  const intl = useIntl();
  const [isOpen, setIsOpen] = useState(false);
  const [followUpQuestion, setFollowUpQuestion] = useState('');
  const [chatMessages, setChatMessages] = useState<AIChatMessage[]>([]);
  const [isSendingFollowUp, setIsSendingFollowUp] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(false);

  const chatEndRef = useRef<HTMLDivElement | null>(null);
  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const initialResponseAdded = useRef(false);
  const hasScrolledToBottom = useRef(false);
  const isLoadingOlderMessages = useRef(false);
  const previousMessageCount = useRef(0);
  const [textareaRows, setTextareaRows] = useState(1);

  // Show sidebar when response or error arrives
  useEffect(() => {
    if (!response && !error) { return; }

    if (error) {
      setIsOpen(true);
      return;
    }

    let parsedData;
    let isJson = false;

    try {
      parsedData = JSON.parse(response);
      if (typeof parsedData === 'object' && parsedData !== null) {
        isJson = true;
      }
    } catch (e) {
      isJson = false;
    }

    // --- SCENARIO 1: JSON with message history ---
    if (isJson) {
      if (!initialResponseAdded.current) {
        let rawMessages: AIModelResponse[] = [];

        if (parsedData.messages && Array.isArray(parsedData.messages)) {
          rawMessages = parsedData.messages;
          if (parsedData.metadata) {
            setHasMoreHistory(parsedData.metadata.has_more || false);
          }
        } else if (Array.isArray(parsedData)) {
          rawMessages = parsedData;
        }

        // Formatting
        let formattedMessages: AIChatMessage[] = rawMessages.map((msg, index) => ({
          type: msg.role === 'user' ? 'user' : 'ai',
          content: msg.content,
          timestamp: (msg.timestamp && !Number.isNaN(Date.parse(msg.timestamp)))
            ? msg.timestamp
            : new Date().toISOString(),
          originalIndex: index,
        }));

        // Remove empty messages
        formattedMessages = formattedMessages.filter(
          (msg) => msg.content && String(msg.content).trim().length > 0,
        );

        formattedMessages.sort((a, b) => {
          const dateA = new Date(a.timestamp).getTime();
          const dateB = new Date(b.timestamp).getTime();

          // Primary sort: Time
          if (dateA !== dateB) {
            return dateA - dateB;
          }
          // Tie-breaker: original index from backend array
          return (a?.originalIndex || 0) - (b?.originalIndex || 0);
        });

        setChatMessages(formattedMessages);
        setIsOpen(true);
        initialResponseAdded.current = true;
      }

      // --- SCENARIO 2: Simple text (Streaming) ---
    } else {
      setIsOpen(true);

      initialResponseAdded.current = true;
      setChatMessages((prevMessages) => {
        // First chunk or empty chat
        if (prevMessages.length === 0) {
          return [{
            type: 'ai',
            content: response,
            timestamp: new Date().toISOString(),
          }];
        }

        const lastMessage = prevMessages[prevMessages.length - 1];

        // If the last message is from AI -> update its content
        if (lastMessage.type === 'ai') {
          if (lastMessage.content === response) {
            return prevMessages;
          }

          const updatedMessages = [...prevMessages];
          updatedMessages[updatedMessages.length - 1] = {
            ...lastMessage,
            content: response,
            timestamp: lastMessage.timestamp,
          };
          return updatedMessages;
        }

        // New AI message (after user question)
        return [...prevMessages, {
          type: 'ai',
          content: response,
          timestamp: new Date().toISOString(),
        }];
      });
    }
  }, [response, error]);

  // Auto-scroll to bottom when new messages arrive (but not when loading older messages)
  useEffect(() => {
    // Only scroll to bottom if we're not currently loading older messages
    if (chatEndRef.current && !isLoadingOlderMessages.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
      // Mark that we've scrolled to bottom after initial load
      if (!hasScrolledToBottom.current) {
        setTimeout(() => {
          hasScrolledToBottom.current = true;
        }, 500); // Wait for smooth scroll to complete
      }
    }
  }, [chatMessages, isSendingFollowUp]);

  const handleClearSession = async () => {
    try {
      // Prepare context data
      const preparedContext = prepareContextData({
        ...contextData,
      });

      // Make API call
      await callWorkflowService({
        context: preparedContext,
        payload: {
          action: WORKFLOW_ACTIONS.CLEAR_SESSION,
          requestId: `ai-request-${Date.now()}`,
        },
      });
    } catch (err) {
      logError('[AISidebarResponse] Clear session error:', err);
    }
  };

  /**
   * Load older messages when scrolling up
   */
  const handleLoadMoreHistory = async () => {
    if (!hasMoreHistory || isLoadingHistory) {
      return;
    }

    setIsLoadingHistory(true);
    isLoadingOlderMessages.current = true;

    try {
      // Save current scroll position before loading
      const scrollContainer = chatContainerRef.current;
      const scrollHeightBefore = scrollContainer?.scrollHeight || 0;
      const scrollTopBefore = scrollContainer?.scrollTop || 0;

      // Get current message count
      const currentMessageCount = chatMessages.length;

      // Prepare context data
      const preparedContext = prepareContextData({
        ...contextData,
      });

      // Make API call with lazy_load_chat_history action
      // Pass current message count as user input
      const data = await callWorkflowService({
        context: preparedContext,
        userInput: JSON.stringify({ current_messages: currentMessageCount }),
        payload: {
          action: WORKFLOW_ACTIONS.LAZY_LOAD_CHAT_HISTORY,
          requestId: `ai-request-${Date.now()}`,
        },
      });

      // Parse response
      let parsed;
      try {
        parsed = JSON.parse(data.response || '{}');
      } catch (e) {
        parsed = {};
      }

      // Extract messages from response
      const aIMessages: AIModelResponse[] = parsed.messages || [];

      // Format older messages
      const olderMessages: AIChatMessage[] = (Array.isArray(aIMessages) ? aIMessages : []).map((msg) => ({
        type: msg.role === 'user' ? 'user' : 'ai',
        content: msg.content,
        timestamp: msg.timestamp || new Date().toISOString(),
      }));

      // Only prepend if we got new messages
      if (olderMessages.length > 0) {
        // Prepend older messages to current messages
        setChatMessages(prev => [...olderMessages, ...prev]);

        // Restore scroll position after messages are added
        // Use setTimeout to wait for DOM update
        setTimeout(() => {
          if (scrollContainer) {
            const scrollHeightAfter = scrollContainer.scrollHeight;
            const scrollDiff = scrollHeightAfter - scrollHeightBefore;
            scrollContainer.scrollTop = scrollTopBefore + scrollDiff;
          }
        }, 0);
      }

      // Update metadata from response
      // If no messages were returned or metadata says no more, disable further loading
      if (parsed.metadata) {
        setHasMoreHistory(parsed.metadata.has_more || false);
      } else if (olderMessages.length === 0) {
        // If no metadata and no messages returned, no more history
        setHasMoreHistory(false);
      } else {
        setHasMoreHistory(false);
      }
    } catch (err) {
      logError('[AISidebarResponse] Load more history error:', err);
      setHasMoreHistory(false);
    } finally {
      setIsLoadingHistory(false);
      // Reset flag after a small delay to ensure scroll position is restored
      setTimeout(() => {
        isLoadingOlderMessages.current = false;
      }, 100);
    }
  };

  /**
   * Handle scroll event to detect when user reaches top
   */
  const handleScroll = (e) => {
    const { scrollTop } = e.target;

    // Only trigger lazy load after initial scroll to bottom is complete
    // This prevents loading during the initial auto-scroll
    if (scrollTop < 50 && hasMoreHistory && !isLoadingHistory && hasScrolledToBottom.current) {
      handleLoadMoreHistory();
    }
  };

  /**
   * Clear response and close sidebar (shows request component again)
   */
  const handleClearAndClose = async () => {
    await handleClearSession();
    setIsOpen(false);
    setFollowUpQuestion('');
    setChatMessages([]);
    setHasMoreHistory(false);
    setIsLoadingHistory(false);
    initialResponseAdded.current = false;
    hasScrolledToBottom.current = false;
    isLoadingOlderMessages.current = false;
    previousMessageCount.current = 0;
    if (onClear) {
      onClear();
    }
  };

  const handleClose = () => {
    setIsOpen(false);
    setFollowUpQuestion('');
    setChatMessages([]);
    setHasMoreHistory(false);
    setIsLoadingHistory(false);
    initialResponseAdded.current = false;
    hasScrolledToBottom.current = false;
    isLoadingOlderMessages.current = false;
    previousMessageCount.current = 0;
    if (onClear) {
      onClear();
    }
  };

  const displayTitle = customMessage || intl.formatMessage(messages['ai.extensions.sidebar.default.title']);

  /**
   * Handle follow-up question submission
   * Makes direct API call instead of using onAskAgain
   */
  const handleFollowUpSubmit = async () => {
    if (!followUpQuestion.trim()) {
      return;
    }

    const userMessage = followUpQuestion.trim();
    const aiPlaceholder: AIChatMessage = {
      type: 'ai',
      content: '',
      timestamp: '',
    };

    setChatMessages(prev => [...prev, {
      type: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    }, aiPlaceholder,
    ]);

    setFollowUpQuestion('');
    setTextareaRows(1);
    setIsSendingFollowUp(true);

    try {
      // Prepare context data
      const preparedContext = prepareContextData({
        ...contextData,
      });

      let buffer = '';
      let wasStreaming = false;

      // Make API call
      const data = await callWorkflowService({
        context: preparedContext,
        userInput: userMessage,
        payload: {
          action: WORKFLOW_ACTIONS.RUN,
          requestId: `ai-request-${Date.now()}`,
        },
        onStreamChunk: (chunk) => {
          buffer += chunk;
          wasStreaming = true;
          setIsSendingFollowUp(false);

          setChatMessages(prev => {
            const newMsgs = [...prev];
            const lastIndex = newMsgs.length - 1;
            // Update only the last message content (the AI placeholder)
            if (newMsgs[lastIndex] && newMsgs[lastIndex].type === 'ai') {
              let validTimestamp = newMsgs[lastIndex].timestamp;
              if (!validTimestamp || Number.isNaN(Date.parse(validTimestamp))) {
                validTimestamp = new Date().toISOString();
              }
              newMsgs[lastIndex] = {
                ...newMsgs[lastIndex],
                content: buffer,
                type: 'ai',
                timestamp: validTimestamp,
              };
            }
            return newMsgs;
          });
        },
      });

      // Only add a new message if streaming didn't occur
      // If streaming occurred, the message is already updated via onStreamChunk
      if (!wasStreaming) {
        // Extract response from various possible fields
        let aiResponse = '';
        if (data.response) {
          aiResponse = data.response;
        } else if (data.message) {
          aiResponse = data.message;
        } else if (data.content) {
          aiResponse = data.content;
        } else if (data.result) {
          aiResponse = data.result;
        } else {
          aiResponse = NO_RESPONSE_MSG;
        }

        // Update the AI placeholder with the final response
        setChatMessages(prev => {
          const newMsgs = [...prev];
          const lastIndex = newMsgs.length - 1;
          if (newMsgs[lastIndex] && newMsgs[lastIndex].type === 'ai') {
            let validTimestamp = newMsgs[lastIndex].timestamp;
            if (!validTimestamp || Number.isNaN(Date.parse(validTimestamp))) {
              validTimestamp = new Date().toISOString();
            }
            newMsgs[lastIndex] = {
              ...newMsgs[lastIndex],
              content: aiResponse,
              timestamp: validTimestamp,
            };
          }
          return newMsgs;
        });
      }
    } catch (err) {
      logError('[AISidebarResponse] Follow-up error:', err);
      const userFriendlyError = formatErrorMessage(err);
      // Add error message to chat
      setChatMessages(prev => [...prev, {
        type: 'error',
        content: userFriendlyError,
        timestamp: new Date().toISOString(),
      }]);
    } finally {
      setIsSendingFollowUp(false);
    }
  };

  /**
   * Handle textarea auto-resize based on content
   */
  const handleTextareaChange = (e) => {
    const { value } = e.target;
    setFollowUpQuestion(value);

    // If content is empty, reset to 1 row
    if (!value.trim()) {
      setTextareaRows(1);
      return;
    }

    // Calculate number of rows needed (max 10)
    const lineHeight = 30; // Approximate line height in pixels
    const maxRows = 10;
    const minRows = 1;

    // Reset height to auto to get accurate scrollHeight
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      const { scrollHeight } = textareaRef.current;
      const calculatedRows = Math.floor(scrollHeight / lineHeight);
      const rows = Math.min(Math.max(calculatedRows, minRows), maxRows);
      setTextareaRows(rows);
    }
  };

  /**
   * Handle Enter key press in textarea
   */
  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleFollowUpSubmit();
    }
  };

  // Don't render if no response or error (loading state is handled by parent component)
  if (!response && !error && chatMessages.length === 0) {
    return null;
  }

  return (
    <ModalLayer
      isOpen={isOpen}
      isBlocking
      // This is a requiered prop for the ModalLayer component. However, we are not using it.
      // The modal is closed by the close button in the header.
      onClose={() => { }}
    >

      {/* Sidebar */}
      <div
        className="vh-100 bg-white right mis-auto w-xs mw-xs d-flex flex-column ai-sidebar-chat"
        role="dialog"
        aria-modal="true"
        aria-label={intl.formatMessage(messages['ai.extensions.sidebar.aria.label'])}
      >
        {/* Header */}
        <div className="d-flex justify-content-between p-3 border bg-light-200">
          <div className="d-flex align-items-center">
            <CheckCircle className="text-success mr-2" aria-hidden="true" />
            <strong style={{ fontSize: '1rem' }}>{displayTitle}</strong>
          </div>
          <ButtonGroup size="sm">
            <Dropdown>
              <Dropdown.Toggle
                variant="light"
                size="sm"
                id="sidebar-settings-dropdown"
                className="p-2"
              >
                <Icon src={Settings} aria-label={intl.formatMessage(messages['ai.extensions.sidebar.settings.label'])} size="sm" />
              </Dropdown.Toggle>
              <Dropdown.Menu>
                <Dropdown.Item onClick={handleClearAndClose}>
                  {intl.formatMessage(messages['ai.extensions.sidebar.clear.chat'])}
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>

            {/* Close button */}
            <Button
              variant="secondary"
              onClick={handleClose}
              aria-label={intl.formatMessage(messages['ai.extensions.sidebar.close.label'])}
            >
              <Icon src={Close} aria-hidden="true" size="sm" />
            </Button>
          </ButtonGroup>
        </div>

        {/* Content */}
        <Scrollable
          ref={chatContainerRef}
          onScroll={handleScroll}
          className="flex-grow-1 p-3"
        >
          {/* Loading indicator for lazy loading at top */}
          {isLoadingHistory && (
            <div className="d-flex align-items-center justify-content-center mb-4">
              <Spinner animation="border" size="sm" role="status" />
              <span className="text-muted x-small ml-2">
                {intl.formatMessage(messages['ai.extensions.sidebar.loading.history'])}
              </span>
            </div>
          )}

          {/* Load more button (alternative to auto-load on scroll) */}
          {hasMoreHistory && !isLoadingHistory && (
            <div className="text-center mb-3">
              <Button
                variant="tertiary"
                size="sm"
                onClick={handleLoadMoreHistory}
                iconAfter={ExpandLess}
              >
                {intl.formatMessage(messages['ai.extensions.sidebar.load.older'])}
              </Button>
            </div>
          )}

          {/* Error state */}
          {error && (
            <Alert
              variant="danger"
              className="mb-3 align-items-center"
              dismissible
              onClose={() => onError && onError('')}
              icon={Warning}
            >
              {error}
            </Alert>
          )}

          {/* Chat messages */}
          {chatMessages.length > 0 && (
            <div className="chat-messages">
              {chatMessages.map((message, index) => {
                // ⛔ Skip empty or invalid messages
                if (!message.content || typeof message.content !== 'string' || !message.content.trim()) {
                  return null;
                }
                const messageKey = `${message.timestamp}-${index}`;
                let variant = 'muted';
                let className = 'ai-message';

                if (message.type === 'user') {
                  variant = 'dark';
                  className = 'mis-auto user-message';
                } else if (message.type === 'error') {
                  className = 'bg-danger';
                }
                return (
                  <Card className={`small my-3 w-75 ${className}`} variant={variant} key={messageKey}>
                    <Card.Section className="pb-2">
                      <ReactMarkdown>
                        {message.content}
                      </ReactMarkdown>
                    </Card.Section>
                    <Card.Footer className={`message-time x-small d-flex ${variant === 'muted' ? 'flex-row-reverse' : ''}`}>
                      <span>{new Date(message.timestamp).toLocaleTimeString()}</span>
                    </Card.Footer>
                  </Card>
                );
              })}
              {/* Scroll anchor */}
              <div ref={chatEndRef} />
            </div>
          )}

          {/* Loading state for follow-up */}
          {isSendingFollowUp && (
            <div className="d-flex align-items-center justify-content-center mb-4">
              <Spinner animation="border" size="sm" role="status" />
              <span className="text-muted x-small ml-2">
                {intl.formatMessage(messages['ai.extensions.sidebar.thinking'])}
              </span>
            </div>
          )}
        </Scrollable>

        {/* Footer Actions */}
        {showActions && (response || error || chatMessages.length > 0) && (
          <div className="px-2 py-3 border-top position-relative">
            {/* Textarea with send button inside */}
            <Form.Control
              size="sm"
              as="textarea"
              ref={textareaRef}
              placeholder={intl.formatMessage(messages['ai.extensions.sidebar.input.label'])}
              value={followUpQuestion}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyPress}
              disabled={isLoading || isSendingFollowUp}
              rows={textareaRows}
              aria-label={intl.formatMessage(messages['ai.extensions.sidebar.input.label'])}
              className="ai-sidebar-chat-input"
            />
            {/* Send button positioned inside textarea */}
            <Button
              size="sm"
              className="ai-sidebar-chat-button zindex-1"
              onClick={handleFollowUpSubmit}
              disabled={isLoading || isSendingFollowUp || !followUpQuestion.trim()}
              aria-label={intl.formatMessage(messages['ai.extensions.sidebar.send.label'])}
            >
              <Icon src={Send} aria-hidden="true" size="xs" />
            </Button>
          </div>
        )}
      </div>
    </ModalLayer>
  );
};

export default AISidebarResponse;
