"""
Buffer API Client for Lele Chinese Social Automation.
Compliant with Zero-Leak Vault Isolation & Single Responsibility (<= 150 lines).
"""
import os, json, time, urllib.request, urllib.parse
from typing import Dict, Any, List, Optional

GRAPHQL_ENDPOINT = "https://api.buffer.com/graphql"
AUTH_URL = "https://buffer.com/oauth2/authorize"
TOKEN_URL = "https://api.bufferapp.com/1/oauth2/token.json"

CHANNEL_TOKEN_MAPPING = {
    "6a83dda0ccaf649a67c8cb92": "buffer1",  # YouTube Shorts
    "6a83dc5bccaf649a67c8b30f": "buffer1",  # TikTok
    "6a871331ccaf649a67e1b724": "buffer1",  # Facebook Fanpage
    "6a86bd97ccaf649a67dfcca8": "buffer2",  # Facebook Group
    "6a86beacccaf649a67dfcfba": "buffer2",  # Instagram
    "6a86bfa7ccaf649a67dfd25c": "buffer3",  # Twitter / X
    "6a86c04dccaf649a67dfd464": "buffer3",  # Pinterest
}


def load_buffer_credentials(custom_path: Optional[str] = None) -> Dict[str, Any]:
    """Loads Buffer credentials from env vars or isolated vault json file."""
    cid, csecret = os.getenv("BUFFER_CLIENT_ID", "").strip(), os.getenv("BUFFER_CLIENT_SECRET", "").strip()
    ruri, token = os.getenv("BUFFER_REDIRECT_URI", "").strip(), os.getenv("BUFFER_ACCESS_TOKEN", "").strip()
    tokens = {f"buffer{i}": os.getenv(f"BUFFER_ACCESS_TOKEN_{i}", "").strip() for i in range(1, 4)}

    search_paths = [
        custom_path, os.getenv("BUFFER_CREDENTIALS_FILE", ""),
        "/workspace/lelehoctiengtrung/credentials/buffer/credentials.json",
        os.path.expanduser("~/.cloud-profiles/lelehoctiengtrung/buffer/credentials.json"),
    ]
    for path in search_paths:
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                tokens.update(data.get("tokens", {}))
                return {
                    "client_id": data.get("client_id", cid), "client_secret": data.get("client_secret", csecret),
                    "redirect_uri": data.get("redirect_uri", ruri), "tokens": tokens,
                    "access_token": data.get("access_token", token) or tokens.get("buffer1", ""),
                }
            except Exception:
                pass
    return {"client_id": cid, "client_secret": csecret, "redirect_uri": ruri, "tokens": tokens, "access_token": token or tokens.get("buffer1", "")}


def get_channel_token(channel_id: str, creds: Optional[Dict[str, Any]] = None) -> str:
    """Resolves the correct access token for a given channel ID across Buffer accounts."""
    if creds is None:
        creds = load_buffer_credentials()
    tokens = creds.get("tokens", {})
    slot = CHANNEL_TOKEN_MAPPING.get(channel_id, "buffer1")
    return tokens.get(slot) or os.getenv(f"BUFFER_ACCESS_TOKEN_{slot[-1]}") or creds.get("access_token", "")


def get_authorization_url(client_id: str, redirect_uri: str, state: str = "lele_oauth") -> str:
    """Generates standard OAuth2 authorization redirect URL."""
    params = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "state": state}
    return f"{AUTH_URL}?{urllib.parse.urlencode(params)}"


def _http_post_json(url: str, payload: Dict[str, Any], headers: Optional[Dict[str, str]] = None, max_retries: int = 3) -> Dict[str, Any]:
    """Internal HTTP helper with 3-tier exponential backoff."""
    hdrs = {"Content-Type": "application/json"}
    if headers:
        hdrs.update(headers)
    data_bytes = json.dumps(payload).encode("utf-8")
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            req = urllib.request.Request(url, data=data_bytes, headers=hdrs, method="POST")
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_err = e
            if attempt < max_retries:
                time.sleep(1.0 * attempt)
    raise RuntimeError(f"Buffer HTTP POST failed after {max_retries} attempts: {last_err}")


