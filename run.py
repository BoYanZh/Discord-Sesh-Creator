import datetime
import hashlib
import json
import time

import httpx
import toml

HEADERS = {
    "accept": "*/*",
    "accept-language": "en,zh-CN;q=0.9,zh;q=0.8,en-GB;q=0.7,en-US;q=0.6,zh-TW;q=0.5",
    "content-type": "application/json",
    "sec-ch-ua": '"Not.A/Brand";v="8", "Chromium";v="114", "Microsoft Edge";v="114"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",
    "Referrer-Policy": "strict-origin-when-cross-origin",
}


def main():
    config = toml.load(open("config.toml"))
    user_id = config["user_id"]
    guild_id = config["guild_id"]
    channel_id = config["channel_id"]
    access_token = config["access_token"]
    duration_hours = config.get("duration_hours", 2)
    days_in_advance = config.get("days_in_advance", 3)
    now = datetime.datetime.utcnow()
    transport = httpx.HTTPTransport(retries=5)
    with httpx.Client(transport=transport, timeout=30.0) as client:
        url = "https://sesh.fyi/trpc/poll.list"
        headers = HEADERS.copy()
        headers["Referer"] = f"https://sesh.fyi/dashboard/{guild_id}/polls"
        headers["token_type"] = "Bearer"
        headers["access_token"] = access_token
        created_polls = []
        page = 0
        while True:
            params = {
                "batch": 1,
                "input": json.dumps(
                    {
                        "0": {
                            "guild_id": f"{guild_id}",
                            "include_completed": False,
                            "page": page,
                            "sort": {"type": "Created", "direction": "ASC"},
                            "search": "",
                        }
                    }
                ),
            }
            r = client.get(url, headers=headers, params=params)
            data = r.json()[0]["result"]["data"]
            created_polls.extend(data["items"])
            if len(created_polls) >= data["total_item_count"]:
                break
            page += 1
            time.sleep(1)
        print("Created polls: ", created_polls)
        fmt_time = lambda t: t.isoformat(sep="T", timespec="milliseconds") + "Z"
        for days in range(days_in_advance):
            start_time = now.replace(
                hour=0, minute=0, second=0, microsecond=0
            ) + datetime.timedelta(days=days)
            options = [
                {
                    "name": fmt_time(
                        start_time + datetime.timedelta(hours=i * duration_hours)
                    ),
                    "is_newly_added": True,
                }
                for i in range(24 // duration_hours)
            ]
            end_time = start_time + datetime.timedelta(days=1)
            poll_name = (
                "Game Time Poll "
                + hashlib.sha256(
                    (
                        start_time.isoformat(sep=" ", timespec="seconds") + " UTC+0"
                    ).encode()
                ).hexdigest()[:7]
            )
            if next(filter(lambda x: x["poll_name"] == poll_name, created_polls), None):
                print(poll_name, "found, skipping")
                continue
            print(poll_name, "not found, creating")
            url = "https://sesh.fyi/api/create_poll"
            payload = {
                "user_id": f"{user_id}",
                "guild_id": f"{guild_id}",
                "channel_id": f"{channel_id}",
                "description": "The times in the options are shown in your local time zone.",
                "options": options,
                "title": poll_name,
                "end_time": fmt_time(end_time),
                "allow_anyone_to_add": True,
                "eligible_role_ids": [],
                "image_url": "",
                "single_vote_per_user": False,
                "is_anonymous": False,
                "access_token": access_token,
                "token_type": "Bearer",
                "poll_type": 1,
                "forum_tag_ids": [],
                "role_mention_ids": [],
                "user_mentions_ids": [],
            }
            headers = HEADERS.copy()
            headers[
                "Referer"
            ] = f"https://sesh.fyi/dashboard/{guild_id}/polls/create?channel_id={channel_id}"
            r = client.post(url, headers=headers, json=payload)
            assert r.json()["is_success"]


if __name__ == "__main__":
    main()
