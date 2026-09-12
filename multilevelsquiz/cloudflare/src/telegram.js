/**
 * Telegram Bot API Client & Webhook Command Handler for VocabCNQuiz
 */

import {
  triggerGitHubIdeationWorkflow,
  triggerGitHubRenderWorkflow,
  triggerGitHubQCWorkflow
} from "./github_trigger.js";

/**
 * Send HTML message to Telegram Chat with automatic plain-text fallback
 */
export async function sendTelegramMessage(botToken, chatId, text, options = {}) {
  if (!botToken || !chatId) {
    console.warn("[TELEGRAM] Bot token or chat ID missing. Notification skipped.");
    return null;
  }

  const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
  const body = {
    chat_id: chatId,
    text: text,
    parse_mode: options.parse_mode || "HTML",
    disable_web_page_preview: options.disable_web_page_preview ?? true,
    ...options
  };

  if (body.reply_markup === null || body.reply_markup === undefined) {
    delete body.reply_markup;
  }

  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (!data.ok && data.description && data.description.includes("parse entities")) {
      const plainText = text.replace(/<[^>]*>/g, "");
      const retryRes = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chat_id: chatId,
          text: plainText,
          disable_web_page_preview: true
        })
      });
      return await retryRes.json();
    }
    return data;
  } catch (err) {
    console.error("[TELEGRAM] Failed to send message:", err);
    return null;
  }
}

/**
 * Answer Telegram Callback Query
 */
export async function answerTelegramCallback(botToken, callbackQueryId, text = "", showAlert = false) {
  if (!botToken || !callbackQueryId) return null;

  const url = `https://api.telegram.org/bot${botToken}/answerCallbackQuery`;
  try {
    const res = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        callback_query_id: callbackQueryId,
        text: text,
        show_alert: showAlert
      })
    });
    return await res.json();
  } catch (err) {
    console.error("[TELEGRAM] Failed to answer callback query:", err);
    return null;
  }
}

/**
 * Handle Telegram Update asynchronously
 */
