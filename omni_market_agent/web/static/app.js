/*
 * OmniMarket Agent — Light Mode Interactive Terminal & Multi-Modal Voice Assistant Frontend
 * - Top-Docked Interactive Voice Console ("How can I help you today?" -> Listen -> Display Chart -> Speak Everything -> Stop Anytime)
 * - Top-Docked Interactive Candlestick + MA(9, 20, 50, 200) Chart + Synchronized RSI(14)/Divergence Sub-Chart
 * - Universal Search-to-Chart Synchronization (Voice, Top Search, Deep Research Search, Screener Search)
 * - Live Google Finance Grounded Prices, Moving Averages, RSI(14), Momentum, Divergence & Analyst Targets
 */

let currentTicker = "NVDA";
let currentIndexFilter = "";
let currentTheme = "light";
let secondsRemaining = 180;
let dashboardData = null;
let lastDeepResearchVoiceText = "";

let tvChart = null;
let candleSeries = null;
let ma9Series = null;
let ma20Series = null;
let ma50Series = null;
let ma200Series = null;

let tvRsiChart = null;
let rsiSeries = null;
let rsiOverboughtSeries = null;
let rsiOversoldSeries = null;

/* Interactive Voice Assistant State */
let voiceSessionToken = 0;
let activeRecognition = null;
let isVoiceSessionActive = false;
let activeTriggerButtonId = null;
let voiceSafetyTimer = null;

const MIC_IDLE_LABELS = {
  "btn-start-voice-assistant": "🎙️ Talk to OmniMarket",
  "btn-top-mic": "🎤 Voice",
  "btn-research-mic": "🎤 Voice Search",
  "btn-mic": "🎤",
};

const COMPANY_NAME_ALIASES = {
  APPLE: "AAPL",
  NVIDIA: "NVDA",
  MICROSOFT: "MSFT",
  TESLA: "TSLA",
  ALPHABET: "GOOGL",
  GOOGLE: "GOOGL",
  AMAZON: "AMZN",
  META: "META",
  FACEBOOK: "META",
  BROADCOM: "AVGO",
  VISTRA: "VST",
  PALANTIR: "PLTR",
  RUSSELL: "IWM",
  JPMORGAN: "JPM",
  NETFLIX: "NFLX",
  AMD: "AMD",
  ORACLE: "ORCL",
  COSTCO: "COST",
  WALMART: "WMT",
  BERKSHIRE: "BRK-B",
  DISNEY: "DIS",
  BOEING: "BA",
  INTEL: "INTC",
  COINBASE: "COIN",
  MICROSTRATEGY: "MSTR",
  CROWDSTRIKE: "CRWD",
  PALOALTO: "PANW",
};

function formatPct(val) {
  const num = Number(val || 0);
  const sign = num >= 0 ? "+" : "";
  return `${sign}${num.toFixed(2)}%`;
}

function formatUsdChange(val) {
  const num = Number(val || 0);
  const sign = num >= 0 ? "+" : "-";
  return `${sign}$${Math.abs(num).toFixed(2)}`;
}

function tryExtractExplicitTicker(rawInput) {
  const text = (rawInput || "").trim().toUpperCase();
  if (!text) return null;

  for (const [alias, sym] of Object.entries(COMPANY_NAME_ALIASES)) {
    const regex = new RegExp(`\\b${alias}\\b`, "i");
    if (regex.test(text)) return sym;
  }

  const trackedSet = new Set((dashboardData?.equities || []).map(r => r.ticker));
  const stopWords = new Set([
    "DEEP", "RESEARCH", "STOCK", "BUY", "SELL", "HOLD", "SHOW", "CHART", "PRICE",
    "WHAT", "ANALYZE", "ON", "FOR", "AND", "THE", "TO", "OR", "IS", "IN", "OF",
    "HOW", "CAN", "HELP", "ME", "TELL", "EVERYTHING", "ABOUT", "GIVE", "SHARES",
    "ALL", "MOVING", "AVERAGE", "AVERAGES", "RSI", "DIVERGENCE", "MOMENTUM", "TODAY"
  ]);

  const tokens = text.replace(/[^A-Z0-9\-\.]/g, " ").split(/\s+/).filter(Boolean);
  for (const tok of tokens) {
    const norm = tok.replace(".", "-");
    if (trackedSet.has(norm) && !stopWords.has(norm)) return norm;
  }

  if (dashboardData?.equities && text.length >= 4) {
    const byName = dashboardData.equities.find(
      r => (r.company_name || "").toUpperCase().includes(text)
    );
    if (byName) return byName.ticker;
  }

  for (const tok of tokens) {
    const norm = tok.replace(".", "-");
    if (/^[A-Z]{2,5}(-[A-Z]{1,2})?$/.test(norm) && !stopWords.has(norm)) {
      return norm;
    }
  }
  return null;
}

function resolveTickerFromInput(rawInput) {
  return tryExtractExplicitTicker(rawInput) || currentTicker;
}

function getChartThemeOptions(theme) {
  if (theme === "dark") {
    return {
      layout: { background: { color: "#0b1120" }, textColor: "#94a3b8" },
      grid: { vertLines: { color: "#162032" }, horzLines: { color: "#162032" } },
      rightPriceScale: { borderColor: "#263248" },
      timeScale: { borderColor: "#263248" },
    };
  }
  return {
    layout: { background: { color: "#ffffff" }, textColor: "#334155" },
    grid: { vertLines: { color: "#f1f5f9" }, horzLines: { color: "#f1f5f9" } },
    rightPriceScale: { borderColor: "#cbd5e1" },
    timeScale: { borderColor: "#cbd5e1" },
  };
}

function initChart() {
  const container = document.getElementById("tv-chart-container");
  const rsiContainer = document.getElementById("tv-rsi-container");
  if (!window.LightweightCharts || !container) return;

  tvChart = LightweightCharts.createChart(container, {
    width: container.clientWidth,
    height: 300,
    ...getChartThemeOptions(currentTheme),
  });

  candleSeries = tvChart.addCandlestickSeries({
    upColor: "#059669",
    downColor: "#dc2626",
    borderVisible: false,
    wickUpColor: "#059669",
    wickDownColor: "#dc2626",
  });

  ma9Series = tvChart.addLineSeries({ color: "#0284c7", lineWidth: 1, title: "SMA 9" });
  ma20Series = tvChart.addLineSeries({ color: "#d97706", lineWidth: 1, title: "SMA 20" });
  ma50Series = tvChart.addLineSeries({ color: "#ea580c", lineWidth: 2, title: "SMA 50" });
  ma200Series = tvChart.addLineSeries({ color: "#9333ea", lineWidth: 2, title: "SMA 200" });

  if (rsiContainer) {
    tvRsiChart = LightweightCharts.createChart(rsiContainer, {
      width: rsiContainer.clientWidth,
      height: 115,
      ...getChartThemeOptions(currentTheme),
    });

    rsiSeries = tvRsiChart.addLineSeries({
      color: "#2563eb",
      lineWidth: 2,
      title: "RSI(14)",
    });
    rsiOverboughtSeries = tvRsiChart.addLineSeries({
      color: "#dc2626",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      title: "OB 70",
    });
    rsiOversoldSeries = tvRsiChart.addLineSeries({
      color: "#059669",
      lineWidth: 1,
      lineStyle: LightweightCharts.LineStyle.Dashed,
      title: "OS 30",
    });

    let isSyncing = false;
    tvChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (isSyncing || !range || !tvRsiChart) return;
      isSyncing = true;
      tvRsiChart.timeScale().setVisibleLogicalRange(range);
      isSyncing = false;
    });
    tvRsiChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
      if (isSyncing || !range || !tvChart) return;
      isSyncing = true;
      tvChart.timeScale().setVisibleLogicalRange(range);
      isSyncing = false;
    });
  }

  window.addEventListener("resize", () => {
    if (tvChart && container) tvChart.applyOptions({ width: container.clientWidth });
    if (tvRsiChart && rsiContainer) tvRsiChart.applyOptions({ width: rsiContainer.clientWidth });
  });
}

