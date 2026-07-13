import React from 'react'
import styled from 'styled-components'
import { Loader2 } from 'lucide-react'
import ChatContextSelector from './ChatContextSelector'

const MessageBarInput = ({
  value,
  onChange,
  placeholder = 'Message...',
  disabled,
  loading,
  'aria-label': ariaLabel,
  fullWidth,
  chatContext,
  onChatContextChange,
  showChatContextSelector = false,
  hasError = false,
}) => {
  return (
    <StyledWrapper $fullWidth={Boolean(fullWidth)} $hasContext={showChatContextSelector}>
      <div className={`messageBox${hasError ? ' messageBoxError' : ''}`}>
        {showChatContextSelector && (
          <>
            <ChatContextSelector
              value={chatContext}
              onChange={onChatContextChange}
              disabled={disabled}
            />
            <div className="contextDivider" aria-hidden />
          </>
        )}
        <input
          required
          placeholder={placeholder}
          type="text"
          className="messageInput"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          disabled={disabled}
          aria-label={ariaLabel}
        />
        <button type="submit" className="sendButton" disabled={disabled} aria-label={loading ? 'Loading' : 'Send'}>
          {loading ? (
            <Loader2 className="sendSpinner" aria-hidden />
          ) : (
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 664 663">
              <path
                fill="none"
                d="M646.293 331.888L17.7538 17.6187L155.245 331.888M646.293 331.888L17.753 646.157L155.245 331.888M646.293 331.888L318.735 330.228L155.245 331.888"
              />
              <path
                strokeLinejoin="round"
                strokeLinecap="round"
                strokeWidth="33.67"
                stroke="currentColor"
                d="M646.293 331.888L17.7538 17.6187L155.245 331.888M646.293 331.888L17.753 646.157L155.245 331.888M646.293 331.888L318.735 330.228L155.245 331.888"
              />
            </svg>
          )}
        </button>
      </div>
    </StyledWrapper>
  )
}

const StyledWrapper = styled.div`
  ${(p) => (p.$fullWidth ? 'width: 100%;' : '')}

  .messageBox {
    width: fit-content;
    min-height: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--surface-panel);
    padding: 0 18px 0 24px;
    border-radius: 9999px;
    border: 1px solid var(--border-default);
    transition: border-color 0.2s ease;
    color-scheme: light;
  }

  [data-theme='dark'] & .messageBox {
    color-scheme: dark;
  }

  .messageBox:focus-within:not(:has(.messageInput:disabled)) {
    border-color: var(--text-primary);
  }

  .messageBoxError {
    border-color: #ef4444;
  }

  .messageBoxError:focus-within:not(:has(.messageInput:disabled)) {
    border-color: #ef4444;
  }

  .contextDivider {
    width: 1px;
    height: 28px;
    margin: 0 4px 0 8px;
    flex-shrink: 0;
    background-color: var(--border-default);
  }

  .contextSelector {
    position: relative;
    flex-shrink: 0;
    margin-left: -8px;
  }

  .contextTrigger {
    display: flex;
    align-items: center;
    gap: 6px;
    height: 100%;
    padding: 0 10px 0 12px;
    border: none;
    background: transparent;
    color: var(--text-primary);
    cursor: pointer;
    border-radius: 9999px;
    transition: background-color 0.15s ease, color 0.15s ease;
    -webkit-tap-highlight-color: transparent;
  }

  .contextTrigger:hover:not(:disabled) {
    background-color: var(--surface-hover);
  }

  .contextTrigger:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }

  .contextLabel {
    font-size: 0.875rem;
    font-weight: 500;
    line-height: 1;
    white-space: nowrap;
    color: var(--text-primary);
  }

  .contextTrigger svg {
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .contextChevron {
    transition: transform 0.2s ease;
  }

  .contextChevronOpen {
    transform: rotate(180deg);
  }

  .contextMenu {
    position: absolute;
    bottom: calc(100% + 8px);
    left: 0;
    z-index: 50;
    min-width: 168px;
    margin: 0;
    padding: 4px;
    list-style: none;
    border-radius: 12px;
    border: 1px solid var(--border-default);
    background-color: var(--surface-panel);
    color: var(--text-primary);
    box-shadow:
      0 4px 6px -1px rgb(0 0 0 / 0.08),
      0 10px 20px -2px rgb(0 0 0 / 0.12);
  }

  [data-theme='dark'] & .contextMenu {
    box-shadow:
      0 4px 6px -1px rgb(0 0 0 / 0.4),
      0 10px 20px -2px rgb(0 0 0 / 0.5);
  }

  .contextOption {
    display: flex;
    width: 100%;
    align-items: center;
    gap: 10px;
    padding: 10px 12px;
    border: none;
    border-radius: 8px;
    background: transparent;
    color: var(--text-primary);
    font-size: 0.875rem;
    font-weight: 500;
    text-align: left;
    cursor: pointer;
    transition: background-color 0.15s ease;
  }

  .contextOption svg {
    color: var(--text-muted);
    flex-shrink: 0;
  }

  .contextOption:hover {
    background-color: var(--surface-hover);
  }

  .contextOptionActive {
    background-color: var(--surface-hover);
  }

  .contextOptionActive svg {
    color: var(--text-primary);
  }

  .messageInput {
    width: 200px;
    height: 100%;
    background-color: transparent;
    outline: none;
    box-shadow: none;
    border: none;
    padding-left: 6px;
    color: var(--text-primary);
    font-size: 1.125rem;
    line-height: 1.4;
  }
  .messageInput::placeholder {
    color: var(--text-muted);
  }
  .messageInput:disabled {
    color: var(--text-muted);
    cursor: not-allowed;
  }

  .sendButton {
    width: fit-content;
    height: 100%;
    color: var(--text-muted);
    background-color: transparent;
    outline: none;
    border: none;
    -webkit-tap-highlight-color: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: color 0.2s ease, opacity 0.2s ease;
  }
  .messageBox:focus-within:not(:has(.messageInput:disabled)) .sendButton {
    color: var(--text-primary);
  }
  .sendButton:disabled {
    cursor: not-allowed;
    opacity: 0.6;
  }
  .sendButton svg {
    height: 24px;
    width: 24px;
    transition: all 0.3s;
  }
  .sendButton svg path {
    fill: none;
  }
  .sendSpinner {
    height: 24px;
    width: 24px;
    color: currentColor;
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  ${(p) =>
    p.$fullWidth
      ? `
    .messageBox {
      width: 100%;
    }
    .messageInput {
      flex: 1;
      min-width: 0;
      width: auto;
    }
  `
      : ''}

  ${(p) =>
    p.$hasContext
      ? `
    .messageBox {
      padding-left: 8px;
    }
    .messageInput {
      padding-left: 8px;
    }
  `
      : ''}
`

export default MessageBarInput
