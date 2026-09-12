/**
 * Google Sheets API v4 Client using Pure WebCrypto (RS256 JWT)
 * Fully compatible with Cloudflare Workers (No external npm packages required)
 */

let cachedAccessToken = null;
let tokenExpiryTime = 0;

/**
 * Get Vietnam Timestamp string (GMT+7) in YYYY-MM-DD HH:MM:SS format
 */
export function getVietnamTimestamp(date = new Date()) {
  const vnTime = new Date(date.getTime() + (7 * 60 * 60 * 1000));
  return vnTime.toISOString().replace("T", " ").substring(0, 19);
}

/**
 * Base64URL encode string or buffer
 */
function base64UrlEncode(data) {
  let base64;
  if (typeof data === "string") {
    base64 = btoa(unescape(encodeURIComponent(data)));
  } else if (data instanceof Uint8Array || data instanceof ArrayBuffer) {
    let binary = "";
    const bytes = new Uint8Array(data);
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    base64 = btoa(binary);
  }
  return base64.replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

/**
 * Convert PEM RSA private key string to binary ArrayBuffer (PKCS#8)
 */
function pemToArrayBuffer(pem) {
  const b64Lines = pem
    .replace(/-----BEGIN[ A-Z0-9_-]+-----/g, "")
    .replace(/-----END[ A-Z0-9_-]+-----/g, "")
    .replace(/\s+/g, "");
  const binary = atob(b64Lines);
  const buffer = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    buffer[i] = binary.charCodeAt(i);
  }
  return buffer.buffer;
}

/**
 * Generate Google OAuth2 Access Token using RS256 JWT
 */
export async function getGoogleAccessToken(clientEmail, privateKeyPem) {
  const now = Math.floor(Date.now() / 1000);
  if (cachedAccessToken && now < tokenExpiryTime - 120) {
    return cachedAccessToken;
  }

  if (!clientEmail || !privateKeyPem) {
    throw new Error("GCP Service Account Email or Private Key is missing in Cloudflare Worker environment.");
  }

  const header = {
    alg: "RS256",
    typ: "JWT"
  };

  const claimSet = {
    iss: clientEmail,
    scope: "https://www.googleapis.com/auth/spreadsheets",
    aud: "https://oauth2.googleapis.com/token",
    exp: now + 3600,
    iat: now
  };

  const encodedHeader = base64UrlEncode(JSON.stringify(header));
  const encodedClaimSet = base64UrlEncode(JSON.stringify(claimSet));
  const unsignedToken = `${encodedHeader}.${encodedClaimSet}`;

  // Import PKCS#8 private key
  const binaryKey = pemToArrayBuffer(privateKeyPem);
  const cryptoKey = await crypto.subtle.importKey(
    "pkcs8",
    binaryKey,
    {
      name: "RSASSA-PKCS1-v1_5",
      hash: "SHA-256"
    },
    false,
    ["sign"]
  );

  // Sign token
  const signatureBuffer = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    cryptoKey,
    new TextEncoder().encode(unsignedToken)
  );

  const signature = base64UrlEncode(signatureBuffer);
  const jwt = `${unsignedToken}.${signature}`;

  // Exchange JWT for access token
  const tokenRes = await fetch("https://oauth2.googleapis.com/token", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams({
      grant_type: "urn:ietf:params:oauth:grant-type:jwt-bearer",
      assertion: jwt
    })
  });

  const tokenData = await tokenRes.json();
  if (!tokenRes.ok || !tokenData.access_token) {
    throw new Error(`Failed to obtain Google access token: ${JSON.stringify(tokenData)}`);
  }

  cachedAccessToken = tokenData.access_token;
  tokenExpiryTime = now + (tokenData.expires_in || 3600);
  return cachedAccessToken;
}

export class GoogleSheetsClient {
  constructor(clientEmail, privateKeyPem, spreadsheetId, tabName = "pinyin") {
    this.clientEmail = clientEmail;
    this.privateKeyPem = privateKeyPem;
    this.spreadsheetId = spreadsheetId;
    this.tabName = tabName;
  }

  async getAuthToken() {
    return await getGoogleAccessToken(this.clientEmail, this.privateKeyPem);
  }