function toggleUiTheme() {
  currentTheme = currentTheme === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", currentTheme);
  document.body.classList.toggle("light-mode", currentTheme === "light");

  const btn = document.getElementById("btn-theme-toggle");
  if (btn) {
    btn.textContent = currentTheme === "light" ? "☀️ Light Mode" : "🌙 Dark Mode";
  }
  const pill = document.querySelector(".badge-mode-pill");
  if (pill) {
    pill.textContent = currentTheme === "light" ? "☀️ Light UI" : "🌙 Dark UI";
  }
  if (tvChart) tvChart.applyOptions(getChartThemeOptions(currentTheme));
  if (tvRsiChart) tvRsiChart.applyOptions(getChartThemeOptions(currentTheme));
}

function getDivergenceBadgeMeta(divStatus) {
  const s = String(divStatus || "");
  if (s === "BULLISH_DIVERGENCE") {
    return { cls: "buy", pillCls: "bull", label: "⚡ BULLISH DIVERGENCE" };
  }
  if (s === "HIDDEN_BULLISH_DIVERGENCE") {
    return { cls: "buy", pillCls: "bull", label: "↗ HIDDEN BULLISH DIV" };
  }
  if (s === "BEARISH_DIVERGENCE") {
    return { cls: "sell", pillCls: "bear", label: "⚠️ BEARISH DIVERGENCE" };
  }
  if (s === "HIDDEN_BEARISH_DIVERGENCE") {
    return { cls: "sell", pillCls: "bear", label: "↘ HIDDEN BEARISH DIV" };
  }
  if (s === "BULLISH_CONVERGENCE") {
    return { cls: "hold", pillCls: "conv-bull", label: "✓ BULLISH CONVERGENCE" };
  }
  if (s === "BEARISH_CONVERGENCE") {
    return { cls: "hold", pillCls: "conv-bear", label: "↘ BEARISH CONVERGENCE" };
  }
  return { cls: "hold", pillCls: "conv-bull", label: s || "ALIGNED" };
}