def exchange_code_for_token(code: str, client_id: str, client_secret: str, redirect_uri: str) -> Dict[str, Any]:
    """Exchanges authorization code for an OAuth2 Access Token."""
    payload = {"client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri, "code": code, "grant_type": "authorization_code"}
    data = urllib.parse.urlencode(payload).encode("utf-8")
    req = urllib.request.Request(TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


from datetime import datetime, timezone, timedelta


def build_channel_metadata(channel_id: str, title: str, has_assets: bool) -> str:
    """Builds GraphQL metadata string per target channel."""
    safe_title = json.dumps(title)
    if channel_id == "6a83dda0ccaf649a67c8cb92":  # YouTube Shorts
        return f'metadata: {{ youtube: {{ title: {safe_title}, categoryId: "27", privacy: public, notifySubscribers: true, madeForKids: false }} }}'
    elif channel_id == "6a83dc5bccaf649a67c8b30f":  # TikTok
        return 'metadata: { tiktok: { isAiGenerated: true } }'
    elif channel_id in ["6a871331ccaf649a67e1b724", "6a86bd97ccaf649a67dfcca8"]:  # FB Fanpage / Group
        return 'metadata: { facebook: { type: reel } }' if has_assets else 'metadata: { facebook: { type: post } }'
    elif channel_id == "6a86beacccaf649a67dfcfba":  # Instagram
        return 'metadata: { instagram: { type: reel } }' if has_assets else 'metadata: { instagram: { type: post } }'
    return ""


def publish_post(
    access_token: str,
    channel_id: str,
    text: str,
    media_urls: Optional[List[str]] = None,
    mode: str = "customScheduled",
    title: Optional[str] = None,
    delay_minutes: int = 30,
    due_at: Optional[str] = None,
) -> Dict[str, Any]:
    """Publishes or schedules a post (default: 30 minutes later) via Buffer GraphQL API."""
    assets = [f'{{ video: {{ url: "{u}" }} }}' if any(k in u.lower() for k in [".mp4", "download", "uc?", "drive", "video"]) else f'{{ image: {{ url: "{u}" }} }}' for u in (media_urls or [])]
    assets_str = f"[{', '.join(assets)}]"
    meta_str = build_channel_metadata(channel_id, title or text.split("\n")[0][:90], bool(assets))

    due_clause = ""
    if mode == "customScheduled":
        if not due_at:
            due_at = (datetime.now(timezone.utc) + timedelta(minutes=delay_minutes)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
        due_clause = f'dueAt: "{due_at}",'

    mutation = f"""
    mutation {{
      createPost(input: {{
        channelId: "{channel_id}", text: {json.dumps(text)}, mode: {mode},
        {due_clause}
        needsApproval: false, schedulingType: automatic, saveToDraft: false,
        assets: {assets_str}, {meta_str}
      }}) {{
        ... on PostActionSuccess {{ post {{ id status dueAt }} }}
        ... on InvalidInputError {{ message }}
        ... on UnauthorizedError {{ message }}
        ... on LimitReachedError {{ message }}
        ... on NotFoundError {{ message }}
        ... on UnexpectedError {{ message }}
        ... on RestProxyError {{ message }}
      }}
    }}
    """
    res = _http_post_json(GRAPHQL_ENDPOINT, {"query": mutation}, {"Authorization": f"Bearer {access_token}"})
    if "errors" in res and res["errors"]:
        raise ValueError(f"Buffer GraphQL error: {res['errors'][0].get('message')}")
    action_res = res.get("data", {}).get("createPost", {})
    if "message" in action_res:
        raise ValueError(f"Buffer Action error: {action_res['message']}")
    return action_res.get("post", {})
