/**
 * LeLe Chinese Quiz - Cloudflare Exclusive Cron Scheduler & Edge Dispatcher
 * Controls 3 Daily Production Milestones:
 * 1. 00:01 AM GMT+7 (17:01 UTC): Ideation & Scripting (20 rows: 5 rows x 4 tabs)
 * 2. 03:01 AM GMT+7 (20:01 UTC): Cloud Video Rendering & Gatekeeper 2 QC
 * 3. 05:01 AM GMT+7 (22:01 UTC): Morning Gatekeeper Audit & Telegram Briefing
 */

const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
  "Content-Type": "application/json"
};

const json = (data, status = 200) => new Response(JSON.stringify(data, null, 2), { status, headers: CORS });

async function sendTelegram(botToken, chatId, text) {
  if (!botToken || !chatId) return;
  try {
    const url = `https://api.telegram.org/bot${botToken}/sendMessage`;
    await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        chat_id: chatId,
        text: text,
        parse_mode: "HTML",
        disable_web_page_preview: true
      })
    });
  } catch (err) {
    console.error("[TELEGRAM] Error:", err);
  }
}

async function dispatchWorkflow(env, workflowFile, inputs = {}) {
  const owner = env.GITHUB_REPO_OWNER || "nwtuanhoang-coder";
  const repo = env.GITHUB_REPO_NAME || "lele-quiz-automation";
  const token = env.GITHUB_TOKEN;

  if (!token) {
    console.error("[GHA] GITHUB_TOKEN is not configured in worker environment.");
    return { success: false, error: "GITHUB_TOKEN missing" };
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowFile}/dispatches`;
  const res = await fetch(url, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Accept": "application/vnd.github+json",
      "User-Agent": "Cloudflare-Worker-QuizScheduler",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ ref: "main", inputs })
  });

  if (res.status === 204) {
    return { success: true, message: `Dispatched ${workflowFile} successfully.` };
  } else {
    const errText = await res.text();
    console.error(`[GHA] Error ${res.status}:`, errText);
    return { success: false, status: res.status, error: errText };
  }
}

export default {
  async fetch(req, env, ctx) {
    if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: CORS });
    const url = new URL(req.url);

    if (url.pathname === "/" || url.pathname === "/health") {
      return json({
        service: "LeLe Chinese Quiz Exclusive Cloudflare Cron Scheduler",
        status: "Online",
        repository: `${env.GITHUB_REPO_OWNER || "nwtuanhoang-coder"}/${env.GITHUB_REPO_NAME || "lele-quiz-automation"}`,
        milestones: {
          ideation: "00:01 AM GMT+7 (17:01 UTC) -> 01_quiz_ideation_and_scripting.yml",
          rendering: "03:01 AM GMT+7 (20:01 UTC) -> 02_quiz_video_rendering_and_qc.yml",
          morning_audit: "05:01 AM GMT+7 (22:01 UTC) -> 03_quiz_morning_audit.yml"
        },
        timestamp: new Date().toISOString()
      });
    }

    // Manual test dispatch endpoint
    if (url.pathname === "/api/trigger" && req.method === "POST") {
      const payload = await req.json().catch(() => ({}));
      const type = payload.type || url.searchParams.get("type");

      if (type === "ideation") {
        const r = await dispatchWorkflow(env, "01_quiz_ideation_and_scripting.yml", { tab: payload.tab || "all", batch_count: String(payload.count || "5") });
        return json(r);
      } else if (type === "render") {
        const r = await dispatchWorkflow(env, "02_quiz_video_rendering_and_qc.yml", { tab: payload.tab || "all", mode: "all_pending", quality: "qh" });
        return json(r);
      } else if (type === "audit") {
        const r = await dispatchWorkflow(env, "03_quiz_morning_audit.yml");
        return json(r);
      } else if (type === "social") {
        const r = await dispatchWorkflow(env, "04_quiz_social_distribution.yml", { tab: payload.tab || "all", channels: "buffer1", delay_minutes: "30" });
        return json(r);
      }
      return json({ error: "Invalid type. Options: ideation, render, audit, social" }, 400);
    }

    return json({ error: "Not Found" }, 404);
  },

  async scheduled(event, env, ctx) {
    console.log(`[CRON] Fired trigger: ${event.cron} at ${new Date().toISOString()}`);
    const botToken = env.TELEGRAM_BOT_TOKEN;
    const chatId = env.TELEGRAM_CHAT_ID || "1187577977";

    ctx.waitUntil((async () => {
      // 1. Milestone 00:01 AM GMT+7 (17:01 UTC) -> Ideation (20 rows)
      if (event.cron === "1 17 * * *") {
        console.log("[CRON] Executing Milestone 1: Ideation (00:01 AM GMT+7)...");
        await dispatchWorkflow(env, "01_quiz_ideation_and_scripting.yml", { tab: "all", batch_count: "5" });
        await sendTelegram(
          botToken,
          chatId,
          "🌙 <b>[Cloudflare Cron • 00:01 AM GMT+7]</b>\n\n💡 Đã kích hoạt GitHub Actions sinh <b>20 kịch bản mới</b> (5 dòng x 4 tabs) qua Multi-Provider AI Rotator (6 Gemini + 4 Agnes keys)."
        );
      }

      // 2. Milestone 03:01 AM GMT+7 (20:01 UTC) -> Cloud Video Rendering (All Pending)
      else if (event.cron === "1 20 * * *") {
        console.log("[CRON] Executing Milestone 2: Cloud Video Rendering (03:01 AM GMT+7)...");
        await dispatchWorkflow(env, "02_quiz_video_rendering_and_qc.yml", { tab: "all", mode: "all_pending", quality: "qh" });
        await sendTelegram(
          botToken,
          chatId,
          "⚙ <b>[Cloudflare Cron • 03:01 AM GMT+7]</b>\n\n🎬 Đã kích hoạt GitHub Actions render <b>toàn bộ video Pending</b> qua Manim 60fps trên đám mây."
        );
      }

      // 3. Milestone 05:01 AM GMT+7 (22:01 UTC) -> Morning Audit & Reconciliation
      else if (event.cron === "1 22 * * *") {
        console.log("[CRON] Executing Milestone 3: Morning Gatekeeper Audit (05:01 AM GMT+7)...");
        await dispatchWorkflow(env, "03_quiz_morning_audit.yml");
        await sendTelegram(
          botToken,
          chatId,
          "🌅 <b>[Cloudflare Cron • 05:01 AM GMT+7]</b>\n\n🔍 Đang thực hiện kiểm toán đối soát toàn bộ video Ready, kiểm tra HTTP 200 Drive và khoá cứng 21px..."
        );
      }
    })());
  }
};