async function loadChart(ticker, options = {}) {
  const resolved = resolveTickerFromInput(ticker);
  currentTicker = resolved.toUpperCase();

  const tradeSym = document.getElementById("trade-ticker");
  if (tradeSym) tradeSym.value = currentTicker;
  const topInput = document.getElementById("top-stock-search-input");
  if (topInput && options.syncTopInput) topInput.value = currentTicker;

  if (options.scrollIntoView) {
    const topSec = document.getElementById("top-chart-section");
    if (topSec) topSec.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  const res = await fetch(`/api/chart/${encodeURIComponent(currentTicker)}`);
  const data = await res.json();
  if (data.status !== "SUCCESS") return;

  const tech = data.technical;
  const analyst = data.analyst;
  const smart = data.smart_money;

  document.getElementById("chart-ticker-title").textContent =
    `${tech.ticker} — ${tech.company_name} ($${tech.price.toFixed(2)} | ${formatUsdChange(tech.daily_change_usd)} / ${formatPct(tech.daily_change_pct)})`;

  const gfLink = document.getElementById("chart-gf-link");
  gfLink.href = tech.google_finance_url;
  gfLink.textContent = `🔗 Live Google Finance (${tech.google_finance_symbol}) • ${tech.data_source || "Google Finance"}`;

  const sigBadge = document.getElementById("chart-signal-badge");
  sigBadge.textContent = `${tech.action_signal} (${tech.signal_score}/100)`;
  sigBadge.className = "signal-badge " + (
    tech.action_signal.includes("BUY") ? "buy" : tech.action_signal.includes("SELL") ? "sell" : "hold"
  );

  if (candleSeries && tech.chart_series && tech.chart_series.length > 0) {
    const seen = new Set();
    const cleanBars = [];
    for (const b of tech.chart_series) {
      if (b.time && !seen.has(b.time)) {
        seen.add(b.time);
        cleanBars.push(b);
      }
    }
    cleanBars.sort((a, b) => a.time.localeCompare(b.time));

    candleSeries.setData(cleanBars.map(b => ({
      time: b.time, open: b.open, high: b.high, low: b.low, close: b.close
    })));
    ma9Series.setData(cleanBars.filter(b => b.sma_9 !== null).map(b => ({ time: b.time, value: b.sma_9 })));
    ma20Series.setData(cleanBars.filter(b => b.sma_20 !== null).map(b => ({ time: b.time, value: b.sma_20 })));
    ma50Series.setData(cleanBars.filter(b => b.sma_50 !== null).map(b => ({ time: b.time, value: b.sma_50 })));
    ma200Series.setData(cleanBars.filter(b => b.sma_200 !== null).map(b => ({ time: b.time, value: b.sma_200 })));
    tvChart.timeScale().fitContent();

    if (rsiSeries && tvRsiChart) {
      const rsiPoints = cleanBars.filter(b => b.rsi_14 !== null && b.rsi_14 !== undefined).map(b => ({
        time: b.time,
        value: Number(b.rsi_14),
      }));
      rsiSeries.setData(rsiPoints);
      rsiOverboughtSeries.setData(rsiPoints.map(p => ({ time: p.time, value: 70 })));
      rsiOversoldSeries.setData(rsiPoints.map(p => ({ time: p.time, value: 30 })));
      tvRsiChart.timeScale().fitContent();
    }
  }

  const divMeta = getDivergenceBadgeMeta(tech.divergence_status);
  const divBadgeEl = document.getElementById("chart-divergence-badge");
  const divTextEl = document.getElementById("chart-divergence-text");
  if (divBadgeEl) {
    divBadgeEl.className = `signal-badge ${divMeta.cls}`;
    divBadgeEl.textContent = divMeta.label;
  }
  if (divTextEl) {
    divTextEl.textContent = tech.divergence_explanation || "";
  }

  const up = (analyst.recent_upgrades_downgrades && analyst.recent_upgrades_downgrades[0]) || { firm: "Consensus", action: "Active" };
  const congCount = (smart.congressional_holders || []).length;
  const tomCount = (smart.tom_lee_fundstrat_themes || []).length;

  document.getElementById("chart-submetrics").innerHTML = `
    <div class="subcard">
      <div class="sc-title">Moving Averages (9 / 20 / 50 / 200)</div>
      <div class="sc-val">
        SMA: $${tech.sma_9.toFixed(2)} / $${tech.sma_20.toFixed(2)} / $${tech.sma_50.toFixed(2)} / $${tech.sma_200.toFixed(2)}<br/>
        <span style="font-size:11px;color:var(--text-muted);">EMA 9/20: $${tech.ema_9.toFixed(2)} / $${tech.ema_20.toFixed(2)} • ${tech.ma_alignment}</span>
      </div>
    </div>
    <div class="subcard">
      <div class="sc-title">RSI(14), Momentum &amp; MACD</div>
      <div class="sc-val">
        RSI(14): ${tech.rsi_14.toFixed(1)} (${tech.rsi_regime})<br/>
        <span style="font-size:11px;color:var(--text-muted);">10d ROC: ${formatPct(tech.momentum_roc_10d_pct)} • MACD Hist: ${tech.macd_histogram >= 0 ? '+' : ''}${tech.macd_histogram.toFixed(3)}</span>
      </div>
    </div>
    <div class="subcard">
      <div class="sc-title">Price–RSI Divergence Status</div>
      <div class="sc-val">
        <span class="div-pill ${divMeta.pillCls}">${divMeta.label}</span><br/>
        <span style="font-size:11px;color:var(--text-muted);">${(tech.divergence_explanation || "").slice(0, 95)}</span>
      </div>
    </div>
    <div class="subcard">
      <div class="sc-title">Analyst Forecast &amp; Smart Money</div>
      <div class="sc-val">
        ${analyst.consensus_rating} • PT $${analyst.target_price_mean.toFixed(2)} (${formatPct(analyst.implied_upside_pct)})<br/>
        <span style="font-size:11px;color:var(--text-muted);">${up.firm} • 🏛️ Cong: ${congCount || "0"} • 🎯 Tom Lee: ${tomCount ? "Yes" : "No"}</span>
      </div>
    </div>
  `;

  if (dashboardData && Array.isArray(dashboardData.equities)) {
    const idx = dashboardData.equities.findIndex(r => r.ticker === tech.ticker);
    if (idx >= 0) {
      dashboardData.equities[idx] = {
        ...dashboardData.equities[idx],
        ...tech,
        consensus_rating: analyst.consensus_rating,
        target_price_mean: analyst.target_price_mean,
        implied_upside_pct: analyst.implied_upside_pct,
      };
      renderScreenerTable(dashboardData.equities);
    }
  }
}

/* ============================================================================
 * Interactive Voice Assistant Engine ("How can I help?" -> Listen -> Chart -> Speak Everything -> Stop Anytime)
 * ============================================================================ */

function setVoiceConsoleState(state, promptHtml, subText) {
  const bar = document.getElementById("interactive-voice-console");
  const badge = document.getElementById("voice-status-badge");
  const promptEl = document.getElementById("voice-live-prompt");
  const subEl = document.getElementById("voice-live-transcript");
  const stopBtn = document.getElementById("btn-stop-voice-response");

  if (!bar || !badge || !promptEl || !subEl) return;

  bar.classList.remove("speaking", "listening");
  badge.className = `vc-badge ${state}`;

  if (state === "greeting") {
    bar.classList.add("speaking");
    badge.textContent = "🔊 GREETING";
    if (stopBtn) stopBtn.classList.add("active-stop");
  } else if (state === "listening") {
    bar.classList.add("listening");
    badge.textContent = "🎙️ LISTENING";
    if (stopBtn) stopBtn.classList.add("active-stop");
  } else if (state === "analyzing") {
    badge.textContent = "⚙️ ANALYZING & CHARTING";
    if (stopBtn) stopBtn.classList.add("active-stop");
  } else if (state === "speaking") {
    bar.classList.add("speaking");
    badge.textContent = "🔊 SPEAKING RESPONSE";
    if (stopBtn) stopBtn.classList.add("active-stop");
  } else {
    badge.textContent = "🎙️ VOICE READY";
    if (stopBtn) stopBtn.classList.remove("active-stop");
  }

  promptEl.innerHTML = promptHtml;
  subEl.innerHTML = subText || "Click <strong>⏹️ Stop Response</strong> (or press <code>Esc</code>) at any time to stop.";
}

function resetAllMicButtons() {
  Object.entries(MIC_IDLE_LABELS).forEach(([id, label]) => {
    const el = document.getElementById(id);
    if (el) {
      el.classList.remove("recording");
      el.textContent = label;
    }
  });
}

function stopAllVoiceInteraction(customMsg) {
  voiceSessionToken += 1;
  isVoiceSessionActive = false;
  activeTriggerButtonId = null;

  if (voiceSafetyTimer) {
    clearTimeout(voiceSafetyTimer);
    voiceSafetyTimer = null;
  }

  if (activeRecognition) {
    try {
      activeRecognition.onresult = null;
      activeRecognition.onerror = null;
      activeRecognition.onend = null;
      activeRecognition.stop();
    } catch (_) {}
    activeRecognition = null;
  }

  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }

  resetAllMicButtons();
  setVoiceConsoleState(
    "idle",
    customMsg || "⏹️ Voice interaction stopped. Click <strong>'🎙️ Talk to OmniMarket'</strong> whenever you want to speak again.",
    "Voice response halted cleanly."
  );
}

function speakSentenceQueue(fullText, token, onDoneCallback) {
  if (!window.speechSynthesis || !fullText || token !== voiceSessionToken) {
    if (onDoneCallback) onDoneCallback();
    return;
  }

  window.speechSynthesis.cancel();
  const sentences = fullText
    .replace(/\s+/g, " ")
    .split(/(?<=[.!?])\s+/)
    .map(s => s.trim())
    .filter(Boolean);

  if (!sentences.length) {
    if (onDoneCallback) onDoneCallback();
    return;
  }

  let idx = 0;

  function speakNext() {
    if (token !== voiceSessionToken) return;
    if (idx >= sentences.length) {
      if (onDoneCallback) onDoneCallback();
      return;
    }

    const currentSentence = sentences[idx];
    idx += 1;

    setVoiceConsoleState(
      "speaking",
      `🔊 <strong>OmniMarket Speaking (${idx}/${sentences.length}):</strong> "${currentSentence}"`,
      `Interactive Stock Chart for <strong>${currentTicker}</strong> is displayed below • Click <strong>⏹️ Stop Response</strong> anytime to stop.`
    );

    const utter = new SpeechSynthesisUtterance(currentSentence);
    utter.rate = 1.03;
    utter.onend = () => {
      if (token !== voiceSessionToken) return;
      speakNext();
    };
    utter.onerror = () => {
      if (token !== voiceSessionToken) return;
      speakNext();
    };
    window.speechSynthesis.speak(utter);
  }

  speakNext();
}

function speakText(text) {
  const token = ++voiceSessionToken;
  isVoiceSessionActive = true;
  speakSentenceQueue(text, token, () => {
    if (token === voiceSessionToken) {
      isVoiceSessionActive = false;
      resetAllMicButtons();
      setVoiceConsoleState(
        "idle",
        "✅ Finished speaking analysis. Click <strong>'🎙️ Talk to OmniMarket'</strong> to ask another question.",
        `Chart displayed: <strong>${currentTicker}</strong>`
      );
    }
  });
}

