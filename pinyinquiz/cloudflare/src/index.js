/**
 * LeLe Chinese Quiz - Ultra-Lightweight Edge Gateway & Router (Pinyin Quiz)
 * Execution Budget: < 2ms CPU | Zero Heavy Compute | HTTP 202 Async Dispatch
 */

import { getConfig } from "./config.js";
import { triggerGitHubIdeationWorkflow, triggerGitHubRenderWorkflow, triggerGitHubQCWorkflow } from "./github_trigger.js";
import { sendTelegramMessage, handleTelegramUpdate } from "./telegram.js";

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Telegram-Bot-Api-Secret-Token",
  "Content-Type": "application/json"
};

const json = (data, status = 200) => new Response(JSON.stringify(data, null, 2), { status, headers: CORS });

export default {
  async fetch(req, env, ctx) {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });

    const url = new URL(req.url), method = req.method, config = getConfig(env);

    // 1. Health Check
    if (method === "GET" && url.pathname === "/") {
      return json({ project: "LeLe Pinyin Quiz Edge Router", pipeline: config.sheetTabName, status: "Online", architecture: "Ultra-Lightweight Async Dispatch (< 2ms)", timestamp: new Date().toISOString() });
    }

    // 2. Gatekeeper Ingestion Webhook (Immediate HTTP 202 Async Acceptance)
    if (url.pathname === "/api/receive-ideas") {
      if (method === "GET") return json({ endpoint: "/api/receive-ideas", method: "POST", pipeline: config.sheetTabName, status: "Online (HTTP 202 Async Dispatch)" });
      if (method === "POST") {
        try {
          const payload = await req.json();
          const rowId = String(payload.row_id || payload.batch_id || payload.id || "");
          ctx.waitUntil((async () => {
            console.log(`[EDGE-DISPATCH] Ingested idea tab=${config.sheetTabName} row_id=${rowId}`);
            if (payload.auto_render !== false && rowId) await triggerGitHubRenderWorkflow(env, { row_id: rowId, quality: payload.quality || "qh" });
          })());
          return json({ success: true, status: "Accepted", pipeline: config.sheetTabName, batch_id: rowId || null, dispatched: true, message: "Payload received and queued for asynchronous cloud execution.", timestamp: new Date().toISOString() }, 202);
        } catch (err) {
          return json({ success: false, error: err.message }, 400);
        }
      }
    }

    // Helper to extract workflow trigger parameters
    const getParams = async () => {
      let b = {};
      if (method === "POST") try { b = await req.json(); } catch (_) {}
      return {
        mode: b.mode || url.searchParams.get("mode") || "batch",
        count: b.count || url.searchParams.get("count") || "5",
        level: b.level || url.searchParams.get("level") || "",
        rowId: b.row_id || url.searchParams.get("row_id") || "",
        quality: b.quality || url.searchParams.get("quality") || "qh"
      };
    };

    // 3. Workflow Trigger Endpoints (Ideation, Render, QC)
    if (url.pathname === "/api/trigger-ideation" || url.pathname === "/api/ideate" || url.pathname === "/api/dispatch-ideation") {
      const p = await getParams();
      ctx.waitUntil(triggerGitHubIdeationWorkflow(env, { mode: p.mode, count: p.count, level: p.level, row_id: p.rowId }));
      return json({ success: true, action: "ideation_dispatched", mode: p.mode, count: p.count, level: p.level, row_id: p.rowId, timestamp: new Date().toISOString() }, 202);
    }

    if (url.pathname === "/api/trigger-render" || url.pathname === "/api/render") {
      const p = await getParams();
      ctx.waitUntil(triggerGitHubRenderWorkflow(env, { row_id: p.rowId, quality: p.quality }));
      return json({ success: true, action: "render_dispatched", row_id: p.rowId, quality: p.quality, timestamp: new Date().toISOString() }, 202);
    }

    if (url.pathname === "/api/trigger-qc" || url.pathname === "/api/qc") {
      const p = await getParams();
      ctx.waitUntil(triggerGitHubQCWorkflow(env, { row_id: p.rowId }));
      return json({ success: true, action: "qc_dispatched", row_id: p.rowId, timestamp: new Date().toISOString() }, 202);
    }

    // 4. Notification Relay (Telegram)
    if (url.pathname === "/api/notify" && method === "POST") {
      try {
        const body = await req.json();
        const tgRes = await sendTelegramMessage(config.telegramBotToken, body.chat_id || config.telegramChatId, body.text || body.message || "🔔 Thông báo", body.options || {});
        return json({ success: Boolean(tgRes && tgRes.ok), result: tgRes });
      } catch (err) {
        return json({ success: false, error: err.message }, 500);
      }
    }

    // 5. Telegram Webhook Handler (Ultra-Fast Non-Blocking Response)
    if (url.pathname === "/webhook" && method === "POST") {
      if (config.telegramWebhookSecret && req.headers.get("X-Telegram-Bot-Api-Secret-Token") !== config.telegramWebhookSecret) {
        return new Response("Unauthorized", { status: 401 });
      }
      try {
        const update = await req.json();
        ctx.waitUntil(handleTelegramUpdate(update, env, config));
        return new Response("OK", { status: 200 });
      } catch (err) {
        return json({ error: err.message }, 400);
      }
    }

    return json({ error: "Not Found", path: url.pathname }, 404);
  },

  /**
   * Cron Trigger Event Handler (Asynchronous Scheduled Dispatches)
   */
  async scheduled(event, env, ctx) {
    const config = getConfig(env);
    console.log(`[CRON] Event fired at ${new Date().toISOString()} (Cron: ${event.cron})`);
    ctx.waitUntil((async () => {
      try {
        if (event.cron === "1 17 * * 1" || event.cron === "1 17 * * *") {
          console.log("[CRON] Dispatching weekly ideation batch...");
          await triggerGitHubIdeationWorkflow(env, { mode: "batch", count: 5 });
          if (config.telegramBotToken && config.telegramChatId) {
            await sendTelegramMessage(config.telegramBotToken, config.telegramChatId, `🏭 <b>[Lịch Tự Động Hằng Tuần]</b>\n\n🚀 Đã kích hoạt GitHub Actions sinh 5 kịch bản mới cho pipeline <code>${config.sheetTabName}</code>.`);
          }
        }
      } catch (err) {
        console.error("[CRON] Dispatch error:", err);
      }
    })());
  }
};
