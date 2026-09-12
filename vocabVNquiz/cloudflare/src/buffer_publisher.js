/**
 * Buffer GraphQL API Client for Multi-Platform Social Video Publishing
 * Official Endpoint: https://api.buffer.com
 */

import { generateSocialMetadata, getBatchMetadata } from "./metadata_helper.js";
import { getVietnamTimestamp } from "./google_sheets.js";

const BUFFER_GRAPHQL_ENDPOINT = "https://api.buffer.com";

/**
 * Convert standard Google Drive view link to direct streaming MP4 download links
 * Returns array of viable direct download / streaming URLs
 */
export function getGDriveDirectUrls(gdriveUrl) {
  if (!gdriveUrl || typeof gdriveUrl !== "string") return [];

  const match = gdriveUrl.match(/\/d\/([a-zA-Z0-9_-]+)/) || gdriveUrl.match(/id=([a-zA-Z0-9_-]+)/);
  if (match && match[1]) {
    const fileId = match[1];
    return [
      `https://drive.usercontent.google.com/download?id=${fileId}&export=download&authuser=0`,
      `https://lh3.googleusercontent.com/d/${fileId}`,
      `https://drive.google.com/uc?export=download&id=${fileId}`
    ];
  }
  return [gdriveUrl];
}

export function convertGDriveToDirectUrl(gdriveUrl) {
  const urls = getGDriveDirectUrls(gdriveUrl);
  return urls.length > 0 ? urls[0] : (gdriveUrl || "");
}

/**
 * Fetch all connected channels using Buffer GraphQL API
 */
export async function getBufferChannels(token, organizationId = "") {
  if (!token) {
    throw new Error("BUFFER_ACCESS_TOKEN is missing.");
  }

  // 1. Get Organization ID if not provided
  let orgId = organizationId;
  if (!orgId) {
    const orgQuery = `query { account { organizations { id name } } }`;
    const orgRes = await fetch(BUFFER_GRAPHQL_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ query: orgQuery })
    });
    const orgData = await orgRes.json();
    orgId = orgData.data?.account?.organizations?.[0]?.id;
  }

  if (!orgId) {
    throw new Error("Could not find Buffer Organization ID for this token.");
  }

  // 2. Query channels for this organization
  const channelsQuery = `
    query GetChannels($input: ChannelsInput!) {
      channels(input: $input) {
        id
        name
        service
        type
      }
    }
  `;

  const channelsRes = await fetch(BUFFER_GRAPHQL_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({
      query: channelsQuery,
      variables: { input: { organizationId: orgId } }
    })
  });

  const channelsData = await channelsRes.json();
  if (channelsData.errors) {
    throw new Error(`Buffer GraphQL Channels Error: ${JSON.stringify(channelsData.errors)}`);
  }

  return channelsData.data?.channels || [];
}

/**
 * Get Buffer Quota and Health stats from GraphQL API and Response Headers
 */
export async function getBufferQuotaAndHealth(token) {
  if (!token) {
    return { error: "BUFFER_ACCESS_TOKEN is missing" };
  }

  const query = `
    query {
      account {
        id
        email
        organizations {
          id
          name
        }
      }
    }
  `;

  try {
    const res = await fetch(BUFFER_GRAPHQL_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ query })
    });

    const data = await res.json();
    const orgId = data.data?.account?.organizations?.[0]?.id;
    const email = data.data?.account?.email || "";

    // Parse rate limit headers
    const limitHeader = parseInt(res.headers.get("x-ratelimit-limit") || "3000", 10);
    const remainingHeader = parseInt(res.headers.get("x-ratelimit-remaining") || "3000", 10);
    const resetHeader = res.headers.get("x-ratelimit-reset");
    const used = Math.max(0, limitHeader - remainingHeader);
    const percent = Math.round((remainingHeader / limitHeader) * 100);

    let daysRemaining = null;
    let resetDateStr = "";
    let resetTimeFormatted = "";

    if (resetHeader) {
      const resetTs = parseInt(resetHeader, 10);
      if (!isNaN(resetTs) && resetTs > 0) {
        const nowSec = Math.floor(Date.now() / 1000);
        const diffSec = Math.max(0, resetTs - nowSec);
        const rawDays = diffSec / 86400;
        daysRemaining = Number(rawDays.toFixed(1));

        // Format GMT+7: HH:mm DD/MM
        const resetDateVN = new Date(resetTs * 1000 + (7 * 3600 * 1000));
        const hours = String(resetDateVN.getUTCHours()).padStart(2, "0");
        const mins = String(resetDateVN.getUTCMinutes()).padStart(2, "0");
        const day = String(resetDateVN.getUTCDate()).padStart(2, "0");
        const month = String(resetDateVN.getUTCMonth() + 1).padStart(2, "0");
        resetTimeFormatted = `${hours}:${mins} ${day}/${month}`;
        resetDateStr = resetDateVN.toISOString().replace("T", " ").substring(0, 19);
      }
    }

    if (daysRemaining === null) {
      daysRemaining = 28;
    }

    let channels = [];
    if (orgId) {
      channels = await getBufferChannels(token, orgId);
    }

    return {
      email,
      monthlyLimit: limitHeader,
      monthlyRemaining: remainingHeader,
      monthlyUsed: used,
      monthlyPercent: percent,
      daysRemaining,
      resetTimeFormatted,
      resetDateStr,
      channelsCount: channels.length,
      channels
    };
  } catch (err) {
    return {
      error: err.message,
      monthlyLimit: 3000,
      monthlyRemaining: 2960,
      monthlyUsed: 40,
      monthlyPercent: 98,
      daysRemaining: 28,
      resetTimeFormatted: "",
      resetDateStr: "",
      channelsCount: 3,
      channels: []
    };
  }
}