function speakVoiceSummary(text) {
  const enabled = document.getElementById("tts-enabled")?.checked;
  if (!enabled) return;
  speakText(text);
}

function startInteractiveVoiceSession(triggerBtnId, mode = "coordinator") {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    alert("Interactive Voice requires Chrome or Edge (Web Speech API). Please type your request instead.");
    return;
  }

  // Toggle OFF if user clicks the same active mic button
  if (isVoiceSessionActive && activeTriggerButtonId === triggerBtnId) {
    stopAllVoiceInteraction("⏹️ Voice session stopped by user.");
    return;
  }

  // Cancel any existing speech or recognition first
  stopAllVoiceInteraction();

  const sessionToken = ++voiceSessionToken;
  isVoiceSessionActive = true;
  activeTriggerButtonId = triggerBtnId;

  const triggerBtn = document.getElementById(triggerBtnId);
  if (triggerBtn) {
    triggerBtn.classList.add("recording");
    triggerBtn.textContent = "⏹️ Stop Voice";
  }

  // Scroll the top Interactive Voice Console & Top Stock Chart into view immediately
  const topSec = document.getElementById("top-chart-section");
  if (topSec) topSec.scrollIntoView({ behavior: "smooth", block: "start" });

  // STEP 1: Speak greeting "How can I help you today?" BEFORE opening microphone
  const greetingText = "How can I help you today?";
  setVoiceConsoleState(
    "greeting",
    `🤖 <strong>OmniMarket Agent:</strong> "${greetingText}"`,
    "Preparing microphone after greeting... Click <strong>⏹️ Stop Response</strong> to cancel."
  );

  let micStarted = false;
  function beginListeningPhase() {
    if (micStarted || sessionToken !== voiceSessionToken) return;
    micStarted = true;
    openMicrophoneForRequest(sessionToken, triggerBtnId, mode);
  }

  if (window.speechSynthesis) {
    window.speechSynthesis.cancel();
    const greetUtter = new SpeechSynthesisUtterance(greetingText);
    greetUtter.rate = 1.06;
    greetUtter.onend = () => beginListeningPhase();
    greetUtter.onerror = () => beginListeningPhase();
    window.speechSynthesis.speak(greetUtter);
    // Fallback timer in case browser speech synthesis is muted or onend is delayed
    voiceSafetyTimer = setTimeout(() => beginListeningPhase(), 2200);
  } else {
    beginListeningPhase();
  }
}

function openMicrophoneForRequest(sessionToken, triggerBtnId, mode) {
  if (sessionToken !== voiceSessionToken) return;

  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRec();
  activeRecognition = recognition;
  recognition.lang = "en-US";
  recognition.continuous = false;
  recognition.interimResults = true;
  recognition.maxAlternatives = 1;

  let finalTranscript = "";
  let previewChartTicker = null;

  setVoiceConsoleState(
    "listening",
    `🎙️ <strong>Listening:</strong> Speak your stock or question now (e.g., <em>"Analyze Apple"</em>, <em>"Tell me everything about Nvidia"</em>, <em>"Buy 5 shares of Microsoft"</em>)...`,
    "As soon as you mention a stock, its live interactive chart will display below."
  );

  // 10-second listening timeout so mic never stays stuck open if room is quiet
  if (voiceSafetyTimer) clearTimeout(voiceSafetyTimer);
  voiceSafetyTimer = setTimeout(() => {
    if (sessionToken === voiceSessionToken && activeRecognition) {
      try {
        activeRecognition.stop();
      } catch (_) {}
    }
  }, 10000);

  recognition.onresult = (event) => {
    if (sessionToken !== voiceSessionToken) return;

    let interimTranscript = "";
    for (let i = event.resultIndex; i < event.results.length; i++) {
      const textPiece = event.results[i][0].transcript;
      if (event.results[i].isFinal) {
        finalTranscript += textPiece + " ";
      } else {
        interimTranscript += textPiece;
      }
    }

    const combined = (finalTranscript + interimTranscript).trim();
    if (combined) {
      setVoiceConsoleState(
        "listening",
        `🗣️ <strong>Hearing:</strong> "${combined}"`,
        "Detecting stock ticker & updating live chart..."
      );

      // Immediately display the stock chart on screen as soon as a ticker is heard!
      const detectedSym = tryExtractExplicitTicker(combined);
      if (detectedSym && detectedSym !== previewChartTicker) {
        previewChartTicker = detectedSym;
        loadChart(detectedSym, { scrollIntoView: false, syncTopInput: true });
      }
    }
  };

  recognition.onerror = () => {
    if (sessionToken !== voiceSessionToken) return;
    if (!finalTranscript.trim()) {
      stopAllVoiceInteraction("⚠️ No speech detected. Click <strong>'🎙️ Talk to OmniMarket'</strong> to try again.");
    }
  };

  recognition.onend = () => {
    if (sessionToken !== voiceSessionToken) return;
    if (voiceSafetyTimer) {
      clearTimeout(voiceSafetyTimer);
      voiceSafetyTimer = null;
    }

    const spokenQuery = finalTranscript.trim();
    if (!spokenQuery) {
      stopAllVoiceInteraction("⚠️ No voice request heard. Click <strong>'🎙️ Talk to OmniMarket'</strong> to try again.");
      return;
    }

    // Populate UI inputs with what the user said
    const chatIn = document.getElementById("chat-input");
    if (chatIn) chatIn.value = spokenQuery;
    const drIn = document.getElementById("deep-research-input");
    if (drIn && mode === "research") drIn.value = spokenQuery;

    handleInteractiveVoiceRequest(spokenQuery, mode, sessionToken);
  };

  try {
    recognition.start();
  } catch (_) {
    stopAllVoiceInteraction("⚠️ Microphone already in use or permission denied.");
  }
}

