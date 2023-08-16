import requests

with requests.get(
    "https://api.scryfall.com/bulk-data/all_cards",
    params={"format": "file"},
    stream=True,
) as resp:
    for line in resp.iter_lines():
        print(line)
