import requests  # Change the import at the top

# Replace the urlopen block with this:
response = requests.get("https://yahoo.com", timeout=5)
source = response.content

data = json.loads(source)

# print(json.dumps(data, indent=2))

usd_rates = dict()

for item in data['list']['resources']:
    name = item['resource']['fields']['name']
    price = item['resource']['fields']['price']
    usd_rates[name] = price

print(50 * float(usd_rates['USD/INR']))