async function handleInteractiveVoiceRequest(spokenQuery, mode, sessionToken) {
  if (sessionToken !== voiceSessionToken) return;

  // Resolve ticker & immediately display the Top Interactive Stock Chart on screen
  const targetSym = resolveTickerFromInput(spokenQuery);
  setVoiceConsoleState(
    "analyzing",
    `⚙️ <strong>Analyzing "${spokenQuery}"</strong> — Displaying <strong>${targetSym}</strong> stock chart & running all sub-agents...`,
    "Running TechnicalIndicatorSubAgent, AnalystForecastSubAgent, SmartMoneyIndexSubAgent & DeepResearchSubAgent..."
  );

  // Display chart on screen right away while interacting
  await loadChart(targetSym, { scrollIntoView: true, syncTopInput: true });
  if (sessionToken !== voiceSessionToken) return;

  // Run full multi-agent coordinator request (includes Technical + Analyst + SmartMoney + DeepResearch + TradeExecution)
  appendChatMessage("user", spokenQuery, "🎤 Interactive Voice Input");
  const res = await fetch("/api/agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: spokenQuery,
      modality: "voice",
      selected_ticker: targetSym,
      session_id: "interactive_voice_session",
    }),
  });
  const data = await res.json();
  if (sessionToken !== voiceSessionToken) return;

  const meta = `Model: ${data.model_routing?.synthesis_tier || "gemini-2.5-pro"} • Groundedness: ${data.self_evaluation?.groundedness_score || 1.0} • Trace: ${(data.trace_id || "").slice(0, 8)}`;
  appendChatMessage("assistant", data.response_text, meta);

  // Ensure the chart displays the authoritative ticker resolved by the backend
  const finalSym = data.active_ticker || targetSym;
  await loadChart(finalSym, { scrollIntoView: true, syncTopInput: true });
  if (sessionToken !== voiceSessionToken) return;

  // Also update the Deep Stock Research Studio UI with the deep research report returned by the backend
  if (data.deep_research_report && data.deep_research_report.status === "SUCCESS") {
    lastDeepResearchVoiceText = data.deep_research_report.voice_briefing || data.voice_summary || "";
    renderDeepResearchReport(data.deep_research_report, data.model_routing, data.trace_id);
  }

  if (data.portfolio_summary) {
    updatePortfolioUI(data.portfolio_summary);
  }

  // Speak the comprehensive response covering everything, with full Stop Response control
  const spokenReply = (mode === "research" && lastDeepResearchVoiceText)
    ? lastDeepResearchVoiceText
    : (data.voice_summary || "Analysis complete and displayed on screen.");

  speakSentenceQueue(spokenReply, sessionToken, () => {
    if (sessionToken === voiceSessionToken) {
      isVoiceSessionActive = false;
      activeTriggerButtonId = null;
      resetAllMicButtons();
      setVoiceConsoleState(
        "idle",
        `✅ <strong>Completed Voice Briefing for ${finalSym}.</strong> Click <strong>'🎙️ Talk to OmniMarket'</strong> to ask a follow-up question.`,
        `Interactive Stock Chart & Deep Research Dossier for <strong>${finalSym}</strong> are displayed below.`
      );
    }
  });
}

/* ============================================================================
 * Dedicated Multi-Modal Deep Stock Research Studio (DeepResearchSubAgent)
 * ============================================================================ */

async function runDeepStockResearch(queryOrTicker, modality = "text", autoSpeak = false, syncChart = true) {
  const cleaned = (queryOrTicker || "").trim();
  if (!cleaned) return;

  const guessedTicker = resolveTickerFromInput(cleaned);
  if (syncChart && guessedTicker) {
    loadChart(guessedTicker, { scrollIntoView: true, syncTopInput: true });
  }

  const container = document.getElementById("deep-research-results");
  container.innerHTML = `<div style="padding:10px;color:var(--text-muted);font-weight:600;">🔬 Running DeepResearchSubAgent (Company Moat + Live Google Finance Technical Buy/Sell/Hold Synthesis) for "${cleaned}"...</div>`;

  const res = await fetch("/api/research/deep", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: cleaned,
      modality,
      selected_ticker: guessedTicker || currentTicker,
      session_id: "deep_research_studio_session",
    }),
  });
  const payload = await res.json();

  if (payload.status !== "SUCCESS" || !payload.report) {
    container.innerHTML = `<div class="hitl-box">⚠️ ${payload.error_message || payload.llm_recovery_instruction || "Unable to complete deep research."}</div>`;
    return;
  }

  const r = payload.report;
  lastDeepResearchVoiceText = r.voice_briefing || "";
  renderDeepResearchReport(r, payload.model_routing, payload.trace_id);

  if (r.ticker && syncChart) {
    await loadChart(r.ticker, { scrollIntoView: false, syncTopInput: true });
  }

  const ttsToggle = document.getElementById("research-tts-enabled");
  if ((autoSpeak || modality === "voice") && ttsToggle && ttsToggle.checked && lastDeepResearchVoiceText) {
    speakText(lastDeepResearchVoiceText);
  }
}

