import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import ReactMarkdown from 'react-markdown';
import { Button, Alert, IconButton } from '@openedx/paragon';
import {
  Send,
  CheckCircle,
  Warning,
  Close,
} from '@openedx/paragon/icons';

// Import AI services
import {
  callAIService,
  prepareContextData,
  getDefaultEndpoint,
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
  const [previousSubmissionIds, setPreviousSubmissionIds] = useState([]);
  const chatEndRef = useRef(null);
  const chatContainerRef = useRef(null);
  const initialResponseAdded = useRef(false);
  const hasScrolledToBottom = useRef(false);
  const isLoadingOlderMessages = useRef(false);
  const previousMessageCount = useRef(0);

  // Show sidebar when response or error arrives (but not while just loading)
  useEffect(() => {
    if (response && !initialResponseAdded.current) {
      setIsOpen(true);
      try {
        const parsed = JSON.parse(response);

        // Check if response has metadata structure
        if (parsed.messages && Array.isArray(parsed.messages)) {
          const formattedMessages = parsed.messages.map((msg) => ({
            type: msg.role === 'user' ? 'user' : 'ai',
            content: msg.content,
            timestamp: new Date().toISOString(),
          }));
          setChatMessages(formattedMessages);

          // Store metadata for lazy loading
          if (parsed.metadata) {
            setHasMoreHistory(parsed.metadata.has_more || false);
            setPreviousSubmissionIds(parsed.metadata.previous_submission_ids || []);
          }

          initialResponseAdded.current = true;
          return;
        }

        // Fallback: check if it's just an array of messages
        if (Array.isArray(parsed)) {
          const formattedMessages = parsed.map((msg) => ({
            type: msg.role === 'user' ? 'user' : 'ai',
            content: msg.content,
            timestamp: new Date().toISOString(),
          }));
          setChatMessages(formattedMessages);
          initialResponseAdded.current = true;
          return;
        }
      } catch (e) {
        // Not JSON, proceed to add as single message
      }

      // Add single response message
      setChatMessages([{
        type: 'ai',
        content: response,
        timestamp: new Date().toISOString(),
      }]);
      initialResponseAdded.current = true;
    }

    if (error) {
      setIsOpen(true);
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
      // Get API endpoint
      const apiEndpoint = getDefaultEndpoint();

      // Prepare context data
      const preparedContext = prepareContextData({
        ...contextData,
      });

      // Make API call
      await callAIService({
        contextData: preparedContext,
        action: 'clear_session',
        apiEndpoint,
        courseId: preparedContext.courseId,
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
    if (!hasMoreHistory || isLoadingHistory || previousSubmissionIds.length === 0) {
      return;
    }

    setIsLoadingHistory(true);
    isLoadingOlderMessages.current = true;

    try {
      // Save current scroll position before loading
      const scrollContainer = chatContainerRef.current;
      const scrollHeightBefore = scrollContainer?.scrollHeight || 0;
      const scrollTopBefore = scrollContainer?.scrollTop || 0;

      // Get the oldest submission ID to load from
      const oldestSubmissionId = previousSubmissionIds[previousSubmissionIds.length - 1];

      // Get API endpoint
      const apiEndpoint = getDefaultEndpoint();

      // Prepare context data
      const preparedContext = prepareContextData({
        ...contextData,
      });

      // Make API call with lazy_load_chat_history action
      const data = await callAIService({
        contextData: preparedContext,
        action: 'lazy_load_chat_history',
        apiEndpoint,
        courseId: preparedContext.courseId,
        userQuery: oldestSubmissionId, // Pass submission ID as userQuery
      });

      // Parse response
      const parsed = JSON.parse(data.response || '[]');

      // Format older messages
      const olderMessages = (Array.isArray(parsed) ? parsed : []).map((msg) => ({
        type: msg.role === 'user' ? 'user' : 'ai',
        content: msg.content,
        timestamp: new Date().toISOString(),
      }));

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

      // Update metadata from response
      if (data.metadata) {
        setHasMoreHistory(data.metadata.has_more || false);
        setPreviousSubmissionIds(data.metadata.previous_submission_ids || []);
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
    setPreviousSubmissionIds([]);
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
    setPreviousSubmissionIds([]);
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

    // Add user message to chat
    setChatMessages(prev => [...prev, {
      type: 'user',
      content: userMessage,
      timestamp: new Date().toISOString(),
    }]);

    setFollowUpQuestion('');
    setIsSendingFollowUp(true);

    try {
      // Get API endpoint
      const apiEndpoint = getDefaultEndpoint();

      // Prepare context data
      const preparedContext = prepareContextData({
        ...contextData,
      });

      // Make API call
      const data = await callAIService({
        contextData: preparedContext,
        apiEndpoint,
        courseId: preparedContext.courseId,
        userQuery: userMessage,
      });

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

      // Add AI response to chat
      setChatMessages(prev => [...prev, {
        type: 'ai',
        content: aiResponse,
        timestamp: new Date().toISOString(),
      }]);
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
   * Handle Enter key press in input
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
          <IconButton
            src={Close}
            iconAs="svg"
            alt="Close"
            onClick={handleClearAndClose}
            size="sm"
            variant="secondary"
          />
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
            <div className="d-flex flex-column gap-2">
              <input
                type="text"
                className="form-control"
                placeholder="Type your follow-up question..."
                value={followUpQuestion}
                onChange={(e) => setFollowUpQuestion(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={isLoading || isSendingFollowUp}
                style={{
                  fontSize: '0.9rem',
                  borderRadius: '6px',
                }}
              />

              <div className="d-flex justify-content-end gap-2">
                {/* Clear button */}
                {onClear && (
                  <Button
                    variant="outline-secondary"
                    size="sm"
                    onClick={handleClearAndClose}
                    className="py-1 px-3"
                  >
                    Clear
                  </Button>
                )}

                {/* Send follow-up button */}
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleFollowUpSubmit}
                  disabled={isLoading || isSendingFollowUp || !followUpQuestion.trim()}
                  iconBefore={Send}
                  className="py-1 px-3"
                >
                  Send
                </Button>
              </div>
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
