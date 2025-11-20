import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
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
  const chatEndRef = useRef(null);
  const initialResponseAdded = useRef(false);

  // Show sidebar when response or error arrives (but not while just loading)
  useEffect(() => {
    if (response && !initialResponseAdded.current) {
      setIsOpen(true);
      try {
        const parsed = JSON.parse(response);
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

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatMessages, isSendingFollowUp]);

  /**
   * Format response text for display
   */
  const formatResponse = (responseText) => {
    if (!responseText) { return ''; }

    // Convert newlines to break tags
    let formatted = responseText.replace(/\n/g, '<br>');

    // Basic markdown-like formatting
    formatted = formatted
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code>$1</code>');

    return formatted;
  };

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
  }

  /**
   * Clear response and close sidebar (shows request component again)
   */
  const handleClearAndClose = async () => {
    await handleClearSession();
    setIsOpen(false);
    setFollowUpQuestion('');
    setChatMessages([]);
    initialResponseAdded.current = false;
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
          onClick={handleClearAndClose}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => e.key === 'Escape' && handleClearAndClose()}
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
        <div style={{ flex: 1, overflowY: 'auto', padding: '20px' }}>
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
                      // eslint-disable-next-line react/no-danger
                      dangerouslySetInnerHTML={{
                        __html: formatResponse(message.content),
                      }}
                    />
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