function renderDeepResearchReport(r, routing, traceId) {
  const container = document.getElementById("deep-research-results");
  const comp = r.company_research || {};
  const tech = r.technical_research || {};
  const ans = r.analyst_and_smart_money || {};
  const fund = comp.fundamentals || {};

  const rec = r.final_recommendation || "HOLD";
  const badgeCls = rec === "BUY" ? "buy" : rec === "SELL" ? "sell" : "hold";
  const tradeSide = rec === "SELL" ? "SELL" : "BUY";
  const divMeta = getDivergenceBadgeMeta(tech.divergence_status);

  const moatDriversHtml = (comp.moat_drivers || []).map(d => `<li>${d}</li>`).join("");
  const catalystsHtml = (comp.bull_catalysts || []).map(c => `<li><strong>✓</strong> ${c}</li>`).join("");
  const risksHtml = (comp.bear_risks || []).map(rk => `<li><strong>⚠️</strong> ${rk}</li>`).join("");

  const smartSummary = [
    ans.in_congressional_leaders_index ? `🏛️ Congress (${(ans.congressional_holders || []).length} filing[s])` : "🏛️ Congress: None",
    ans.in_tom_lee_fundstrat_index ? `🎯 Tom Lee GRNY (${(ans.tom_lee_fundstrat_themes || []).join(", ")})` : "🎯 Tom Lee: Not in core list"
  ].join(" • ");

  container.innerHTML = `
    <div class="dr-verdict-banner">
      <div>
        <div style="font-size:15px;font-weight:800;">
          ${r.ticker} — ${r.company_name} ($${Number(tech.price || 0).toFixed(2)})
          <span class="signal-badge ${badgeCls}" style="margin-left:8px;font-size:12px;">
            VERDICT: ${r.final_recommendation} (${r.conviction_tier} • ${r.conviction_score}/100)
          </span>
        </div>
        <div style="font-size:11.5px;color:var(--text-muted);margin-top:3px;">
          ${comp.sector} • ${comp.industry} •
          <a href="${r.google_finance_url}" target="_blank" rel="noopener" class="gf-link">🔗 Google Finance (${r.google_finance_symbol})</a> •
          Model: <strong>${routing?.selected_model || routing?.synthesis_tier || "gemini-2.5-pro"}</strong> • Trace: <code>${(traceId || "").slice(0, 8)}</code>
        </div>
      </div>
      <div style="display:flex;gap:8px;align-items:center;">
        <button type="button" class="btn-secondary btn-sm" onclick="loadChart('${r.ticker}', { scrollIntoView: true, syncTopInput: true })">
          📈 Focus Top Chart
        </button>
        <button type="button" class="btn-action" onclick="submitDirectOrder('${r.ticker}', '${tradeSide}', 5)">
          ⚡ Execute ${tradeSide} 5 ${r.ticker}
        </button>
      </div>
    </div>

    <div class="dr-grid">
      <!-- Column 1: Company Fundamentals & Competitive Moat -->
      <div class="dr-card">
        <h4>
          <span>🏢 1. Company Research &amp; Competitive Moat</span>
          <span class="dr-subbadge">${comp.moat_rating || "Institutional Profile"}</span>
        </h4>
        <p style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">
          ${comp.business_model || ""}
        </p>

        <div class="dr-metrics-row">
          <div class="dr-metric-pill">
            <span class="m-lbl">Fwd P/E</span>
            <span class="m-val">${fund.forward_pe_est || "—"}x</span>
          </div>
          <div class="dr-metric-pill">
            <span class="m-lbl">Rev YoY</span>
            <span class="m-val pos">+${fund.revenue_growth_yoy_pct || 0}%</span>
          </div>
          <div class="dr-metric-pill">
            <span class="m-lbl">Gross Margin</span>
            <span class="m-val">${fund.gross_margin_pct || 0}%</span>
          </div>
          <div class="dr-metric-pill">
            <span class="m-lbl">FCF Margin</span>
            <span class="m-val">${fund.fcf_margin_pct || 0}%</span>
          </div>
          <div class="dr-metric-pill">
            <span class="m-lbl">ROIC</span>
            <span class="m-val">${fund.roic_pct || 0}%</span>
          </div>
        </div>

        <div style="font-size:11.5px;font-weight:700;margin-top:6px;">Competitive Moat Drivers:</div>
        <ul class="dr-list">${moatDriversHtml}</ul>

        <div style="font-size:11.5px;font-weight:700;margin-top:6px;color:var(--emerald);">Bullish Growth Catalysts:</div>
        <ul class="dr-list">${catalystsHtml}</ul>

        <div style="font-size:11.5px;font-weight:700;margin-top:6px;color:var(--crimson);">Key Risks &amp; Downside Factors:</div>
        <ul class="dr-list">${risksHtml}</ul>
      </div>

      <!-- Column 2: Technical Analysis Buy / Sell / Hold Verdict -->
      <div class="dr-card">
        <h4>
          <span>📈 2. Technical Analysis to Buy, Sell, or Hold</span>
          <span class="signal-badge ${badgeCls}">${r.final_recommendation}</span>
        </h4>
        <p style="font-size:12px;color:var(--text-secondary);margin-bottom:8px;">
          ${tech.technical_thesis || ""}
        </p>

        <div class="dr-metrics-row">
          <div class="dr-metric-pill">
            <span class="m-lbl">Live Price</span>
            <span class="m-val">$${Number(tech.price || 0).toFixed(2)}</span>
          </div>
          <div class="dr-metric-pill">
            <span class="m-lbl">RSI (14)</span>
            <span class="m-val">${Number(tech.rsi_14 || 0).toFixed(1)}</span>
          </div>
          <div class="dr-metric-pill">
            <span class="m-lbl">10d ROC</span>
            <span class="m-val ${tech.momentum_roc_10d_pct >= 0 ? 'pos' : 'neg'}">${formatPct(tech.momentum_roc_10d_pct)}</span>
          </div>
          <div class="dr-metric-pill">
            <span class="m-lbl">Support 1</span>
            <span class="m-val">$${Number(tech.support_level_1 || 0).toFixed(2)}</span>
          </div>
          <div class="dr-metric-pill">
            <span class="m-lbl">Resistance 1</span>
            <span class="m-val">$${Number(tech.resistance_level_1 || 0).toFixed(2)}</span>
          </div>
        </div>

        <ul class="dr-list">
          <li><strong>Moving Averages (9 / 20 / 50 / 200 SMA):</strong> $${tech.sma_9?.toFixed(2)} / $${tech.sma_20?.toFixed(2)} / $${tech.sma_50?.toFixed(2)} / $${tech.sma_200?.toFixed(2)} (<code>${tech.ma_alignment}</code>)</li>
          <li><strong>Price-RSI Divergence:</strong> <span class="div-pill ${divMeta.pillCls}">${divMeta.label}</span> — ${tech.divergence_explanation}</li>
          <li><strong>Actionable Entry / Positioning Plan:</strong> ${tech.optimal_entry_zone}</li>
          <li><strong>Risk Invalidation / Stop-Loss Level:</strong> <span class="neg">$${Number(tech.stop_loss_invalidation || 0).toFixed(2)}</span> (Support 2: $${Number(tech.support_level_2 || 0).toFixed(2)})</li>
          <li><strong>Wall Street Analyst Forecast:</strong> <strong>${ans.consensus_rating}</strong> (${ans.num_analysts} analysts) • 12M Target Mean <strong>$${Number(ans.target_price_mean || 0).toFixed(2)}</strong> (<span class="${ans.implied_upside_pct >= 0 ? 'pos' : 'neg'}">${formatPct(ans.implied_upside_pct)}</span> upside)</li>
          <li><strong>Smart Money Conviction:</strong> ${smartSummary}</li>
        </ul>
      </div>
    </div>
  `;
}

/* ============================================================================
 * 24/7 Screener, Flashing Ribbon & Index Cards
 * ============================================================================ */

async function fetchDashboard() {
  const url = currentIndexFilter ? `/api/dashboard?index=${encodeURIComponent(currentIndexFilter)}` : "/api/dashboard";
  const res = await fetch(url);
  dashboardData = await res.json();
  secondsRemaining = dashboardData.seconds_until_next_refresh || 180;
  renderFlashingRibbon(dashboardData.flashing_alerts || []);
  renderIndexCards(dashboardData.indices || {});
  renderScreenerTable(dashboardData.equities || []);
}

function renderFlashingRibbon(alerts) {
  const box = document.getElementById("flash-ribbon-items");
  if (!alerts.length) {
    box.innerHTML = "<span>No extreme indicator flashes in current cycle.</span>";
    return;
  }
  box.innerHTML = alerts.map(a => {
    const cls = a.action_signal.includes("BUY") || String(a.divergence_status).includes("BULLISH") ? "buy" : "sell";
    return `<span class="flash-chip ${cls}" onclick="loadChart('${a.ticker}', { scrollIntoView: true, syncTopInput: true }); runDeepStockResearch('${a.ticker}', 'text', false, false);">
      ${a.ticker} $${a.price.toFixed(2)} (${formatPct(a.daily_change_pct)}) • ${a.action_signal} • ${a.flash_type.replace("FLASH_", "")}
    </span>`;
  }).join("");
}

function renderIndexCards(indices) {
  const strip = document.getElementById("index-strip");
  const order = ["DJIA", "NASDAQ_100", "SP500", "IWM_RUSSELL3000", "VALUE_STOCKS", "CONGRESSIONAL_LEADERS", "TOM_LEE_FUNDSTRAT"];
  strip.innerHTML = order.filter(k => indices[k]).map(k => {
    const idx = indices[k];
    const cls = idx.avg_daily_change_pct >= 0 ? "pos" : "neg";
    const activeCls = currentIndexFilter === k ? "active" : "";
    return `<div class="index-card ${activeCls}" onclick="selectIndexTab('${k}')">
      <div class="idx-name" title="${idx.name}">${idx.name}</div>
      <div class="idx-metrics">
        <span class="${cls}">${formatPct(idx.avg_daily_change_pct)}</span>
        <span style="color:var(--text-muted);font-size:11px;">${idx.buy_signal_count}/${idx.constituent_count} Buys</span>
      </div>
    </div>`;
  }).join("");
}

