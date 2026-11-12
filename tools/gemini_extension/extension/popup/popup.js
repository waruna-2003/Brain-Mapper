/**
 * Brain Mapper - Gemini Annotator Popup Controller
 */

const BRIDGE_URL = "http://127.0.0.1:8767";

// DOM Elements
const elBridgeStatus = document.getElementById("bridge-status");
const elTabStatus = document.getElementById("tab-status");
const elProgressPercent = document.getElementById("progress-percent");
const elProgressBarFill = document.getElementById("progress-bar-fill");
const elCompletedCount = document.getElementById("completed-count");
const elTargetCount = document.getElementById("target-count");
const elOverlapCount = document.getElementById("overlap-count");
const elFailedCount = document.getElementById("failed-count");
const elLiveStep = document.getElementById("live-step");
const elActivityDetail = document.getElementById("activity-detail-text");
const elBtnToggle = document.getElementById("btn-toggle");
const elBtnSkip = document.getElementById("btn-skip");
const elDelaySlider = document.getElementById("delay-slider");
const elDelayVal = document.getElementById("delay-val");
const elLogList = document.getElementById("log-list");

let isRunning = false;
let activeGeminiTabId = null;

function addLog(text) {
  const item = document.createElement("div");
  item.className = "log-item";
  const time = new Date().toLocaleTimeString();
  item.textContent = `[${time}] ${text}`;
  elLogList.appendChild(item);
  elLogList.scrollTop = elLogList.scrollHeight;
}

// 1. Check Bridge Server Status & Stats
async function updateBridgeStats() {
  try {
    const healthResp = await fetch(`${BRIDGE_URL}/api/health`, { cache: "no-store" });
    if (!healthResp.ok) throw new Error("Health check failed");

    elBridgeStatus.textContent = "Online";
    elBridgeStatus.className = "pill pill-online";

    const statsResp = await fetch(`${BRIDGE_URL}/api/stats`, { cache: "no-store" });
    if (statsResp.ok) {
      const stats = await statsResp.json();
      elProgressPercent.textContent = `${stats.percent}%`;
      elProgressBarFill.style.width = `${stats.percent}%`;
      elCompletedCount.textContent = stats.completed;
      elTargetCount.textContent = stats.target_total || 500;
      elOverlapCount.textContent = stats.deepseek_overlap_count || 0;
      elFailedCount.textContent = stats.failed;
    }
  } catch (err) {
    elBridgeStatus.textContent = "Offline";
    elBridgeStatus.className = "pill pill-offline";
  }
}

// 2. Find and Validate Gemini Tab
async function checkGeminiTab() {
  try {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const currentTab = tabs[0];

    if (currentTab && currentTab.url && currentTab.url.includes("gemini.google.com")) {
      activeGeminiTabId = currentTab.id;

      // Ping content script
      chrome.tabs.sendMessage(activeGeminiTabId, { action: "GET_STATE" }, (resp) => {
        if (chrome.runtime.lastError) {
          elTabStatus.textContent = "Press F5";
          elTabStatus.className = "pill pill-offline";
          elActivityDetail.textContent = "Please press F5 on gemini.google.com tab to attach content script.";
        } else if (resp) {
          elTabStatus.textContent = "Connected";
          elTabStatus.className = "pill pill-online";
          updateStateFromContent(resp);
        }
      });
    } else {
      const allTabs = await chrome.tabs.query({ url: "https://gemini.google.com/*" });
      if (allTabs.length > 0) {
        activeGeminiTabId = allTabs[0].id;
        elTabStatus.textContent = "Tab in Background";
        elTabStatus.className = "pill pill-online";
      } else {
        activeGeminiTabId = null;
        elTabStatus.textContent = "Not Open";
        elTabStatus.className = "pill pill-offline";
        elActivityDetail.textContent = "Open gemini.google.com in a Chrome tab.";
      }
    }
  } catch (e) {
    console.error("Tab check error:", e);
  }
}

function updateStateFromContent(state) {
  if (!state) return;
  isRunning = !!state.isRunning;

  if (isRunning) {
    elBtnToggle.textContent = "Pause Automation";
    elBtnToggle.className = "btn btn-pause";
  } else {
    elBtnToggle.textContent = "Start Automation";
    elBtnToggle.className = "btn btn-primary";
  }

  if (state.currentStep) {
    elLiveStep.textContent = state.currentStep;
  }

  if (state.currentStep === "ERROR") {
    elLiveStep.style.color = "#f28b82";
    elActivityDetail.textContent = state.error || "An error occurred.";
    elActivityDetail.style.color = "#f28b82";
  } else {
    elLiveStep.style.color = "";
    elActivityDetail.style.color = "";
    if (state.currentQuestionId !== null && state.currentQuestionId !== undefined) {
      elActivityDetail.textContent = `Processing text question #${state.currentQuestionId}`;
    }
  }
}

// Listen for broadcast state updates from content script
chrome.runtime.onMessage.addListener((message) => {
  if (message.action === "STATE_UPDATE" && message.state) {
    const s = message.state;
    updateStateFromContent(s);

    if (s.step === "INJECTING_PROMPT") {
      addLog(`Injecting Text Question #${s.question_id}`);
    } else if (s.step === "SENDING") {
      addLog(`Submitting Question #${s.question_id} to Gemini`);
    } else if (s.step === "GENERATING") {
      addLog(`Waiting for response #${s.question_id}`);
    } else if (s.step === "PARSING") {
      addLog(`Validating JSON scores #${s.question_id}`);
    } else if (s.step === "SAVED") {
      addLog(`Saved Question #${s.question_id} to bridge!`);
      updateBridgeStats();
    } else if (s.step === "PACING") {
      addLog(`Pacing delay: ${s.delaySec}s`);
    } else if (s.step === "ERROR") {
      addLog(`Error on #${s.question_id}: ${s.error}`);
    } else if (s.step === "COMPLETED_ALL") {
      addLog(`Completed all 500 text-only questions!`);
      updateBridgeStats();
    }
  }
});

// Event Listeners
elBtnToggle.addEventListener("click", () => {
  if (!activeGeminiTabId) {
    alert("Please open and switch to a gemini.google.com tab first.");
    return;
  }

  const nextAction = isRunning ? "PAUSE" : "START";
  chrome.tabs.sendMessage(activeGeminiTabId, { action: nextAction }, (resp) => {
    if (chrome.runtime.lastError) {
      alert("Could not reach Gemini tab. Please reload the tab (press F5) and try again.");
    } else if (resp) {
      isRunning = nextAction === "START";
      updateStateFromContent({ isRunning });
      addLog(isRunning ? "Automation started." : "Automation paused.");
    }
  });
});

elBtnSkip.addEventListener("click", () => {
  if (!activeGeminiTabId) return;
  chrome.tabs.sendMessage(activeGeminiTabId, { action: "SKIP" }, () => {
    addLog("Sent SKIP signal to active question.");
  });
});

elDelaySlider.addEventListener("input", (e) => {
  const val = e.target.value;
  elDelayVal.textContent = `${val}s`;
});

elDelaySlider.addEventListener("change", (e) => {
  const val = parseInt(e.target.value, 10);
  if (activeGeminiTabId) {
    chrome.tabs.sendMessage(activeGeminiTabId, { action: "SET_DELAY", delaySec: val });
  }
});

// Initialize and poll
updateBridgeStats();
checkGeminiTab();
setInterval(updateBridgeStats, 3000);
setInterval(checkGeminiTab, 4000);
