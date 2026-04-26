import React from 'react'
import styled from 'styled-components'
import { Loader2 } from 'lucide-react'

const MessageBarInput = ({
  value,
  onChange,
  placeholder = 'Message...',
  disabled,
  loading,
  'aria-label': ariaLabel,
  fullWidth,
}) => {
  return (
    <StyledWrapper $fullWidth={Boolean(fullWidth)}>
      <div className="messageBox">
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
  }
  .messageBox:focus-within:not(:has(.messageInput:disabled)) {
    border-color: var(--text-primary);
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
`

export default MessageBarInput
