import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import ReactMarkdown from 'react-markdown';
import {
  Button,
  Alert,
  Dropdown,
} from '@openedx/paragon';
import {
  Send,
  CheckCircle,
  Warning,
  Close,
  Settings,
} from '@openedx/paragon/icons';

// Import AI services
import {
  callWorkflowService,
  prepareContextData,
  formatErrorMessage,
} from '../services';

/**
 * AI Sidebar Response Component
 * Displays AI responses in a floating right sidebar
 */
const AISidebarResponse = ({
  response,
  error,
  isLoading,
  onClear,
  onError,
  showActions = true,
  customMessage,
  contextData = {},
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [followUpQuestion, setFollowUpQuestion] = useState('');
  const [chatMessages, setChatMessages] = useState([]);
  const [isSendingFollowUp, setIsSendingFollowUp] = useState(false);
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [hasMoreHistory, setHasMoreHistory] = useState(false);
  const chatEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const textareaRef = useRef(null);
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

    let parsedData = null;
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
        let rawMessages = [];

        if (parsedData.messages && Array.isArray(parsedData.messages)) {
          rawMessages = parsedData.messages;
          if (parsedData.metadata) {
            setHasMoreHistory(parsedData.metadata.has_more || false);
          }
        } else if (Array.isArray(parsedData)) {
          rawMessages = parsedData;
        }

        // Formatting
        let formattedMessages = rawMessages.map((msg, index) => ({
          type: msg.role === 'user' ? 'user' : 'ai',
          content: msg.content,
          timestamp: msg.timestamp || new Date().toISOString(),
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
          return a.originalIndex - b.originalIndex;
        });

        setChatMessages(formattedMessages);
        setIsOpen(true);
        initialResponseAdded.current = true;
      }
    // eslint-disable-next-line brace-style
    }

    // --- SCENARIO 2: Simple text (Streaming) ---
    else {
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
        action: 'clear_session',
        payload: {
          requestId: `ai-request-${Date.now()}`,
        },
      });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[AISidebarResponse] Clear session error:', err);
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
        action: 'lazy_load_chat_history',
        userInput: JSON.stringify({ current_messages: currentMessageCount }),
        payload: {
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
      const messages = parsed.messages || [];

      // Format older messages
      const olderMessages = (Array.isArray(messages) ? messages : []).map((msg) => ({
        type: msg.role === 'user' ? 'user' : 'ai',
        content: msg.content,
        timestamp: new Date().toISOString(),
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
      // eslint-disable-next-line no-console
      console.error('[AISidebarResponse] Load more history error:', err);
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

  /**
   * Handle follow-up question submission
   * Makes direct API call instead of using onAskAgain
   */
  const handleFollowUpSubmit = async () => {
    if (!followUpQuestion.trim()) {
      return;
    }

    const userMessage = followUpQuestion.trim();
    const aiPlaceholder = {
      type: 'ai',
      content: '',
      timestamp: null,
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
        action: 'run',
        userInput: userMessage,
        payload: {
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
              newMsgs[lastIndex] = {
                ...newMsgs[lastIndex],
                content: buffer,
                type: 'ai',
                timestamp: newMsgs[lastIndex].timestamp ?? new Date().toISOString(),
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
          aiResponse = JSON.stringify(data, null, 2);
        }

        // Update the AI placeholder with the final response
        setChatMessages(prev => {
          const newMsgs = [...prev];
          const lastIndex = newMsgs.length - 1;
          if (newMsgs[lastIndex] && newMsgs[lastIndex].type === 'ai') {
            newMsgs[lastIndex] = {
              ...newMsgs[lastIndex],
              content: aiResponse,
              timestamp: new Date().toISOString(),
            };
          }
          return newMsgs;
        });
      }
    } catch (err) {
      // eslint-disable-next-line no-console
      console.error('[AISidebarResponse] Follow-up error:', err);
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
    const lineHeight = 24; // Approximate line height in pixels
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
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.3)',
            zIndex: 1040,
            transition: 'opacity 0.3s ease',
          }}
          onClick={handleClose}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Escape' && handleClose()}
          aria-label="Close sidebar"
        />
      )}

      {/* Sidebar */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          right: isOpen ? 0 : '-400px',
          width: '400px',
          maxWidth: '90vw',
          height: '100vh',
          backgroundColor: '#fff',
          boxShadow: '-2px 0 8px rgba(0, 0, 0, 0.15)',
          zIndex: 1050,
          transition: 'right 0.3s ease',
          display: 'flex',
          flexDirection: 'column',
          overflowY: 'auto',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #dee2e6',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: '#f8f9fa',
          }}
        >
          <div className="d-flex align-items-center">
            <CheckCircle className="text-success me-2" style={{ width: '20px', height: '20px' }} />
            <strong style={{ fontSize: '1rem' }}>{customMessage || 'AI Assistant Response'}</strong>
          </div>
          <div className="d-flex align-items-center gap-2">
            {/* Settings dropdown with Clear option */}
            <Dropdown>
              <Dropdown.Toggle
                variant="light"
                size="sm"
                id="sidebar-settings-dropdown"
                className="p-2"
                style={{ minWidth: 'auto' }}
              >
                <Settings style={{ width: '16px', height: '16px' }} />
              </Dropdown.Toggle>
              <Dropdown.Menu>
                <Dropdown.Item onClick={handleClearAndClose}>
                  Clear Chat
                </Dropdown.Item>
              </Dropdown.Menu>
            </Dropdown>
            {/* Close button */}
            <button
              type="button"
              onClick={handleClose}
              className="btn btn-secondary btn-sm p-2"
              style={{ minWidth: 'auto' }}
              aria-label="Close sidebar"
            >
              <Close style={{ width: '16px', height: '16px' }} />
            </button>
          </div>
        </div>

        {/* Content */}
        <div
          ref={chatContainerRef}
          style={{ flex: 1, overflowY: 'auto', padding: '20px' }}
          onScroll={handleScroll}
        >
          {/* Loading indicator for lazy loading at top */}
          {isLoadingHistory && (
            <div className="d-flex align-items-center justify-content-center py-3 gap-2">
              <div className="spinner-border spinner-border-sm text-primary" role="status" aria-label="Loading history" />
              <span className="text-muted" style={{ fontSize: '0.85rem' }}>
                Loading older messages...
              </span>
            </div>
          )}

          {/* Load more button (alternative to auto-load on scroll) */}
          {hasMoreHistory && !isLoadingHistory && (
            <div className="text-center mb-3">
              <Button
                variant="link"
                size="sm"
                onClick={handleLoadMoreHistory}
                className="text-muted"
                style={{ fontSize: '0.85rem', textDecoration: 'none' }}
              >
                Load older messages ↑
              </Button>
            </div>
          )}

          {/* Error state */}
          {error && (
            <Alert
              variant="danger"
              className="mb-3"
              dismissible
              onClose={() => onError && onError('')}
            >
              <div className="d-flex align-items-start">
                <Warning className="me-2 mt-1" style={{ width: '16px', height: '16px' }} />
                <div>{error}</div>
              </div>
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
                let bgColor = '#f8f9fa';
                let textColor = '#212529';
                let className = 'ai-message';

                if (message.type === 'user') {
                  bgColor = '#007bff';
                  textColor = '#fff';
                  className = 'user-message';
                } else if (message.type === 'error') {
                  bgColor = '#f8d7da';
                  textColor = '#721c24';
                  className = 'error-message';
                }

                return (
                  <div
                    key={messageKey}
                    className={`message-bubble mb-3 ${className}`}
                    style={{
                      padding: '12px 16px',
                      borderRadius: '12px',
                      backgroundColor: bgColor,
                      color: textColor,
                      marginLeft: message.type === 'user' ? '20%' : '0',
                      marginRight: message.type === 'user' ? '0' : '20%',
                    }}
                  >
                    <div
                      className="message-content"
                      style={{
                        fontSize: '0.9rem',
                        lineHeight: '1.5',
                      }}
                    >
                      <ReactMarkdown>
                        {message.content}
                      </ReactMarkdown>
                    </div>
                    <div
                      className="message-time text-muted"
                      style={{
                        fontSize: '0.7rem',
                        marginTop: '6px',
                        opacity: 0.7,
                      }}
                    >
                      {new Date(message.timestamp).toLocaleTimeString()}
                    </div>
                  </div>
                );
              })}
              {/* Scroll anchor */}
              <div ref={chatEndRef} />
            </div>
          )}

          {/* Loading state for follow-up */}
          {isSendingFollowUp && (
            <div className="d-flex align-items-center justify-content-center py-3 gap-2">
              <div className="spinner-border spinner-border-sm text-primary" role="status" aria-label="Loading" />
              <span className="text-muted" style={{ fontSize: '0.85rem' }}>
                Thinking...
              </span>
            </div>
          )}
        </div>

        {/* Footer Actions */}
        {showActions && (response || error || chatMessages.length > 0) && (
          <div
            style={{
              padding: '16px 20px',
              borderTop: '1px solid #dee2e6',
              backgroundColor: '#f8f9fa',
            }}
          >
            {/* Textarea with send button inside */}
            <div style={{ position: 'relative' }}>
              <textarea
                ref={textareaRef}
                className="form-control"
                placeholder="Type your follow-up question..."
                value={followUpQuestion}
                onChange={handleTextareaChange}
                onKeyPress={handleKeyPress}
                disabled={isLoading || isSendingFollowUp}
                rows={textareaRows}
                style={{
                  fontSize: '0.9rem',
                  borderRadius: '6px',
                  paddingRight: '50px',
                  resize: 'none',
                  overflowY: textareaRows >= 10 ? 'auto' : 'hidden',
                  lineHeight: '1.5',
                }}
              />
              {/* Send button positioned inside textarea */}
              <button
                type="button"
                onClick={handleFollowUpSubmit}
                disabled={isLoading || isSendingFollowUp || !followUpQuestion.trim()}
                className="btn btn-primary btn-sm"
                aria-label="Send message"
                style={{
                  position: 'absolute',
                  right: '8px',
                  bottom: textareaRows > 1 ? '8px' : '50%',
                  transform: textareaRows > 1 ? 'none' : 'translateY(50%)',
                  padding: '6px 8px',
                  minWidth: 'auto',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                }}
              >
                <Send style={{ width: '16px', height: '16px' }} />
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  );
};

AISidebarResponse.propTypes = {
  response: PropTypes.string,
  error: PropTypes.string,
  isLoading: PropTypes.bool,
  onClear: PropTypes.func,
  onError: PropTypes.func,
  showActions: PropTypes.bool,
  customMessage: PropTypes.string,
  contextData: PropTypes.shape({}),
};

AISidebarResponse.defaultProps = {
  response: null,
  error: null,
  isLoading: false,
  onClear: null,
  onError: null,
  showActions: true,
  customMessage: 'AI Assistant Response',
  contextData: {},
};

export default AISidebarResponse;