  /**
   * Fetch all rows from spreadsheet
   */
  async getSheetValues(range = `${this.tabName}!A1:P500`) {
    const token = await this.getAuthToken();
    const url = `https://sheets.googleapis.com/v4/spreadsheets/${this.spreadsheetId}/values/${encodeURIComponent(range)}`;
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` }
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Google Sheets API Error (${res.status}): ${err}`);
    }

    const data = await res.json();
    return data.values || [];
  }

  /**
   * Get all rows from current tab
   */
  async getAllRows() {
    return await this.getSheetValues(`${this.tabName}!A1:P500`);
  }

  /**
   * Append new rows to sheet
   */
  async appendRows(rows) {
    const token = await this.getAuthToken();
    const range = `${this.tabName}!A:P`;
    const url = `https://sheets.googleapis.com/v4/spreadsheets/${this.spreadsheetId}/values/${encodeURIComponent(range)}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS`;

    const res = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        values: rows
      })
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Google Sheets Append Error (${res.status}): ${err}`);
    }

    return await res.json();
  }

  /**
   * Update specific cell or range
   */
  async updateRange(range, values) {
    const token = await this.getAuthToken();
    const url = `https://sheets.googleapis.com/v4/spreadsheets/${this.spreadsheetId}/values/${encodeURIComponent(range)}?valueInputOption=USER_ENTERED`;

    const res = await fetch(url, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        values: values
      })
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Google Sheets Update Error (${res.status}): ${err}`);
    }

    return await res.json();
  }

  /**
   * Update a single cell value
   */
  async updateCell(cellRange, value) {
    return await this.updateRange(cellRange, [[value]]);
  }

  /**
   * Clear a specific range
   */
  async clearRange(range) {
    const token = await this.getAuthToken();
    const url = `https://sheets.googleapis.com/v4/spreadsheets/${this.spreadsheetId}/values/${encodeURIComponent(range)}:clear`;

    const res = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json"
      }
    });

    if (!res.ok) {
      const err = await res.text();
      throw new Error(`Google Sheets Clear Error (${res.status}): ${err}`);
    }

    return await res.json();
  }

  /**
   * Get vocabulary history for smart anti-duplication:
   * - allUsedWords: ALL words that have appeared in the entire sheet
   * - recent5Words: words in the last 5 videos
   * - allTopics: list of all existing topic names on the sheet
   * - recentTopics: list of recent topic names
   */
  async getVocabHistory() {
    const rows = await this.getSheetValues(`${this.tabName}!A2:I500`);
    if (!rows || rows.length === 0) {
      return {
        allUsedWords: [],
        recent5Words: [],
        olderWords: [],
        allTopics: [],
        recentTopics: []
      };
    }

    const allUsedWordsSet = new Set();
    const recentRows = rows.slice(-5);
    const recentWordsSet = new Set();

    for (let rIdx = 0; rIdx < rows.length; rIdx++) {
      const r = rows[rIdx];
      const isRecent = rIdx >= (rows.length - 5);
      for (let i = 4; i <= 8; i++) {
        if (r[i]) {
          const hz = r[i].split("|")[0].trim();
          if (hz) {
            allUsedWordsSet.add(hz);
            if (isRecent) recentWordsSet.add(hz);
          }
        }
      }
    }

    const allTopics = rows.map(r => (r[1] || "").trim()).filter(Boolean);
    const recentTopics = allTopics;

    const pastBatches = rows.map((r, idx) => {
      const batchWords = [];
      for (let i = 4; i <= 8; i++) {
        if (r[i]) {
          const hz = r[i].split("|")[0].trim();
          if (hz) batchWords.push(hz);
        }
      }
      return {
        id: r[0] || String(idx + 1),
        topic: (r[1] || "").trim(),
        words: batchWords
      };
    }).filter(b => b.words.length > 0);

    return {
      allUsedWords: Array.from(allUsedWordsSet),
      recent5Words: Array.from(recentWordsSet),
      allTopics: allTopics,
      recentTopics: recentTopics,
      pastBatches: pastBatches
    };
  }

  /**
   * Get all used Chinese words across the sheet
   */
  async getExistingWords() {
    const history = await this.getVocabHistory();
    return history.allUsedWords;
  }

  /**
   * Find row number and data by batch ID (Col A or numeric ID)
   */
  async findRowByBatchId(batchId) {
    const cleanId = String(batchId).replace(/^#/, "").trim();
    const rows = await this.getSheetValues(`${this.tabName}!A1:P500`);
    if (!rows || rows.length < 2) return null;

    for (let i = 1; i < rows.length; i++) {
      const row = rows[i];
      const rowId = String(row[0] || "").replace(/^#/, "").trim();
      const rowNum = i + 1;

      if (rowId === cleanId) {
        return {
          rowNumber: rowNum,
          id: row[0] || String(rowNum),
          topic: row[1] || "",
          level: row[2] || "",
          status: (row[3] || "").trim(),
          rawRow: row
        };
      }
    }
    return null;
  }

  /**
   * Get full batch object by ID (Col A or numeric ID)
   */
  async getBatchById(batchId) {
    const cleanId = String(batchId).replace(/^#/, "").trim();
    const rows = await this.getSheetValues(`${this.tabName}!A1:P500`);
    if (!rows || rows.length < 2) return null;

    for (let i = 1; i < rows.length; i++) {
      const row = rows[i];
      const rowId = String(row[0] || "").replace(/^#/, "").trim();
      const rowNumber = i + 1;

      if (rowId === cleanId) {
        const words = [];
        for (let wIdx = 4; wIdx <= 8; wIdx++) {
          const wVal = row[wIdx] || "";
          if (wVal) {
            const parts = wVal.split("|").map(s => s.trim());
            words.push({
              hanzi: parts[0] || "",
              pinyin: parts[1] || "",
              hidden_pinyin: parts[2] || "",
              meaning: parts[3] || parts[0] || ""
            });
          }
        }

        return {
          rowNumber: rowNumber,
          id: row[0] || String(rowNumber),
          topic: row[1] || "HSK 1-2",
          level: row[2] || "HSK 1-2",
          status: (row[3] || "").trim(),
          words: words,
          metadata: row[9] || "",
          videoUrl: row[10] || "",
          youtube: row[11] || "",
          tiktok: row[12] || "",
          facebook: row[13] || "",
          createdAt: row[14] || "",
          notes: row[15] || "",
          rawRow: row
        };
      }
    }
    return null;
  }

  /**
   * Get list of batches with matching status ('Pending', 'Ready', 'Error', 'Video', etc.)
   */
  async getBatchesByStatus(targetStatuses) {
    const statuses = Array.isArray(targetStatuses)
      ? targetStatuses.map(s => s.toLowerCase())
      : [targetStatuses.toLowerCase()];

    const rows = await this.getSheetValues(`${this.tabName}!A1:P500`);
    if (!rows || rows.length < 2) return [];

    const results = [];

    for (let rowIdx = 1; rowIdx < rows.length; rowIdx++) {
      const row = rows[rowIdx];
      const rowNumber = rowIdx + 1; // 1-indexed sheet row number
      const status = (row[3] || "").trim(); // Col D (index 3) is Status

      if (statuses.includes(status.toLowerCase())) {
        const words = [];
        for (let wIdx = 4; wIdx <= 8; wIdx++) {
          const wVal = row[wIdx] || "";
          if (wVal) {
            const parts = wVal.split("|").map(s => s.trim());
            words.push({
              hanzi: parts[0] || "",
              pinyin: parts[1] || "",
              hidden_pinyin: parts[2] || "",
              meaning: parts[3] || parts[0] || ""
            });
          }
        }

        results.push({
          rowNumber: rowNumber,
          id: row[0] || String(rowNumber),
          topic: row[1] || "HSK 1-2",
          level: row[2] || "HSK 1-2",
          status: status,
          words: words,
          metadata: row[9] || "",
          videoUrl: row[10] || "",
          youtube: row[11] || "",
          tiktok: row[12] || "",
          facebook: row[13] || "",
          createdAt: row[14] || "",
          notes: row[15] || "",
          rawRow: row
        });
      }
    }

    return results;
  }

  /**
   * Update video status and links
   */
  async updateBatchStatus(rowNumber, status, videoLink = "", metadataLink = "") {
    // Col D: Status (Col 4)
    await this.updateRange(`${this.tabName}!D${rowNumber}`, [[status]]);
    if (metadataLink) {
      await this.updateRange(`${this.tabName}!J${rowNumber}`, [[metadataLink]]);
    }
    if (videoLink) {
      await this.updateRange(`${this.tabName}!K${rowNumber}`, [[videoLink]]);
    }
  }

  /**
   * Overwrite an entire batch row with newly regenerated words & metadata, resetting status to 'Pending'
   */
  async repairBatchRow(rowNumber, topic, level, words, metadataText, notes) {
    const wordCols = [];
    for (let wIdx = 0; wIdx < 5; wIdx++) {
      const w = words[wIdx];
      if (w) {
        wordCols.push(`${w.hanzi} | ${w.pinyin} | ${w.hidden_pinyin} | ${w.meaning}`);
      } else {
        wordCols.push("");
      }
    }

    const rowUpdates = [[
      topic,           // Col B
      level,           // Col C
      "Pending",       // Col D: Reset Status to Pending
      wordCols[0] || "", // Col E
      wordCols[1] || "", // Col F
      wordCols[2] || "", // Col G
      wordCols[3] || "", // Col H
      wordCols[4] || "", // Col I
      metadataText || "", // Col J
      "",              // Col K: Clear old video link
      "",              // Col L: Youtube
      "",              // Col M: Tiktok
      "",              // Col N: Facebook
      getVietnamTimestamp(), // Col O: Created_At in GMT+7
      notes            // Col P: Notes
    ]];

    await this.updateRange(`${this.tabName}!B${rowNumber}:P${rowNumber}`, rowUpdates);
  }

  /**
   * Delete batch row (Set status to Deleted and clear video links)
   */
  async deleteBatchRow(rowNumber) {
    await this.updateRange(`${this.tabName}!D${rowNumber}`, [["Deleted"]]);
    await this.updateRange(`${this.tabName}!K${rowNumber}`, [[""]]);
  }

  /**
   * Completely clear the entire row content from sheet (A:P)
   */
  async clearBatchRowContent(rowNumber) {
    await this.clearRange(`${this.tabName}!A${rowNumber}:P${rowNumber}`);
  }

  /**
   * Update social posting info and final status ('Published' or 'Error')
   */
  async updateSocialPublishStatus(rowNumber, finalStatus, { youtube = "", tiktok = "", facebook = "" }) {
    // 1. Col D: Status (Published or Error)
    await this.updateRange(`${this.tabName}!D${rowNumber}:D${rowNumber}`, [[finalStatus]]);

    // 2. Col L, M, N: Youtube, Tiktok, Facebook
    const updates = [[
      youtube || "",
      tiktok || "",
      facebook || ""
    ]];
    await this.updateRange(`${this.tabName}!L${rowNumber}:N${rowNumber}`, updates);
  }

  /**
   * Get stats summary for:
   * - Pending (chờ render)
   * - Video (chờ kiểm duyệt duyệt)
   * - Ready (đã duyệt, sẵn sàng đăng tự động)
   * - Error (bị lỗi khi đăng bài)
   */
  async getStatusSummary() {
    const rows = (await this.getSheetValues(`${this.tabName}!A2:P500`)) || [];
    let pendingCount = 0;
    let videoCount = 0;
    let readyCount = 0;
    let failedCount = 0;
    let errorCount = 0;
    const errorDetails = [];

    let readyHsk1 = 0, readyHsk2 = 0, readyHsk3 = 0;
    let pendingHsk1 = 0, pendingHsk2 = 0, pendingHsk3 = 0;
    let videoHsk1 = 0, videoHsk2 = 0, videoHsk3 = 0;

    for (let idx = 0; idx < rows.length; idx++) {
      const row = rows[idx];
      const rowNumber = idx + 2;
      const status = (row[3] || "").trim().toLowerCase();
      const rowId = row[0] || `#${rowNumber}`;
      const topic = row[1] || "";
      const rawLevel = (row[2] || "").trim().toUpperCase();

      let level = "HSK 1";
      if (rawLevel.includes("3")) level = "HSK 3";
      else if (rawLevel.includes("2")) level = "HSK 2";

      if (status === "pending") {
        pendingCount++;
        if (level === "HSK 3") pendingHsk3++;
        else if (level === "HSK 2") pendingHsk2++;
        else pendingHsk1++;
      } else if (status === "video") {
        videoCount++;
        if (level === "HSK 3") videoHsk3++;
        else if (level === "HSK 2") videoHsk2++;
        else videoHsk1++;
      } else if (status === "ready") {
        readyCount++;
        if (level === "HSK 3") readyHsk3++;
        else if (level === "HSK 2") readyHsk2++;
        else readyHsk1++;
      } else if (status === "failed") {
        failedCount++;
      } else if (status === "error") {
        errorCount++;
        // Check missing channels
        const missing = [];
        if (!row[11] || !row[11].trim().toLowerCase().startsWith("pub")) missing.push("YouTube");
        if (!row[12] || !row[12].trim().toLowerCase().startsWith("pub")) missing.push("TikTok");
        if (!row[13] || !row[13].trim().toLowerCase().startsWith("pub")) missing.push("Facebook");
        errorDetails.push({
          rowId,
          topic,
          missingChannels: missing.join(", ") || "Chưa đăng"
        });
      }
    }

    return {
      pendingCount,
      videoCount,
      readyCount,
      failedCount,
      errorCount,
      errorDetails,
      readyByLevel: {
        hsk1: readyHsk1,
        hsk2: readyHsk2,
        hsk3: readyHsk3
      },
      pendingByLevel: {
        hsk1: pendingHsk1,
        hsk2: pendingHsk2,
        hsk3: pendingHsk3
      },
      videoByLevel: {
        hsk1: videoHsk1,
        hsk2: videoHsk2,
        hsk3: videoHsk3
      }
    };
  }
}
