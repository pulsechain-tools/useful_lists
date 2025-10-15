#!/usr/bin/env python3
import json
import socket
import sys
import time
import os
from typing import Optional

# Constants
IPC_PATH = "/mnt/fourtb/erigon/execution/erigon.ipc"
GET_RESERVES_SELECTOR = "0x0902f1ac"
MAX_UINT112 = (1 << 112) * 0.98


def send_ipc_request(payload: dict, ipc_path: str, timeout: float = 10.0) -> Optional[dict]:
    data = json.dumps(payload).encode()

    def _single_send():
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            s.settimeout(timeout)
            s.connect(ipc_path)
            s.sendall(data)
            s.shutdown(socket.SHUT_WR)
            chunks = []
            while True:
                try:
                    chunk = s.recv(8192)
                except socket.timeout:
                    break
                if not chunk:
                    break
                chunks.append(chunk)
            raw = b"".join(chunks).decode(errors="ignore").strip()
            if not raw:
                return None
            return json.loads(raw)
        finally:
            s.close()

    try:
        return _single_send()
    except Exception:
        time.sleep(0.5)
        try:
            return _single_send()
        except Exception:
            return None


def parse_get_reserves_result(hexdata: str):
    if not hexdata or not hexdata.startswith("0x"):
        return None
    h = hexdata[2:]
    h = h.rjust(64 * 3, "0")
    try:
        reserve0 = int(h[0:64], 16)
        reserve1 = int(h[64:128], 16)
        return reserve0, reserve1
    except Exception:
        return None


def get_lp_reserves(lp_address: str):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "eth_call",
        "params": [
            {"to": lp_address, "data": GET_RESERVES_SELECTOR},
            "latest",
        ],
    }
    result = send_ipc_request(payload, IPC_PATH)
    if not result or "result" not in result:
        raise RuntimeError(f"Failed to fetch reserves for LP address {lp_address}")
    return parse_get_reserves_result(result["result"])


def find_pools_by_token(token_address: str, file_path: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    matching_pools = [
        item for item in data
        if item.get("token0", "").lower() == token_address.lower() or item.get("token1", "").lower() == token_address.lower()
    ]

    return matching_pools


def fetch_token_details(token_addresses, ipc_path):
    payload = []
    id_to_addr = {}
    req_id = 1

    for addr in token_addresses:
        payload.append({
            "jsonrpc": "2.0",
            "id": req_id,
            "method": "eth_call",
            "params": [{"to": addr, "data": "0x313ce567"}, "latest"]  # decimals selector
        })
        id_to_addr[req_id] = addr
        req_id += 1

    rpc_results = send_ipc_request(payload, ipc_path)
    if isinstance(rpc_results, dict):
        rpc_results = [rpc_results]

    decimals_map = {}
    for item in rpc_results:
        rid = item.get("id")
        result = item.get("result")
        if not result or not isinstance(result, str):
            continue
        addr = id_to_addr.get(rid)
        if addr:
            try:
                decimals_map[addr] = int(result, 16)
            except ValueError:
                decimals_map[addr] = 18  # Default to 18 decimals if parsing fails

    return decimals_map


def main():
    if len(sys.argv) != 2:
        print("Usage: single_lp_balance.py <TOKEN_ADDRESS>")
        sys.exit(1)

    token_address = sys.argv[1]
    file_path = "/mnt/fiveh/DATA/pulsex_v2_lps.json"

    try:
        pools = find_pools_by_token(token_address, file_path)
        if not pools:
            print(f"No pools found for token address {token_address}")
            sys.exit(0)

        token_addresses = set()
        for pool in pools:
            token_addresses.add(pool["token0"].lower())
            token_addresses.add(pool["token1"].lower())

        decimals_map = fetch_token_details(token_addresses, IPC_PATH)

        for pool in pools:
            pool_address = pool["pool_address"]
            token0 = pool["token0"].lower()
            token1 = pool["token1"].lower()
            decimals0 = decimals_map.get(token0, 18)
            decimals1 = decimals_map.get(token1, 18)

            print(f"Processing pool: {pool_address}")

            try:
                reserves = get_lp_reserves(pool_address)
                if not reserves:
                    print(f"  Failed to fetch reserves for pool {pool_address}")
                    continue

                reserve0, reserve1 = reserves
                adjusted_reserve0 = reserve0 / (10 ** decimals0)
                adjusted_reserve1 = reserve1 / (10 ** decimals1)
                percentage0 = (adjusted_reserve0 / MAX_UINT112) * 100
                percentage1 = (adjusted_reserve1 / MAX_UINT112) * 100

                print(f"  Reserves for pool {pool_address}:")
                print(f"    Token 0: {adjusted_reserve0} ({percentage0:.2f}% of MAX_UINT112)")
                print(f"    Token 1: {adjusted_reserve1} ({percentage1:.2f}% of MAX_UINT112)")
            except Exception as e:
                print(f"  Error processing pool {pool_address}: {e}")

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()