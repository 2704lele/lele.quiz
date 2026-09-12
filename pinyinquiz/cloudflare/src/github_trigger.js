/**
 * GitHub Actions Workflow Dispatch Client for PinyinQuiz Pipeline
 * Triggers repository workflows directly from Cloudflare Worker with Zero-Secret dynamic parameters.
 */

/**
 * Trigger Ideation Workflow (ScriptNewIdeation.yml)
 */
export async function triggerGitHubIdeationWorkflow(env, options = {}) {
  const owner = env.GITHUB_REPO_OWNER || "naadld";
  const repo = env.GITHUB_REPO_NAME || "lele2vid";
  const workflow = env.GITHUB_IDEATION_WORKFLOW_FILE || env.GITHUB_IDEATION_WORKFLOW || "ScriptNewIdeation.yml";
  const token = env.GITHUB_TOKEN;

  if (!token) {
    console.warn("[GITHUB-TRIGGER] GITHUB_TOKEN is missing in environment variables.");
    return { success: false, error: "GITHUB_TOKEN is missing." };
  }

  const webhookUrl = options.cf_webhook_url || env.CF_WEBHOOK_URL || "https://lele-pinyinquiz.hothihuong113.workers.dev/api/receive-ideas";
  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;

  const payload = {
    ref: options.ref || "main",
    inputs: {
      mode: options.mode || "batch",
      count: String(options.count || "5"),
      level: String(options.level || ""),
      row_id: String(options.row_id || ""),
      rejected_topic: String(options.rejected_topic || ""),
      error_reasons: String(options.error_reasons || ""),
      cf_webhook_url: webhookUrl
    }
  };

  console.log(`[GITHUB-TRIGGER] Dispatching '${workflow}' (mode: ${payload.inputs.mode}, row_id: '${payload.inputs.row_id}') to ${owner}/${repo}`);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "Cloudflare-Worker-LeLeQuiz",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (response.status === 204) {
      return { success: true, message: `Dispatched ${workflow} successfully on ${owner}/${repo}` };
    }

    const errBody = await response.text();
    console.error(`[GITHUB-TRIGGER] GitHub API Error (${response.status}): ${errBody}`);
    return { success: false, status: response.status, error: errBody };
  } catch (err) {
    console.error(`[GITHUB-TRIGGER] Fetch error:`, err);
    return { success: false, error: err.message };
  }
}

/**
 * Trigger Video Render Workflow (Render.yml)
 */
export async function triggerGitHubRenderWorkflow(env, options = {}) {
  const owner = env.GITHUB_REPO_OWNER || "naadld";
  const repo = env.GITHUB_REPO_NAME || "lele2vid";
  const workflow = env.GITHUB_WORKFLOW_FILE || "Render.yml";
  const token = env.GITHUB_TOKEN;

  if (!token) {
    console.warn("[GITHUB-TRIGGER] GITHUB_TOKEN is missing in environment variables.");
    return { success: false, error: "GITHUB_TOKEN is missing." };
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;
  const payload = {
    ref: options.ref || "main",
    inputs: {
      quality: options.quality || "qh",
      row_id: String(options.row_id || "")
    }
  };

  console.log(`[GITHUB-TRIGGER] Dispatching '${workflow}' (row_id: '${payload.inputs.row_id}') to ${owner}/${repo}`);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "Cloudflare-Worker-LeLeQuiz",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (response.status === 204) {
      return { success: true, message: `Dispatched ${workflow} successfully on ${owner}/${repo}` };
    }

    const errBody = await response.text();
    console.error(`[GITHUB-TRIGGER] GitHub API Error (${response.status}): ${errBody}`);
    return { success: false, status: response.status, error: errBody };
  } catch (err) {
    console.error(`[GITHUB-TRIGGER] Fetch error:`, err);
    return { success: false, error: err.message };
  }
}

/**
 * Trigger Auto-QC Physical Video Inspection Workflow (ProductQC.yml)
 */
export async function triggerGitHubQCWorkflow(env, options = {}) {
  const owner = env.GITHUB_REPO_OWNER || "naadld";
  const repo = env.GITHUB_REPO_NAME || "lele2vid";
  const workflow = env.GITHUB_QC_WORKFLOW_FILE || env.GITHUB_QC_WORKFLOW || "ProductQC.yml";
  const token = env.GITHUB_TOKEN;

  if (!token) {
    console.warn("[GITHUB-TRIGGER] GITHUB_TOKEN is missing in environment variables.");
    return { success: false, error: "GITHUB_TOKEN is missing." };
  }

  const url = `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflow}/dispatches`;
  const payload = {
    ref: options.ref || "main",
    inputs: {
      row_id: String(options.row_id || "")
    }
  };

  console.log(`[GITHUB-TRIGGER] Dispatching '${workflow}' (row_id: '${payload.inputs.row_id}') to ${owner}/${repo}`);

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${token}`,
        "Accept": "application/vnd.github+json",
        "User-Agent": "Cloudflare-Worker-LeLeQuiz",
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    if (response.status === 204) {
      return { success: true, message: `Dispatched ${workflow} successfully on ${owner}/${repo}` };
    }

    const errBody = await response.text();
    console.error(`[GITHUB-TRIGGER] GitHub API Error (${response.status}): ${errBody}`);
    return { success: false, status: response.status, error: errBody };
  } catch (err) {
    console.error(`[GITHUB-TRIGGER] Fetch error:`, err);
    return { success: false, error: err.message };
  }
}
