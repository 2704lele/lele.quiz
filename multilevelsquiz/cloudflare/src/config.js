/**
 * Configuration manager for MultilevelsQuiz Cloudflare Worker
 */

export function parseKeyList(val) {
  if (!val) return [];
  if (Array.isArray(val)) return val.map(k => String(k).trim()).filter(Boolean);
  return String(val)
    .split(/[\n,]+/)
    .map(k => k.trim())
    .filter(Boolean);
}

export function getConfig(env) {
  return {
    spreadsheetId: env.SPREADSHEET_ID || "1b6LNl7JHRiCsjK1w9VuD86GLqAfmSOtDUOm5whrGdH0",
    sheetTabName: env.SHEET_TAB_NAME || "multilevels",

    // Account & AI Gateway
    accountId: env.ACCOUNT_ID || "3591f5b61af3263ca14af7a1765cc954",
    aiGatewayName: env.AI_GATEWAY_NAME || "lelemultilevelsquiz",

    // Service Account Credentials
    gcpClientEmail: env.GCP_SERVICE_ACCOUNT_EMAIL || "",
    gcpPrivateKey: (env.GCP_SERVICE_ACCOUNT_PRIVATE_KEY || "").replace(/\\n/g, "\n"),

    // Telegram
    telegramBotToken: env.TELEGRAM_BOT_TOKEN || "",
    telegramChatId: env.TELEGRAM_CHAT_ID || "1187577977",
    telegramWebhookSecret: env.TELEGRAM_WEBHOOK_SECRET || "",

    // GitHub Actions
    githubRepoOwner: env.GITHUB_REPO_OWNER || "naadld",
    githubRepoName: env.GITHUB_REPO_NAME || "lele2vid",
    githubWorkflowFile: env.GITHUB_WORKFLOW_FILE || "multilevels_render.yml",
    githubIdeationWorkflow: env.GITHUB_IDEATION_WORKFLOW_FILE || env.GITHUB_IDEATION_WORKFLOW || "multilevels_ideation.yml",
    githubQcWorkflow: env.GITHUB_QC_WORKFLOW_FILE || env.GITHUB_QC_WORKFLOW || "multilevels_qc.yml",
    githubToken: env.GITHUB_TOKEN || "",
    cfWebhookUrl: env.CF_WEBHOOK_URL || "https://lele-multilevelsquiz.hothihuong113.workers.dev/api/receive-ideas",

    // AI Providers & Models
    geminiApiKeys: parseKeyList(env.GEMINI_API_KEYS || env.GEMINI_API_KEY),
    geminiModel: env.GEMINI_MODEL || "gemini-3.7-flash",
    aiModel: env.AI_MODEL || "@cf/meta/llama-3.3-70b-instruct"
  };
}
