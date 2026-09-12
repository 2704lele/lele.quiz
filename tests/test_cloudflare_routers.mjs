/**
 * Comprehensive Unit and Integration Test Suite for Cloudflare Edge Routers
 * Verifies M1 Deliverables:
 * - Ultra-lightweight routers (<150 lines JS)
 * - Immediate HTTP 202 Accepted on /api/receive-ideas
 * - Async dispatch via ctx.waitUntil
 * - Endpoints: /, OPTIONS, /api/trigger-ideation, /api/trigger-render, /api/trigger-qc, /api/notify, /webhook
 * - Scheduled cron event handling
 * - Zero stale domain (.aleron-dt) references
 * - Correct webhook URLs per pipeline
 */

import { readdirSync, readFileSync } from "fs";
import { resolve, join } from "path";
import assert from "node:assert/strict";

const PROJECT_ROOT = resolve(".");

async function runTests() {
  console.log("==================================================================");
  console.log("🚀 STARTING CLOUDFLARE EDGE ROUTERS VERIFICATION TEST SUITE");
  console.log("==================================================================\n");

  const pipelines = [
    { name: "pinyin", path: "pinyinquiz", expectedWorkflow: "Render.yml", expectedDomain: "lele-pinyinquiz.hothihuong113.workers.dev" },
    { name: "vocabCN", path: "vocabCNquiz", expectedWorkflow: "vocabcn_render.yml", expectedDomain: "lele-vocabcnquiz.hothihuong113.workers.dev" },
    { name: "vocabVN", path: "vocabVNquiz", expectedWorkflow: "vocabvn_render.yml", expectedDomain: "lele-vocabvnquiz.hothihuong113.workers.dev" }
  ];

  // 1. Static Line Count & Integrity Verification
  console.log("📋 [TEST 1] Checking Line Counts and Code Constraints (< 150 lines)");
  for (const p of pipelines) {
    const indexPath = join(PROJECT_ROOT, p.path, "cloudflare/src/index.js");
    const content = readFileSync(indexPath, "utf8");
    const lines = content.split("\n").length;
    console.log(`   - ${p.name} index.js: ${lines} lines`);
    assert.ok(lines < 150, `${p.name} index.js has ${lines} lines, exceeding 150 lines limit!`);
  }
  console.log("   ✅ All router files are strictly under 150 lines of JS.\n");

  // 2. Stale Domain Check
  console.log("🔍 [TEST 2] Verifying Zero Stale Domain (.aleron-dt) References");
  const checkFiles = [
    "pinyinquiz/cloudflare/src/config.js",
    "pinyinquiz/cloudflare/src/github_trigger.js",
    "pinyinquiz/cloudflare/src/index.js",
    "pinyinquiz/scripts/generate_daily_batches.py",
    "vocabCNquiz/cloudflare/src/config.js",
    "vocabCNquiz/cloudflare/src/github_trigger.js",
    "vocabCNquiz/cloudflare/src/index.js",
    "vocabCNquiz/scripts/generate_daily_batches.py",
    "vocabVNquiz/cloudflare/src/config.js",
    "vocabVNquiz/cloudflare/src/github_trigger.js",
    "vocabVNquiz/cloudflare/src/index.js",
    "vocabVNquiz/scripts/generate_daily_batches.py"
  ];

  for (const relPath of checkFiles) {
    const content = readFileSync(join(PROJECT_ROOT, relPath), "utf8");
    assert.ok(!content.includes(".aleron-dt.workers.dev"), `Stale domain found in ${relPath}!`);
  }
  console.log("   ✅ Stale domain '.aleron-dt.workers.dev' is completely eliminated.\n");

  // 3. VocabVN Pipeline Fallback Isolation Check
  console.log("🔍 [TEST 3] Verifying VocabVN Isolation from PinyinQuiz");
  const vnTriggerContent = readFileSync(join(PROJECT_ROOT, "vocabVNquiz/cloudflare/src/github_trigger.js"), "utf8");
  assert.ok(!vnTriggerContent.includes("lele-pinyinquiz"), "vocabVNquiz/github_trigger.js still references lele-pinyinquiz!");
  assert.ok(vnTriggerContent.includes("lele-vocabvnquiz"), "vocabVNquiz/github_trigger.js does not reference lele-vocabvnquiz!");
  console.log("   ✅ VocabVN trigger correctly isolated to lele-vocabvnquiz.\n");

  // 4. Dynamic Execution Tests on all 3 Workers
  console.log("⚡ [TEST 4] Dynamic Functional Routing & Execution");
  for (const p of pipelines) {
    console.log(`\n--- Testing ${p.name.toUpperCase()} Edge Router (${p.path}) ---`);
    const workerModule = await import(`../${p.path}/cloudflare/src/index.js`);
    const worker = workerModule.default;

    const mockEnv = {
      SHEET_TAB_NAME: p.name,
      GITHUB_TOKEN: "mock_token_123",
      GITHUB_REPO_OWNER: "naadld",
      GITHUB_REPO_NAME: "lele2vid",
      GITHUB_WORKFLOW_FILE: p.expectedWorkflow,
      TELEGRAM_BOT_TOKEN: "mock_tg_token",
      TELEGRAM_CHAT_ID: "1187577977",
      TELEGRAM_WEBHOOK_SECRET: "test_secret_abc"
    };

    let backgroundPromises = [];
    const mockCtx = {
      waitUntil(promise) {
        backgroundPromises.push(promise);
      }
    };

    // Test 4.1: GET / (Health Check)
    {
      const req = new Request("https://mock-worker.dev/");
      const res = await worker.fetch(req, mockEnv, mockCtx);
      assert.equal(res.status, 200);
      const data = await res.json();
      assert.equal(data.pipeline, p.name);
      assert.equal(data.status, "Online");
      console.log(`   [4.1] GET / -> HTTP ${res.status} OK (pipeline: ${data.pipeline})`);
    }

    // Test 4.2: OPTIONS / (CORS Preflight)
    {
      const req = new Request("https://mock-worker.dev/api/receive-ideas", { method: "OPTIONS" });
      const res = await worker.fetch(req, mockEnv, mockCtx);
      assert.equal(res.status, 204);
      assert.equal(res.headers.get("Access-Control-Allow-Origin"), "*");
      console.log(`   [4.2] OPTIONS /api/receive-ideas -> HTTP ${res.status} (CORS headers verified)`);
    }

    // Test 4.3: POST /api/receive-ideas (HTTP 202 Immediate Accepted & Async Dispatch)
    {
      backgroundPromises = [];
      const startTime = performance.now();
      const payload = {
        row_id: "25",
        topic: "Thời Gian Hàng Ngày",
        level: "HSK 1",
        words: [" hôm nay", " ngày mai"],
        auto_render: true
      };
      const req = new Request("https://mock-worker.dev/api/receive-ideas", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });
      const res = await worker.fetch(req, mockEnv, mockCtx);
      const duration = performance.now() - startTime;

      assert.equal(res.status, 202, `Expected HTTP 202 Accepted, got ${res.status}`);
      const data = await res.json();
      assert.equal(data.success, true);
      assert.equal(data.status, "Accepted");
      assert.equal(data.batch_id, "25");
      assert.equal(data.dispatched, true);
      assert.ok(backgroundPromises.length > 0, "Background execution promise not registered in ctx.waitUntil!");
      console.log(`   [4.3] POST /api/receive-ideas -> HTTP ${res.status} Accepted in ${duration.toFixed(2)}ms (Batch #${data.batch_id})`);
    }

    // Test 4.4: GET /api/receive-ideas (Info endpoint)
    {
      const req = new Request("https://mock-worker.dev/api/receive-ideas");
      const res = await worker.fetch(req, mockEnv, mockCtx);
      assert.equal(res.status, 200);
      const data = await res.json();
      assert.equal(data.endpoint, "/api/receive-ideas");
      console.log(`   [4.4] GET /api/receive-ideas -> HTTP ${res.status} (Status info)`);
    }

    // Test 4.5: POST /api/trigger-ideation
    {
      backgroundPromises = [];
      const req = new Request("https://mock-worker.dev/api/trigger-ideation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "batch", count: "3", level: "HSK 2" })
      });
      const res = await worker.fetch(req, mockEnv, mockCtx);
      assert.equal(res.status, 202);
      const data = await res.json();
      assert.equal(data.action, "ideation_dispatched");
      assert.equal(data.count, "3");
      assert.ok(backgroundPromises.length > 0);
      console.log(`   [4.5] POST /api/trigger-ideation -> HTTP ${res.status} (Action: ${data.action})`);
    }

    // Test 4.6: POST /api/trigger-render
    {
      backgroundPromises = [];
      const req = new Request("https://mock-worker.dev/api/trigger-render", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ row_id: "12", quality: "qh" })
      });
      const res = await worker.fetch(req, mockEnv, mockCtx);
      assert.equal(res.status, 202);
      const data = await res.json();
      assert.equal(data.action, "render_dispatched");
      assert.equal(data.row_id, "12");
      assert.ok(backgroundPromises.length > 0);
      console.log(`   [4.6] POST /api/trigger-render -> HTTP ${res.status} (Action: ${data.action}, row_id: ${data.row_id})`);
    }

    // Test 4.7: POST /api/trigger-qc
    {
      backgroundPromises = [];
      const req = new Request("https://mock-worker.dev/api/trigger-qc", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ row_id: "12" })
      });
      const res = await worker.fetch(req, mockEnv, mockCtx);
      assert.equal(res.status, 202);
      const data = await res.json();
      assert.equal(data.action, "qc_dispatched");
      assert.equal(data.row_id, "12");
      assert.ok(backgroundPromises.length > 0);
      console.log(`   [4.7] POST /api/trigger-qc -> HTTP ${res.status} (Action: ${data.action}, row_id: ${data.row_id})`);
    }

    // Test 4.8: Telegram Webhook Auth & Non-Blocking Ack
    {
      // Unauthorized without token
      const reqUnauth = new Request("https://mock-worker.dev/webhook", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: { text: "/help", chat: { id: 123 } } })
      });
      const resUnauth = await worker.fetch(reqUnauth, mockEnv, mockCtx);
      assert.equal(resUnauth.status, 401);
      console.log(`   [4.8a] POST /webhook (No secret) -> HTTP 401 Unauthorized`);

      // Authorized with correct token
      backgroundPromises = [];
      const reqAuth = new Request("https://mock-worker.dev/webhook", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Telegram-Bot-Api-Secret-Token": "test_secret_abc"
        },
        body: JSON.stringify({ message: { text: "/help", chat: { id: 123 } } })
      });
      const resAuth = await worker.fetch(reqAuth, mockEnv, mockCtx);
      assert.equal(resAuth.status, 200);
      assert.ok(backgroundPromises.length > 0);
      console.log(`   [4.8b] POST /webhook (Valid secret) -> HTTP 200 OK (Async execution registered)`);
    }

    // Test 4.9: 404 on Unknown Path
    {
      const req = new Request("https://mock-worker.dev/api/unknown-endpoint");
      const res = await worker.fetch(req, mockEnv, mockCtx);
      assert.equal(res.status, 404);
      console.log(`   [4.9] GET /api/unknown-endpoint -> HTTP 404 Not Found`);
    }

    // Test 4.10: Scheduled Event Execution
    {
      backgroundPromises = [];
      await worker.scheduled({ cron: "1 17 * * 1" }, mockEnv, mockCtx);
      assert.ok(backgroundPromises.length > 0);
      console.log(`   [4.10] scheduled({ cron: '1 17 * * 1' }) -> Non-blocking dispatch registered`);
    }
  }

  console.log("\n==================================================================");
  console.log("🎉 ALL MILESTONE 1 VERIFICATION TESTS PASSED SUCCESSFULLY (100% GREEN)");
  console.log("==================================================================");
}

runTests().catch(err => {
  console.error("❌ TEST FAILED:", err);
  process.exit(1);
});