function renderScreenerTable(rows) {
  const q = (document.getElementById("ticker-search").value || "").trim().toUpperCase();
  const filtered = rows.filter(r => !q || r.ticker.includes(q) || (r.company_name || "").toUpperCase().includes(q));
  const tbody = document.getElementById("screener-tbody");

  tbody.innerHTML = filtered.slice(0, 150).map(r => {
    const chgCls = r.daily_change_pct >= 0 ? "pos" : "neg";
    const sigCls = r.action_signal.includes("BUY") ? "buy" : r.action_signal.includes("SELL") ? "sell" : "hold";
    const rowFlash = r.flash_alert ? (r.action_signal.includes("BUY") ? "row-flash-buy" : "row-flash-sell") : "";
    const divMeta = getDivergenceBadgeMeta(r.divergence_status);
    const smartBadges = [
      r.in_congressional_leaders ? "🏛️ Cong" : "",
      r.in_tom_lee_fundstrat ? "🎯 TomLee" : ""
    ].filter(Boolean).join(" ") || "—";

    return `<tr class="${rowFlash}" onclick="loadChart('${r.ticker}', { scrollIntoView: true, syncTopInput: true })">
      <td><strong>${r.ticker}</strong><br/><span style="font-size:10px;color:var(--text-muted);">${(r.company_name || "").slice(0, 18)}</span></td>
      <td><strong>$${r.price.toFixed(2)}</strong></td>
      <td class="${chgCls}">${formatPct(r.daily_change_pct)}</td>
      <td class="${r.momentum_roc_10d_pct >= 0 ? 'pos' : 'neg'}">${formatPct(r.momentum_roc_10d_pct)}</td>
      <td>${r.rsi_14.toFixed(1)}</td>
      <td style="font-size:11px;">${r.sma_9.toFixed(0)} / ${r.sma_20.toFixed(0)} / ${r.sma_50.toFixed(0)} / ${r.sma_200.toFixed(0)}</td>
      <td><span class="div-pill ${divMeta.pillCls}" title="${r.divergence_explanation || ''}">${divMeta.label}</span></td>
      <td>$${r.target_price_mean.toFixed(2)} <span class="${r.implied_upside_pct >= 0 ? 'pos' : 'neg'}">(${formatPct(r.implied_upside_pct)})</span></td>
      <td style="font-size:11px;">${smartBadges}</td>
      <td><span class="signal-badge ${sigCls}">${r.action_signal}</span></td>
      <td onclick="event.stopPropagation()" style="display:flex;gap:4px;">
        <button class="btn-secondary btn-sm" onclick="runDeepStockResearch('${r.ticker}', 'text', false, true)" title="Run Deep Company + Technical Research &amp; Update Top Chart">🔬 Research</button>
        <button class="btn-buy" style="padding:3px 7px;font-size:10.5px;" onclick="submitDirectOrder('${r.ticker}', 'BUY', 5)">Buy</button>
      </td>
    </tr>`;
  }).join("");
}

function selectIndexTab(indexId) {
  currentIndexFilter = indexId;
  document.querySelectorAll(".filter-tabs .tab").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.index === indexId);
  });
  fetchDashboard();
}

/* ============================================================================
 * Portfolio, HITL Gate & Multi-Modal Voice / Text Coordinator Chat
 * ============================================================================ */

async function fetchPortfolio() {
  const res = await fetch("/api/portfolio");
  const pf = await res.json();
  updatePortfolioUI(pf);
}

function updatePortfolioUI(pf) {
  document.getElementById("header-equity").textContent = `$${Number(pf.total_equity_usd || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;
  document.getElementById("header-cash").textContent = `$${Number(pf.cash_usd || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}`;

  const hitlBox = document.getElementById("hitl-pending-box");
  const pending = pf.pending_hitl_orders || [];
  if (pending.length > 0) {
    hitlBox.classList.remove("hidden");
    hitlBox.innerHTML = pending.map(p => `
      <div style="margin-bottom:6px;">
        <strong>⚠️ HITL Confirmation Required:</strong> ${p.side} ${p.quantity} ${p.ticker} (~$${p.estimated_notional_usd.toLocaleString()})<br/>
        <button class="btn-buy" style="padding:4px 8px;margin-top:4px;" onclick="confirmHitlOrder('${p.confirmation_token}', 'APPROVE')">✓ Approve (${p.confirmation_token})</button>
        <button class="btn-sell" style="padding:4px 8px;margin-top:4px;" onclick="confirmHitlOrder('${p.confirmation_token}', 'REJECT')">✕ Reject</button>
      </div>
    `).join("");
  } else {
    hitlBox.classList.add("hidden");
  }

  const posBox = document.getElementById("positions-list");
  const positions = pf.positions || [];
  if (!positions.length) {
    posBox.innerHTML = `<div style="color:var(--text-muted);font-size:11.5px;">No open positions. Use Voice/Text or Quick Trade to BUY.</div>`;
    return;
  }
  posBox.innerHTML = positions.map(p => `
    <div style="display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border-subtle);font-size:11.5px;">
      <span><strong>${p.ticker}</strong> (${p.quantity} sh @ $${p.avg_cost_usd.toFixed(2)})</span>
      <span class="${p.unrealized_pnl_usd >= 0 ? 'pos' : 'neg'}">$${p.market_value_usd.toFixed(2)} (${formatPct(p.unrealized_pnl_pct)})</span>
    </div>
  `).join("");
}

async function submitDirectOrder(ticker, side, quantity) {
  const res = await fetch("/api/trade/order", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker, side, quantity: Number(quantity) }),
  });
  const data = await res.json();
  updatePortfolioUI(data.portfolio);
  const tr = data.trade_result;
  if (tr.status === "HITL_CONFIRMATION_REQUIRED") {
    appendChatMessage("assistant", `⚠️ **Human-in-the-Loop Gate Triggered** (\`${tr.confirmation_token}\`): ${tr.message}`, "TradeExecutionSubAgent");
  } else if (tr.status === "FILLED") {
    appendChatMessage("assistant", `✅ **Order Filled**: ${tr.side} ${tr.quantity} ${tr.ticker} @ $${tr.fill_price_usd.toFixed(2)}`, "TradeExecutionSubAgent");
  } else {
    appendChatMessage("assistant", `⚠️ **Order Error**: ${tr.error_message || JSON.stringify(tr)}`, "TradeExecutionSubAgent");
  }
}

async function confirmHitlOrder(token, decision) {
  const res = await fetch("/api/trade/confirm", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirmation_token: token, decision }),
  });
  const data = await res.json();
  updatePortfolioUI(data.portfolio);
  const tr = data.trade_result;
  appendChatMessage("assistant", `HITL Decision **${decision}** processed for \`${token}\` -> Status: **${tr.status}**`, "HumanInTheLoopApprovalGate");
}