/**
 * Publish video to a specific Buffer channel using GraphQL createPost mutation
 */
export async function createBufferGraphQLPost(token, channelId, text, videoUrl = "", metadata = null) {
  const mutation = `
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            status
            channelId
          }
        }
        ... on MutationError {
          message
        }
      }
    }
  `;

  const inputPayload = {
    channelId: channelId,
    mode: "shareNow",
    schedulingType: "automatic",
    needsApproval: false,
    text: text
  };

  if (videoUrl) {
    inputPayload.assets = [
      {
        video: {
          url: videoUrl
        }
      }
    ];
  }

  if (metadata) {
    inputPayload.metadata = metadata;
  }

  const response = await fetch(BUFFER_GRAPHQL_ENDPOINT, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${token}`
    },
    body: JSON.stringify({
      query: mutation,
      variables: { input: inputPayload }
    })
  });

  const resData = await response.json();
  if (resData.errors && resData.errors.length > 0) {
    throw new Error(resData.errors.map(e => e.message).join(", "));
  }

  const createPostResult = resData.data?.createPost;
  if (createPostResult?.message) {
    throw new Error(createPostResult.message);
  }

  return createPostResult;
}

const INTER_PLATFORM_DELAY_MS = 30000; // 30 seconds delay between platforms

/**
 * Publish video with fallback URL rotation and automatic exponential retry
 */
export async function createBufferGraphQLPostWithRetry(token, channelId, text, videoUrls = [], metadata = null, maxRetries = 3) {
  const urlsToTry = Array.isArray(videoUrls) ? videoUrls : [videoUrls];
  let lastError = null;

  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const currentUrl = urlsToTry[attempt % urlsToTry.length] || "";
    try {
      const res = await createBufferGraphQLPost(token, channelId, text, currentUrl, metadata);
      return res;
    } catch (err) {
      lastError = err;
      console.warn(`Buffer Post attempt ${attempt + 1}/${maxRetries} failed for channel ${channelId} (URL: ${currentUrl.substring(0, 50)}...): ${err.message}`);
      if (attempt < maxRetries - 1) {
        // Wait 5s, 10s with backoff before retry to release Google Drive download concurrency locks
        await new Promise(r => setTimeout(r, 5000 * (attempt + 1)));
      }
    }
  }

  throw lastError || new Error("Failed to create Buffer post after retries.");
}

// ============================================================================
// GATEKEEPER ANTI-DUPLICATE PUBLISHING LOCK & LIVE BUFFER AUDITOR
// ============================================================================
const IN_FLIGHT_PUBLISH_LOCKS = new Map();
const PUBLISH_LOCK_TIMEOUT_MS = 120000; // 2 minutes mutex lock per batch

/**
 * Check if a channel column is already marked as published in Google Sheets
 */
export function isChannelPublished(val) {
  if (!val || typeof val !== "string") return false;
  const lower = val.trim().toLowerCase();
  return lower.startsWith("pub") || lower.startsWith("ok") || lower.startsWith("http");
}

/**
 * Fetch recent posts directly from Buffer GraphQL API to inspect live history
 */
export async function fetchRecentBufferPosts(token, organizationId) {
  const query = `
    query GetRecentPosts($input: PostsInput!) {
      posts(input: $input) {
        edges {
          node {
            id
            channelId
            channelService
            status
            text
            sentAt
            createdAt
          }
        }
      }
    }
  `;
  try {
    const res = await fetch(BUFFER_GRAPHQL_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token
      },
      body: JSON.stringify({
        query,
        variables: { input: { organizationId } }
      })
    });
    const data = await res.json();
    return data.data?.posts?.edges?.map(e => e.node) || [];
  } catch (err) {
    console.warn("[GATEKEEPER] Could not query Buffer recent posts:", err.message);
    return [];
  }
}

/**
 * Check if a similar post already exists on Buffer within maxAgeHours (default: 24 hours)
 */
export function isDuplicateOnBuffer(recentPosts, service, topic, maxAgeHours = 24) {
  if (!recentPosts || recentPosts.length === 0 || !topic) return null;
  const cleanTopic = topic.toLowerCase().replace(/hsk\s*\d+\s*[•·-]\s*/gi, "").trim();
  const now = Date.now();
  const maxAgeMs = maxAgeHours * 3600 * 1000;

  for (const p of recentPosts) {
    if (p.channelService && p.channelService.toLowerCase() === service.toLowerCase()) {
      const createdTs = new Date(p.createdAt || p.sentAt || 0).getTime();
      if (now - createdTs <= maxAgeMs) {
        const textLower = (p.text || "").toLowerCase();
        if (cleanTopic.length >= 3 && textLower.includes(cleanTopic)) {
          return p;
        }
      }
    }
  }
  return null;
}

/**
 * Publish single batch video to all 3 platforms with STRICT Multi-Tier Gatekeeper Protection:
 * - Tier 1: Sheet-Level Status Check (Rejects if already Published)
 * - Tier 2: In-Flight Concurrency Mutex Lock (Blocks concurrent / rapid repeat triggers)
 * - Tier 3: Live Buffer History Audit (Inspects Buffer API to prevent duplicate submissions within 24h)
 * 
 * @param {object} env Worker environment
 * @param {object} batch Batch object containing topic, level, words, videoUrl, youtube, tiktok, facebook
 * @returns {object} Publishing result with per-platform status and final status ('Published' or 'Error')
 */
export async function publishBatchToBuffer(env, batch) {
  const token = env.BUFFER_ACCESS_TOKEN;
  const orgId = env.BUFFER_ORGANIZATION_ID || "6a83dbc8ed2918dea599c57c";

  if (!token) {
    throw new Error("BUFFER_ACCESS_TOKEN is not configured.");
  }

  const batchId = String(batch.id || "").replace(/^#/, "").trim();
  const statusLower = String(batch.status || "").trim().toLowerCase();

  // =========================================================================
  // GATEKEEPER TIER 1: SHEET-LEVEL STATUS & INTEGRITY CHECK
  // =========================================================================
  const isSheetYtDone = isChannelPublished(batch.youtube);
  const isSheetTtDone = isChannelPublished(batch.tiktok);
  const isSheetFbDone = isChannelPublished(batch.facebook);

  if (statusLower === "published" || (isSheetYtDone && isSheetTtDone && isSheetFbDone)) {
    console.warn(`🛑 [GATEKEEPER 403 BLOCKED] Batch #${batchId} (${batch.topic}) is already marked as Published on Sheet. Refusing duplicate publish.`);
    return {
      batchId: batch.id,
      topic: batch.topic,
      finalStatus: "Published",
      skipped: true,
      gatekeeperBlocked: true,
      error: `🛑 [GATEKEEPER] Dòng #${batch.id} (${batch.topic}) đã hoàn tất đăng đủ cả 3 nền tảng. Hệ thống cấm triệt để việc kích hoạt đăng lại!`,
      youtubeStatus: batch.youtube,
      tiktokStatus: batch.tiktok,
      fbStatus: batch.facebook,
      isYtOk: true,
      isTtOk: true,
      isFbOk: true,
      fullyPublished: true
    };
  }

  // =========================================================================
  // GATEKEEPER TIER 2: IN-FLIGHT CONCURRENCY MUTEX LOCK
  // =========================================================================
  const now = Date.now();
  const lockKey = `publish_batch_${batchId}`;
  if (IN_FLIGHT_PUBLISH_LOCKS.has(lockKey)) {
    const lockTs = IN_FLIGHT_PUBLISH_LOCKS.get(lockKey);
    if (now - lockTs < PUBLISH_LOCK_TIMEOUT_MS) {
      console.warn(`🛑 [GATEKEEPER 429 BLOCKED] Batch #${batchId} has an active publishing lock (${Math.round((now - lockTs) / 1000)}s ago). Refusing concurrent trigger.`);
      return {
        batchId: batch.id,
        topic: batch.topic,
        finalStatus: batch.status,
        skipped: true,
        gatekeeperBlocked: true,
        error: `🛑 [GATEKEEPER MUTEX] Dòng #${batch.id} đang trong tiến trình xuất bản (In-Flight Lock). Vui lòng không kích hoạt liên tục nhiều lần!`,
        isYtOk: isSheetYtDone,
        isTtOk: isSheetTtDone,
        isFbOk: isSheetFbDone
      };
    }
  }

  // Acquire Mutex Lock
  IN_FLIGHT_PUBLISH_LOCKS.set(lockKey, now);

  try {
    // Predefined or auto-discovered channel mapping
    let channels = [];
    try {
      channels = await getBufferChannels(token, orgId);
    } catch (err) {
      console.warn("Could not auto-fetch channels, using standard IDs:", err);
    }

    if (channels.length === 0) {
      channels = [
        { id: "6a871331ccaf649a67e1b724", name: "Lê Lê học tiếng Trung", service: "facebook", type: "page" },
        { id: "6a83dc5bccaf649a67c8b30f", name: "lelehoctiengtrung", service: "tiktok", type: "account" },
        { id: "6a83dda0ccaf649a67c8cb92", name: "Lê Lê và Hán Ngữ", service: "youtube", type: "channel" }
      ];
    }

    // =========================================================================
    // GATEKEEPER TIER 3: LIVE BUFFER HISTORY AUDIT (24H ANTI-DUPLICATION)
    // =========================================================================
    const recentBufferPosts = await fetchRecentBufferPosts(token, orgId);
    console.log(`[GATEKEEPER] Auditing against ${recentBufferPosts.length} recent Buffer posts...`);

    const meta = getBatchMetadata(batch.metadata, batch.topic, batch.level, batch.words);
    const directVideoUrls = getGDriveDirectUrls(batch.videoUrl);
    const directVideoUrl = directVideoUrls[0] || "";
    const nowStr = getVietnamTimestamp();

    console.log(`[PUBLISHER] Processing Batch #${batch.id} (${batch.topic}) - Video: ${directVideoUrl ? "YES" : "NO"}...`);

    // Existing statuses
    let youtubeStatus = batch.youtube || "";
    let tiktokStatus = batch.tiktok || "";
    let fbStatus = batch.facebook || "";

    const results = [];
    const errors = [];

    for (let i = 0; i < channels.length; i++) {
      const ch = channels[i];
      const service = ch.service.toLowerCase();

      // 1. YouTube Shorts
      if (service === "youtube") {
        if (isChannelPublished(youtubeStatus)) {
          console.log(`[GATEKEEPER] YouTube channel already published for #${batch.id} on Sheet. Skipping.`);
          continue;
        }
        const existingOnBuffer = isDuplicateOnBuffer(recentBufferPosts, "youtube", batch.topic);
        if (existingOnBuffer) {
          console.warn(`🛑 [GATEKEEPER] YouTube post already exists on Buffer (ID: ${existingOnBuffer.id}) for '${batch.topic}'. Skipping mutation.`);
          youtubeStatus = `Published (Buffer ID: ${existingOnBuffer.id})`;
          results.push({ channel: "YouTube", status: "skipped_duplicate_on_buffer", postId: existingOnBuffer.id });
          continue;
        }

        try {
          const description = meta.youtube.description;
          const ytMetadata = {
            youtube: {
              title: meta.youtube.title,
              categoryId: "27", // Education category
              privacy: "public",
              madeForKids: false
            }
          };
          await createBufferGraphQLPostWithRetry(token, ch.id, description, directVideoUrls, ytMetadata);
          youtubeStatus = `Published (${nowStr})`;
          results.push({ channel: "YouTube", status: "success" });
        } catch (err) {
          console.error("YouTube Post Error:", err);
          youtubeStatus = `Error: ${err.message.substring(0, 60)}`;
          errors.push({ channel: "YouTube", error: err.message });
        }

        // Staggered delay to allow Buffer to process
        if (i < channels.length - 1) {
          await new Promise(resolve => setTimeout(resolve, INTER_PLATFORM_DELAY_MS));
        }
      }

      // 2. TikTok
      else if (service === "tiktok") {
        if (isChannelPublished(tiktokStatus)) {
          console.log(`[GATEKEEPER] TikTok channel already published for #${batch.id} on Sheet. Skipping.`);
          continue;
        }
        const existingOnBuffer = isDuplicateOnBuffer(recentBufferPosts, "tiktok", batch.topic);
        if (existingOnBuffer) {
          console.warn(`🛑 [GATEKEEPER] TikTok post already exists on Buffer (ID: ${existingOnBuffer.id}) for '${batch.topic}'. Skipping mutation.`);
          tiktokStatus = `Published (Buffer ID: ${existingOnBuffer.id})`;
          results.push({ channel: "TikTok", status: "skipped_duplicate_on_buffer", postId: existingOnBuffer.id });
          continue;
        }

        try {
          const caption = meta.tiktok.caption;
          const ttMetadata = {
            tiktok: {
              isAiGenerated: false
            }
          };
          await createBufferGraphQLPostWithRetry(token, ch.id, caption, directVideoUrls, ttMetadata);
          tiktokStatus = `Published (${nowStr})`;
          results.push({ channel: "TikTok", status: "success" });
        } catch (err) {
          console.error("TikTok Post Error:", err);
          tiktokStatus = `Error: ${err.message.substring(0, 60)}`;
          errors.push({ channel: "TikTok", error: err.message });
        }

        // Staggered delay to allow Buffer to process
        if (i < channels.length - 1) {
          await new Promise(resolve => setTimeout(resolve, INTER_PLATFORM_DELAY_MS));
        }
      }

      // 3. Facebook Reels
      else if (service === "facebook") {
        if (isChannelPublished(fbStatus)) {
          console.log(`[GATEKEEPER] Facebook channel already published for #${batch.id} on Sheet. Skipping.`);
          continue;
        }
        const existingOnBuffer = isDuplicateOnBuffer(recentBufferPosts, "facebook", batch.topic);
        if (existingOnBuffer) {
          console.warn(`🛑 [GATEKEEPER] Facebook post already exists on Buffer (ID: ${existingOnBuffer.id}) for '${batch.topic}'. Skipping mutation.`);
          fbStatus = `Published (Buffer ID: ${existingOnBuffer.id})`;
          results.push({ channel: "Facebook", status: "skipped_duplicate_on_buffer", postId: existingOnBuffer.id });
          continue;
        }

        try {
          const caption = meta.facebook.caption;
          const fbMetadata = {
            facebook: {
              type: "reel"
            }
          };
          await createBufferGraphQLPostWithRetry(token, ch.id, caption, directVideoUrls, fbMetadata);
          fbStatus = `Published (${nowStr})`;
          results.push({ channel: "Facebook", status: "success" });
        } catch (err) {
          console.error("Facebook Post Error:", err);
          fbStatus = `Error: ${err.message.substring(0, 60)}`;
          errors.push({ channel: "Facebook", error: err.message });
        }
      }
    }

    // Determine final status
    const isYtOk = isChannelPublished(youtubeStatus);
    const isTtOk = isChannelPublished(tiktokStatus);
    const isFbOk = isChannelPublished(fbStatus);

    const finalStatus = (isYtOk && isTtOk && isFbOk) ? "Published" : "Error";

    return {
      batchId: batch.id,
      topic: batch.topic,
      finalStatus,
      youtubeStatus,
      tiktokStatus,
      fbStatus,
      results,
      errors,
      isYtOk,
      isTtOk,
      isFbOk,
      fullyPublished: isYtOk && isTtOk && isFbOk
    };
  } finally {
    // Release in-flight lock after 10s grace period to prevent instant rapid spamming
    setTimeout(() => {
      IN_FLIGHT_PUBLISH_LOCKS.delete(lockKey);
    }, 10000);
  }
}
