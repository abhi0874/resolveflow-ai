"""Use the authenticated local API; never bypass workspace authorization."""

import argparse
import getpass
import json
import uuid

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["index", "search"])
    parser.add_argument("--workspace", required=True, type=uuid.UUID)
    parser.add_argument("--document", type=uuid.UUID)
    parser.add_argument("--query")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--top-k", type=int, default=5)
    args = parser.parse_args()
    if args.command == "index" and not args.document:
        parser.error("--document is required for indexing")
    if args.command == "search" and not args.query:
        parser.error("--query is required for search")
    with httpx.Client(base_url="http://127.0.0.1:8000/api/v1", timeout=60) as client:

        def post(path, body):
            token = client.get("/auth/csrf")
            token.raise_for_status()
            return client.post(
                path,
                json=body,
                headers={
                    "Origin": "http://127.0.0.1:3000",
                    "X-CSRF-Token": token.json()["csrf_token"],
                },
            )

        login = post(
            "/auth/login", {"email": input("Account email: "), "password": getpass.getpass()}
        )
        if not login.is_success:
            raise SystemExit(f"Login failed ({login.status_code})")
        try:
            prefix = f"/workspaces/{args.workspace}"
            response = (
                post(prefix + f"/documents/{args.document}/index", {"force": args.force})
                if args.command == "index"
                else post(
                    prefix + "/knowledge-base/search", {"query": args.query, "top_k": args.top_k}
                )
            )
            if not response.is_success:
                raise SystemExit(f"Request failed ({response.status_code})")
            print(json.dumps(response.json(), indent=2))
        finally:
            post("/auth/logout", {})


if __name__ == "__main__":
    main()
