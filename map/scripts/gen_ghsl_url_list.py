#!/usr/bin/env python3
import argparse
import re
import urllib.request


def fetch_tile_list(base_url: str) -> list[str]:
    with urllib.request.urlopen(base_url) as resp:
        html = resp.read().decode("utf-8", errors="ignore")
    # Find all zip filenames in the index
    return re.findall(r"(GHS_POP_[^\\s\\\"]+?\\.zip)", html)


def build_urls(epoch: int, res: int, scheme: str):
    root = f"{scheme}://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/GHSL/GHS_POP_GLOBE_R2023A"
    dataset = f"GHS_POP_E{epoch}_GLOBE_R2023A_54009_{res}"
    tiles_url = f"{root}/{dataset}/V1-0/tiles/"
    zips = fetch_tile_list(tiles_url)
    for zip_name in zips:
        name = zip_name.replace(".zip", "")
        url = f"/vsizip//vsicurl/{tiles_url}{zip_name}/{name}.tif"
        yield url


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epoch", type=int, default=2020)
    parser.add_argument("--res", type=int, choices=[100, 1000], default=100)
    parser.add_argument("--scheme", choices=["https", "http"], default="https")
    args = parser.parse_args()
    for url in build_urls(args.epoch, args.res, args.scheme):
        print(url)


if __name__ == "__main__":
    main()