export async function handleTelegramUpdate(update, env, config) {
  const botToken = config.telegramBotToken;
  if (!botToken) return;

  // 1. Handle Callback Queries (Inline buttons)
  if (update.callback_query) {
    const cb = update.callback_query;
    const cbId = cb.id;
    const cbData = cb.data || "";
    const chatId = cb.message?.chat?.id;

    if (cbData.startsWith("cmd_") || cbData.startsWith("render") || cbData.startsWith("qc") || cbData.startsWith("ideate")) {
      await answerTelegramCallback(botToken, cbId, "⏳ Đang xử lý yêu cầu...", false);
      if (cbData.includes("ideate")) {
        await triggerGitHubIdeationWorkflow(env, { mode: "batch", count: 1 });
        if (chatId) await sendTelegramMessage(botToken, chatId, "💡 <b>[GitHub Actions]</b> Đã kích hoạt sinh ý tưởng mới.");
      } else if (cbData.includes("render")) {
        const rowId = cbData.includes(":") ? cbData.split(":")[1] : "";
        await triggerGitHubRenderWorkflow(env, { row_id: rowId });
        if (chatId) await sendTelegramMessage(botToken, chatId, `🎬 <b>[GitHub Actions]</b> Đã kích hoạt Render video ${rowId ? '#' + rowId : 'toàn bộ Pending'}.`);
      } else if (cbData.includes("qc")) {
        const rowId = cbData.includes(":") ? cbData.split(":")[1] : "";
        await triggerGitHubQCWorkflow(env, { row_id: rowId });
        if (chatId) await sendTelegramMessage(botToken, chatId, `🛡️ <b>[GitHub Actions]</b> Đã kích hoạt Auto-QC ${rowId ? '#' + rowId : ''}.`);
      }
    }
    return;
  }

  // 2. Handle Text Commands
  if (update.message && update.message.text) {
    const text = update.message.text.trim();
    const chatId = update.message.chat.id;

    if (text === "/start" || text === "/help") {
      await sendTelegramMessage(botToken, chatId, getHelpMessage(config.sheetTabName));
      return;
    }

    if (text === "/myid") {
      await sendTelegramMessage(botToken, chatId, `🆔 <b>Chat ID:</b> <code>${chatId}</code>\n<b>Pipeline:</b> <code>${config.sheetTabName || "vocabCN"}</code>`);
      return;
    }

    if (text === "/ideate" || text === "/sinh1") {
      await triggerGitHubIdeationWorkflow(env, { mode: "batch", count: 1 });
      await sendTelegramMessage(botToken, chatId, `💡 <b>[Kích Hoạt Sinh Ý Tưởng]</b>\n\n🚀 Đã dispatch workflow GitHub Actions sinh 1 batch mới.`);
      return;
    }

    if (text === "/ideate5" || text === "/idea5" || text === "/sinh5") {
      await triggerGitHubIdeationWorkflow(env, { mode: "batch", count: 5 });
      await sendTelegramMessage(botToken, chatId, `💡 <b>[Kích Hoạt Sinh 5 Ý Tưởng]</b>\n\n🚀 Đã dispatch workflow GitHub Actions sinh 5 batch mới.`);
      return;
    }

    if (text.startsWith("/render")) {
      const parts = text.split(/\s+/);
      const rowId = parts.length > 1 ? parts[1] : "";
      await triggerGitHubRenderWorkflow(env, { row_id: rowId });
      await sendTelegramMessage(botToken, chatId, `🎬 <b>[Kích Hoạt Render]</b>\n\n🚀 Đã dispatch workflow GitHub Actions render video ${rowId ? '#' + rowId : 'toàn bộ Pending'}.`);
      return;
    }

    if (text === "/renderall") {
      await triggerGitHubRenderWorkflow(env, { row_id: "" });
      await sendTelegramMessage(botToken, chatId, `🎬 <b>[Kích Hoạt Render Toàn Bộ]</b>\n\n🚀 Đã dispatch workflow GitHub Actions render tất cả dòng Pending.`);
      return;
    }

    if (text.startsWith("/qc") || text === "/qcall") {
      const parts = text.split(/\s+/);
      const rowId = parts.length > 1 && text.startsWith("/qc ") ? parts[1] : "";
      await triggerGitHubQCWorkflow(env, { row_id: rowId });
      await sendTelegramMessage(botToken, chatId, `🛡️ <b>[Kích Hoạt Auto-QC]</b>\n\n🚀 Đã dispatch workflow GitHub Actions kiểm duyệt video ${rowId ? '#' + rowId : ''}.`);
      return;
    }

    if (text === "/status") {
      await sendTelegramMessage(
        botToken,
        chatId,
        `📊 <b>[Trạng Thái Pipeline: ${config.sheetTabName || "vocabCN"}]</b>\n\n` +
        `• <b>Spreadsheet:</b> <code>${config.spreadsheetId}</code>\n` +
        `• <b>Tab:</b> <code>${config.sheetTabName}</code>\n` +
        `• <b>Edge Gateway:</b> <code>Online (<2ms CPU)</code>\n` +
        `• <b>GitHub Repo:</b> <code>${config.githubRepoOwner}/${config.githubRepoName}</code>`
      );
      return;
    }
  }
}

/**
 * Build help menu message
 */
export function getHelpMessage(tabName = "vocabCN") {
  return `🤖 <b>HỆ THỐNG ĐIỀU KHIỂN & KIỂM DUYỆT TỰ ĐỘNG - LÊ LÊ HỌC TIẾNG TRUNG</b>
<i>(Cloudflare Edge Gateway - Tab: ${tabName})</i>

💡 <b>DANH SÁCH LỆNH ĐIỀU KHIỂN:</b>
━━━━━━━━━━━━━━━━━━━━━
🔹 <code>/ideate</code>: Tạo 1 bộ ý tưởng mới qua GitHub Actions.
🔹 <code>/ideate5</code> (hoặc <code>/sinh5</code>): Tạo 5 bộ ý tưởng mới.
🔹 <code>/render [id]</code>: Render video dòng cụ thể (hoặc tất cả Pending).
🔹 <code>/renderall</code>: Render toàn bộ các dòng Pending.
🔹 <code>/qc [id]</code>: Auto-QC kiểm tra chất lượng video.
🔹 <code>/status</code>: Thông tin kết nối & trạng thái pipeline.
🔹 <code>/myid</code>: Xem Chat ID Telegram.
🔹 <code>/help</code>: Xem lại hướng dẫn này.
━━━━━━━━━━━━━━━━━━━━━`;
}
