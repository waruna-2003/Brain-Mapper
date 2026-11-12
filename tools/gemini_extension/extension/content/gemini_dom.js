/**
 * Google Gemini Web DOM Adapter
 * Resilient selectors and synthetic event synthesizers for gemini.google.com
 */

const GeminiDOM = {
  /**
   * Locate the prompt input element (Quill editor, rich-textarea, or contenteditable)
   */
  getInputElement() {
    const selectors = [
      '.ql-editor[contenteditable="true"]',
      'rich-textarea div[contenteditable="true"]',
      'div[contenteditable="true"][role="textbox"]',
      'div[contenteditable="true"][aria-label*="prompt"]',
      'div[contenteditable="true"][aria-label*="Enter"]',
      'div.text-input-field div[contenteditable="true"]',
      'div.textarea[contenteditable="true"]',
      'div[contenteditable="true"]',
      'textarea',
    ];
    for (const sel of selectors) {
      const el = document.querySelector(sel);
      if (el && el.offsetParent !== null) {
        return el;
      }
    }
    return null;
  },

  /**
   * Programmatically set input value and trigger Gemini's Quill/Angular editor state
   */
  async setInputValue(inputEl, text) {
    if (!inputEl) return false;
    inputEl.focus();

    // 1. Clear existing content first
    try {
      if (inputEl.tagName && inputEl.tagName.toLowerCase() === 'textarea') {
        inputEl.value = '';
      } else {
        inputEl.innerHTML = '<p><br></p>';
      }
    } catch (_) {}

    await new Promise(r => setTimeout(r, 100));

    // 2. Primary Method: Simulated Clipboard Paste (natively handled by Quill/Angular)
    let populated = false;
    try {
      const dt = new DataTransfer();
      dt.setData('text/plain', text);
      const pasteEvent = new ClipboardEvent('paste', {
        bubbles: true,
        cancelable: true,
        clipboardData: dt,
      });
      inputEl.dispatchEvent(pasteEvent);
      await new Promise(r => setTimeout(r, 250));

      const len = (inputEl.innerText || inputEl.value || '').trim().length;
      if (len > 10) {
        populated = true;
      }
    } catch (e) {
      console.warn("[Gemini DOM] Clipboard paste attempt failed:", e);
    }

    // 3. Fallback Method: document.execCommand('insertText')
    if (!populated) {
      try {
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(inputEl);
        selection.removeAllRanges();
        selection.addRange(range);

        document.execCommand('insertText', false, text);
        await new Promise(r => setTimeout(r, 200));

        const len = (inputEl.innerText || inputEl.value || '').trim().length;
        if (len > 10) {
          populated = true;
        }
      } catch (e) {
        console.warn("[Gemini DOM] execCommand insertText failed:", e);
      }
    }

    // 4. Fallback Method: Direct Paragraph HTML / Value Injection
    if (!populated) {
      if (inputEl.tagName && inputEl.tagName.toLowerCase() === 'textarea') {
        const setter = Object.getOwnPropertyDescriptor(
          window.HTMLTextAreaElement.prototype,
          'value'
        )?.set;
        if (setter) setter.call(inputEl, text);
        else inputEl.value = text;
      } else {
        const lines = text.split('\n');
        inputEl.innerHTML = lines
          .map(l => `<p>${l ? l.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') : '<br>'}</p>`)
          .join('');
      }

      inputEl.dispatchEvent(new InputEvent('input', { bubbles: true, inputType: 'insertFromPaste', data: text }));
      inputEl.dispatchEvent(new Event('input', { bubbles: true }));
      inputEl.dispatchEvent(new Event('change', { bubbles: true }));
    }

    // Trigger keyboard notification so Send button enables
    inputEl.dispatchEvent(new KeyboardEvent('keydown', { key: ' ', bubbles: true }));
    inputEl.dispatchEvent(new KeyboardEvent('keyup', { key: ' ', bubbles: true }));
    await new Promise(r => setTimeout(r, 300));

    const finalLen = (inputEl.innerText || inputEl.value || '').trim().length;
    return finalLen > 0;
  },

  /**
   * Locate and click Gemini's send button with retry loop
   */
  async clickSendButton(maxWaitMs = 4000) {
    const startTime = Date.now();
    const inputEl = this.getInputElement();

    const buttonSelectors = [
      'button[aria-label*="Send message"]',
      'button[aria-label*="Send prompt"]',
      'button[aria-label*="Send"]',
      'button.send-button',
      'div[role="button"][aria-label*="Send"]',
      'button:has(mat-icon[data-mat-icon-name="send"])',
      'button[mat-icon-button]:has(mat-icon)',
      'button:has(svg path)',
    ];

    while (Date.now() - startTime < maxWaitMs) {
      // 1. Try finding enabled send button
      for (const sel of buttonSelectors) {
        const btn = document.querySelector(sel);
        if (btn) {
          const target = btn.tagName.toLowerCase() === 'mat-icon' || btn.tagName.toLowerCase() === 'svg' ? btn.closest('button, div[role="button"]') : btn;
          if (target && !target.disabled && target.getAttribute('aria-disabled') !== 'true') {
            target.click();
            console.log("[Gemini DOM] Send button clicked successfully.");
            return true;
          }
        }
      }

      // 2. Try dispatching Enter key on input element
      if (inputEl) {
        const initialLen = (inputEl.innerText || inputEl.value || '').trim().length;
        if (initialLen > 0) {
          inputEl.focus();
          const enterDown = new KeyboardEvent('keydown', {
            key: 'Enter',
            code: 'Enter',
            keyCode: 13,
            which: 13,
            bubbles: true,
            cancelable: true,
          });
          inputEl.dispatchEvent(enterDown);

          // Wait 350ms to see if input cleared (indicating submission)
          await new Promise(r => setTimeout(r, 350));
          const currentLen = (inputEl.innerText || inputEl.value || '').trim().length;
          if (currentLen === 0) {
            console.log("[Gemini DOM] Enter key successfully submitted prompt.");
            return true;
          }
        }
      }

      await new Promise(r => setTimeout(r, 300));
    }

    return false;
  },

  /**
   * Check if Gemini is currently generating output
   */
  isGenerating() {
    const stopSelectors = [
      'button[aria-label*="Stop response"]',
      'button[aria-label*="Stop generating"]',
      'button[aria-label*="Stop"]',
      'button.stop-button',
      'div[role="button"][aria-label*="Stop"]',
      'mat-progress-bar',
      'div.sparkle-icon.pulsing',
    ];

    for (const sel of stopSelectors) {
      const el = document.querySelector(sel);
      if (el && el.offsetParent !== null) {
        return true;
      }
    }

    return false;
  },

  /**
   * Retrieve ONLY assistant / model response elements (strictly excluding user query containers)
   */
  getAssistantMessages() {
    // 1. Primary: Gemini <model-response> custom elements
    const modelResponses = Array.from(document.querySelectorAll('model-response'));
    if (modelResponses.length > 0) return modelResponses;

    // 2. message-content containers inside model responses
    const msgContents = Array.from(document.querySelectorAll('message-content')).filter(el => {
      return !el.closest('user-query');
    });
    if (msgContents.length > 0) return msgContents;

    // 3. Fallback: div.model-response-text
    const textContainers = Array.from(document.querySelectorAll('div.model-response-text, div[class*="response-container"]'));
    if (textContainers.length > 0) return textContainers;

    // 4. Fallback: markdown blocks not inside user query
    const markdowns = Array.from(document.querySelectorAll('.markdown, div[class*="markdown"]')).filter(el => {
      return !el.closest('user-query');
    });
    return markdowns;
  },

  /**
   * Get the text content of the latest assistant message (excluding <model-thoughts> blocks)
   */
  getLastAssistantMessageText() {
    const msgs = this.getAssistantMessages();
    if (msgs.length === 0) return '';

    const lastMsg = msgs[msgs.length - 1];

    // 1. Prefer <message-content> specifically so we never pick <model-thoughts> in Gemini Pro
    const msgContent = lastMsg.tagName && lastMsg.tagName.toLowerCase() === 'message-content'
      ? lastMsg
      : lastMsg.querySelector('message-content');
    if (msgContent) {
      const mdInside = msgContent.querySelector('.markdown, div[class*="markdown"]');
      if (mdInside) {
        return (mdInside.innerText || mdInside.textContent || '').trim();
      }
      return (msgContent.innerText || msgContent.textContent || '').trim();
    }

    // 2. Fallback: find last .markdown inside lastMsg that is NOT inside model-thoughts
    const markdowns = Array.from(lastMsg.querySelectorAll('.markdown, div[class*="markdown"]')).filter(
      el => !el.closest('model-thoughts')
    );
    if (markdowns.length > 0) {
      const lastMd = markdowns[markdowns.length - 1];
      return (lastMd.innerText || lastMd.textContent || '').trim();
    }

    return (lastMsg.innerText || lastMsg.textContent || '').trim();
  },

  /**
   * Attempt to open a clean chat thread to keep the DOM fast over 500 questions
   */
  async startNewChat() {
    const selectors = [
      'button[aria-label*="New chat"]',
      'a[aria-label*="New chat"]',
      '[data-test-id="new-chat-button"]',
      'a[href="/app"]',
    ];
    for (const sel of selectors) {
      const btn = document.querySelector(sel);
      if (btn && btn.offsetParent !== null) {
        btn.click();
        await new Promise(r => setTimeout(r, 1800));
        return true;
      }
    }
    return false;
  },

  /**
   * Resiliently wait for response completion with anti-stale and stability checks
   */
  async waitForCompletion(options = {}) {
    const {
      initialMessageCount = 0,
      baselineText = '',
      expectedQuestionId = null,
      timeoutMs = 150000,
      pollIntervalMs = 700,
    } = options;

    const startTime = Date.now();
    let generationObserved = false;
    let lastSeenText = '';
    let stableCount = 0;

    // Phase 1: Wait for generation to start or new assistant message to appear (up to 35s)
    while (Date.now() - startTime < 35000) {
      const currentlyGenerating = this.isGenerating();
      const currentCount = this.getAssistantMessages().length;
      const currentText = this.getLastAssistantMessageText();

      if (currentlyGenerating || currentCount > initialMessageCount || (currentText && currentText !== baselineText)) {
        generationObserved = true;
        break;
      }
      await new Promise(r => setTimeout(r, 500));
    }

    if (!generationObserved) {
      console.warn("[Gemini DOM] Notice: Generation indicator not explicitly caught; proceeding to observe response text.");
    }

    // Phase 2: Wait for generation to complete and text to stabilize
    while (Date.now() - startTime < timeoutMs) {
      const currentlyGenerating = this.isGenerating();
      const currentCount = this.getAssistantMessages().length;
      const currentText = this.getLastAssistantMessageText();

      // Guard against reading previous turn if Gemini hasn't appended the new turn yet
      const isNewTurn = currentCount > initialMessageCount || (currentText && currentText !== baselineText);

      if (!currentlyGenerating && isNewTurn && currentText && currentText.length > 25) {
        const hasJsonSignal = currentText.includes('{') && (currentText.includes('attention') || currentText.includes('working_memory'));

        if (hasJsonSignal) {
          // Anti-stale check: if response explicitly contains a different question_id, keep waiting for the new turn
          if (expectedQuestionId !== null) {
            const qidMatch = currentText.match(/"question_id"\s*:\s*"?(\d+)"?/);
            if (qidMatch && parseInt(qidMatch[1], 10) !== expectedQuestionId) {
              stableCount = 0;
              await new Promise(r => setTimeout(r, pollIntervalMs));
              continue;
            }
          }

          if (currentText === lastSeenText) {
            stableCount++;
            if (stableCount >= 2) {
              console.log("[Gemini DOM] Response complete and stabilized.");
              return currentText;
            }
          } else {
            stableCount = 0;
            lastSeenText = currentText;
          }
        }
      } else {
        stableCount = 0;
      }

      await new Promise(r => setTimeout(r, pollIntervalMs));
    }

    throw new Error(`Timeout: No stable assistant response received from Gemini after ${timeoutMs / 1000}s`);
  },
};