function formatSimpleMarkdown(md) {
  return (md || "")
    .replace(/^### (.*)$/gm, "<h4>$1</h4>")
    .replace(/^#### (.*)$/gm, "<h5>$1</h5>")
    .replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" class="gf-link">$1</a>')
    .replace(/\n/g, "<br/>");
}

function appendChatMessage(role, text, metaText) {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = `msg ${role}`;
  div.innerHTML = `<div class="msg-meta">${metaText || (role === "user" ? "You" : "OmniMarket Coordinator")}</div>
                   <div class="msg-body">${formatSimpleMarkdown(text)}</div>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

async function sendAgentQuery(queryText, modality = "text") {
  if (!queryText.trim()) return;
  appendChatMessage("user", queryText, modality === "voice" ? "🎤 Voice Input" : "⌨️ Text Input");

  const res = await fetch("/api/agent/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query: queryText,
      modality,
      selected_ticker: currentTicker,
      session_id: "terminal_session_1",
    }),
  });
  const data = await res.json();
  const meta = `Model: ${data.model_routing?.synthesis_tier || "gemini-2.5-pro"} • Groundedness: ${data.self_evaluation?.groundedness_score || 1.0} • Trace: ${(data.trace_id || "").slice(0, 8)}`;
  appendChatMessage("assistant", data.response_text, meta);

  if (data.active_ticker) {
    loadChart(data.active_ticker, { scrollIntoView: true, syncTopInput: true });
  }
  if (data.deep_research_report && data.deep_research_report.status === "SUCCESS") {
    lastDeepResearchVoiceText = data.deep_research_report.voice_briefing || "";
    renderDeepResearchReport(data.deep_research_report, data.model_routing, data.trace_id);
  }
  if (data.portfolio_summary) {
    updatePortfolioUI(data.portfolio_summary);
  }
  if (data.voice_summary && modality === "voice") {
    speakVoiceSummary(data.voice_summary);
  }
}

document.addEventListener("DOMContentLoaded", () => {
  initChart();
  fetchDashboard();
  fetchPortfolio();
  loadChart("NVDA", { scrollIntoView: false, syncTopInput: true });
  runDeepStockResearch("NVDA", "text", false, false);

  // 1. Interactive Voice Assistant Controls ("How can I help you today?" -> Listen -> Chart -> Speak Everything -> Stop Anytime)
  document.getElementById("btn-start-voice-assistant")?.addEventListener("click", () => {
    startInteractiveVoiceSession("btn-start-voice-assistant", "coordinator");
  });
  document.getElementById("btn-top-mic")?.addEventListener("click", () => {
    startInteractiveVoiceSession("btn-top-mic", "coordinator");
  });
  document.getElementById("btn-research-mic")?.addEventListener("click", () => {
    startInteractiveVoiceSession("btn-research-mic", "research");
  });
  document.getElementById("btn-mic")?.addEventListener("click", () => {
    startInteractiveVoiceSession("btn-mic", "coordinator");
  });

  // Stop Response Buttons + Escape Key Interrupt
  ["btn-stop-voice-response", "btn-stop-research-voice", "btn-stop-chat-voice"].forEach(id => {
    document.getElementById(id)?.addEventListener("click", () => {
      stopAllVoiceInteraction("⏹️ Voice response stopped by user.");
    });
  });

  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && (isVoiceSessionActive || window.speechSynthesis?.speaking)) {
      stopAllVoiceInteraction("⏹️ Voice response stopped via Escape key.");
    }
  });

  // 2. Top Hero Chart Search Form & Quick Ticker Chips
  const topSearchForm = document.getElementById("top-stock-search-form");
  if (topSearchForm) {
    topSearchForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const raw = document.getElementById("top-stock-search-input").value.trim() || currentTicker;
      const sym = resolveTickerFromInput(raw);
      document.getElementById("top-stock-search-input").value = sym;
      await loadChart(sym, { scrollIntoView: true, syncTopInput: true });
      runDeepStockResearch(sym, "text", false, false);
    });
  }

  document.querySelectorAll(".top-ticker-chip").forEach(chip => {
    chip.addEventListener("click", async () => {
      const sym = chip.dataset.ticker;
      document.getElementById("top-stock-search-input").value = sym;
      await loadChart(sym, { scrollIntoView: true, syncTopInput: true });
      runDeepStockResearch(sym, "text", false, false);
    });
  });

  // 3. Theme Toggle (Light Mode Default)
  const themeBtn = document.getElementById("btn-theme-toggle");
  if (themeBtn) {
    themeBtn.addEventListener("click", toggleUiTheme);
  }

  // 4. Deep Research Search Form & Quick Chips
  document.getElementById("deep-research-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = document.getElementById("deep-research-input");
    const q = input.value.trim() || currentTicker;
    runDeepStockResearch(q, "text", false, true);
  });

  document.querySelectorAll(".dr-chip").forEach(chip => {
    chip.addEventListener("click", () => {
      const sym = chip.dataset.ticker;
      document.getElementById("deep-research-input").value = sym;
      runDeepStockResearch(sym, "text", false, true);
    });
  });

  document.getElementById("btn-play-research-voice").addEventListener("click", () => {
    if (lastDeepResearchVoiceText) speakText(lastDeepResearchVoiceText);
  });

  // 5. Screener Filter Tabs & Search-to-Chart Sync
  document.querySelectorAll(".filter-tabs .tab").forEach(btn => {
    btn.addEventListener("click", () => selectIndexTab(btn.dataset.index));
  });

  const tickerSearchInput = document.getElementById("ticker-search");
  tickerSearchInput.addEventListener("input", () => {
    if (!dashboardData) return;
    const rows = dashboardData.equities || [];
    renderScreenerTable(rows);
    const q = tickerSearchInput.value.trim().toUpperCase();
    if (!q) return;
    const exactMatch = rows.find(r => r.ticker === q);
    if (exactMatch) {
      loadChart(exactMatch.ticker, { scrollIntoView: false, syncTopInput: true });
    }
  });

  const screenerSearchForm = document.getElementById("screener-search-form");
  if (screenerSearchForm) {
    screenerSearchForm.addEventListener("submit", (e) => {
      e.preventDefault();
      const q = tickerSearchInput.value.trim();
      if (!q) return;
      const sym = resolveTickerFromInput(q);
      loadChart(sym, { scrollIntoView: true, syncTopInput: true });
    });
  }

  // 6. Manual 3-Minute Refresh Button
  document.getElementById("btn-refresh-now").addEventListener("click", async () => {
    await fetch("/api/daemon/refresh", { method: "POST" });
    await fetchDashboard();
    await loadChart(currentTicker, { scrollIntoView: false, syncTopInput: true });
  });

  // 7. Coordinator Chat Form & Quick Prompts
  document.getElementById("chat-form").addEventListener("submit", (e) => {
    e.preventDefault();
    const input = document.getElementById("chat-input");
    const q = input.value;
    input.value = "";
    sendAgentQuery(q, "text");
  });

  document.querySelectorAll(".quick-prompts .chip").forEach(chip => {
    chip.addEventListener("click", () => sendAgentQuery(chip.dataset.prompt, "text"));
  });

  // 8. Quick Trade Buy / Sell
  document.getElementById("btn-buy").addEventListener("click", () => {
    submitDirectOrder(
      document.getElementById("trade-ticker").value,
      "BUY",
      document.getElementById("trade-qty").value
    );
  });

  document.getElementById("btn-sell").addEventListener("click", () => {
    submitDirectOrder(
      document.getElementById("trade-ticker").value,
      "SELL",
      document.getElementById("trade-qty").value
    );
  });

  // 9. 24/7 3-Minute Countdown Timer
  setInterval(() => {
    secondsRemaining = Math.max(0, secondsRemaining - 1);
    const m = String(Math.floor(secondsRemaining / 60)).padStart(2, "0");
    const s = String(secondsRemaining % 60).padStart(2, "0");
    document.getElementById("countdown-timer").textContent = `${m}:${s}`;
    if (secondsRemaining === 0) {
      fetchDashboard();
      loadChart(currentTicker, { scrollIntoView: false, syncTopInput: false });
      secondsRemaining = 180;
    }
  }, 1000);
});
