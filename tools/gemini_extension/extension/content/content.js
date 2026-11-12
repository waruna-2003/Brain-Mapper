/**
 * Brain Mapper - Google Gemini Web Content Script Orchestrator
 * Connects gemini.google.com tab to the local bridge server (localhost:8767)
 * Exclusively processes text-based questions for cross-validation
 */

(function () {
  console.log("[BrainMapper] Gemini text-based cross-validation content script active.");

  const BRIDGE_URL = "http://127.0.0.1:8767";

  let isRunning = false;
  let currentStep = "IDLE";
  let currentQuestionId = null;
  let pacingDelayMs = 5000;
  let loopTimeout = null;
  let questionsSinceNewChat = 0;
  const NEW_CHAT_INTERVAL = 25;

  // Sync initial settings from storage
  chrome.storage.local.get(['isRunning', 'pacingDelaySec'], (data) => {
    if (data.isRunning) {
      console.log("[BrainMapper] Resuming active automation state.");
      isRunning = true;
      runNextCycle();
    }
    if (data.pacingDelaySec) {
      pacingDelayMs = data.pacingDelaySec * 1000;
    }
  });

  // Listen for control messages from popup
  chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === "START") {
      console.log("[BrainMapper] Starting Gemini automation...");
      isRunning = true;
      chrome.storage.local.set({ isRunning: true });
      if (loopTimeout) clearTimeout(loopTimeout);
      runNextCycle();
      sendResponse({ status: "STARTED" });
    } else if (message.action === "PAUSE") {
      console.log("[BrainMapper] Pausing automation...");
      isRunning = false;
      chrome.storage.local.set({ isRunning: false });
      if (loopTimeout) clearTimeout(loopTimeout);
      currentStep = "PAUSED";
      notifyPopup("PAUSED");
      sendResponse({ status: "PAUSED" });
    } else if (message.action === "SKIP") {
      console.log("[BrainMapper] Skipping question:", currentQuestionId);
      if (loopTimeout) clearTimeout(loopTimeout);
      if (currentQuestionId !== null) {
        fetch(`${BRIDGE_URL}/api/skip`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ question_id: currentQuestionId }),
        }).then(() => {
          runNextCycle();
        });
      }
      sendResponse({ status: "SKIPPED" });
    } else if (message.action === "GET_STATE") {
      sendResponse({
        isRunning,
        currentStep,
        currentQuestionId,
      });
    } else if (message.action === "SET_DELAY") {
      pacingDelayMs = (message.delaySec || 5) * 1000;
      chrome.storage.local.set({ pacingDelaySec: message.delaySec });
      sendResponse({ pacingDelayMs });
    }
    return true;
  });

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async function notifyPopup(step, details = {}) {
    currentStep = step;
    chrome.runtime.sendMessage({
      action: "STATE_UPDATE",
      state: {
        isRunning,
        step,
        currentQuestionId,
        ...details,
      },
    }).catch(() => {
      // Harmless when popup is closed
    });
  }

  async function runNextCycle() {
    if (!isRunning) {
      currentStep = "PAUSED";
      notifyPopup("PAUSED");
      return;
    }

    try {
      // 1. Fetch next text-only question from bridge server
      notifyPopup("FETCHING_QUESTION");
      const resp = await fetch(`${BRIDGE_URL}/api/next_question`);
      if (!resp.ok) {
        throw new Error(`Bridge server responded with HTTP ${resp.status}`);
      }
      const data = await resp.json();

      if (data.done) {
        console.log("[BrainMapper] All 500 text-only cross-validation questions completed!");
        isRunning = false;
        chrome.storage.local.set({ isRunning: false });
        notifyPopup("COMPLETED_ALL");
        return;
      }

      currentQuestionId = data.question_id;
      notifyPopup("INJECTING_PROMPT", { question_id: currentQuestionId });
      console.log(`[BrainMapper] Processing Question ID: #${currentQuestionId} (Text-Only) (${data.completed_count}/${data.target_total})`);

      // Periodically open a fresh chat thread to avoid DOM bloat & timeouts
      if (questionsSinceNewChat >= NEW_CHAT_INTERVAL) {
        console.log("[BrainMapper] Starting a fresh chat thread to keep Gemini DOM responsive...");
        await GeminiDOM.startNewChat();
        questionsSinceNewChat = 0;
      }

      // 2. Ensure prompt input exists
      const inputEl = GeminiDOM.getInputElement();
      if (!inputEl) {
        throw new Error("Gemini input box not found. Make sure you are on gemini.google.com and logged in.");
      }

      // Check if currently generating
      if (GeminiDOM.isGenerating()) {
        console.warn("[BrainMapper] Gemini is generating. Waiting 3s...");
        await sleep(3000);
      }

      // Baseline state
      const baselineText = (GeminiDOM.getLastAssistantMessageText() || "").trim();
      const initialMessageCount = GeminiDOM.getAssistantMessages().length;

      // 3. Inject text-only prompt
      notifyPopup("INJECTING_PROMPT", { question_id: currentQuestionId });
      await GeminiDOM.setInputValue(inputEl, data.prompt);
      await sleep(800); // Allow Angular/Quill state to enable send button

      // 4. Click send button
      notifyPopup("SENDING", { question_id: currentQuestionId });
      const sent = await GeminiDOM.clickSendButton(4000);
      if (!sent) {
        throw new Error("Could not send prompt to Gemini. Check if input box or Send button is active.");
      }

      notifyPopup("GENERATING", { question_id: currentQuestionId });
      console.log(`[BrainMapper] Question #${currentQuestionId} submitted to Gemini. Waiting for completion...`);

      // 5. Wait for model response to stream and complete
      const rawResponseText = await GeminiDOM.waitForCompletion({
        initialMessageCount,
        baselineText,
        expectedQuestionId: currentQuestionId,
        timeoutMs: 150000,
      });

      // 6. Extract and validate JSON response
      notifyPopup("PARSING", { question_id: currentQuestionId });
      const parsedData = CognitiveParser.parseAndValidate(rawResponseText, currentQuestionId);
      console.log(`[BrainMapper] Question #${currentQuestionId} parsed successfully:`, parsedData.scores);

      // 7. Submit back to bridge server
      notifyPopup("SUBMITTING", { question_id: currentQuestionId });
      const submitResp = await fetch(`${BRIDGE_URL}/api/submit`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          question_id: currentQuestionId,
          scores: parsedData.scores,
          confidence: parsedData.confidence,
          short_rationale: parsedData.short_rationale,
          raw_response: rawResponseText,
        }),
      });

      if (!submitResp.ok) {
        const errJson = await submitResp.json();
        throw new Error(errJson.error || "Bridge submit failed");
      }

      questionsSinceNewChat++;
      notifyPopup("SAVED", { question_id: currentQuestionId });

      // 8. Pacing delay with random jitter
      if (isRunning) {
        const jitter = Math.floor(Math.random() * 2000) - 500;
        const delay = Math.max(2500, pacingDelayMs + jitter);
        console.log(`[BrainMapper] Pacing delay: ${(delay / 1000).toFixed(1)}s before next question...`);
        notifyPopup("PACING", { delaySec: (delay / 1000).toFixed(1) });
        loopTimeout = setTimeout(runNextCycle, delay);
      }
    } catch (err) {
      console.error(`[BrainMapper] Error on question #${currentQuestionId}:`, err);
      notifyPopup("ERROR", { error: err.message, question_id: currentQuestionId });

      // Record failure to bridge
      if (currentQuestionId !== null) {
        try {
          await fetch(`${BRIDGE_URL}/api/fail`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              question_id: currentQuestionId,
              error: err.message,
            }),
          });
        } catch (_) {}
      }

      // If running, cool down 8s before retrying
      if (isRunning) {
        console.log("[BrainMapper] Cooling down for 8s after error before next cycle...");
        loopTimeout = setTimeout(runNextCycle, 8000);
      }
    }
  }
})();
