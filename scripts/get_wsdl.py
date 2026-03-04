import requests
import os

# These should match the values you use in your SOAP client
# Based on your code logic:
plant_ip = "172.19.4.127"  # Replace with the IP you use in pipeline-eds
port = "43080"
wsdl_sub_path = "eds.wsdl"

# Construct the URL
wsdl_url = f"http://{plant_ip}:{port}/{wsdl_sub_path}"
save_path = os.path.expanduser("~/dev/pipeline-eds/eds.wsdl")

try:
    print(f"Connecting to: {wsdl_url}")
    response = requests.get(wsdl_url, timeout=10)
    response.raise_for_status()  # Check for HTTP errors
    
    with open(save_path, "wb") as f:
        f.write(response.content)
        
    print(f"Success! WSDL saved to: {save_path}")
    print("You can now upload this file to Power Automate Custom Connectors.")

except Exception as e:
    print(f"Failed to download WSDL: {e}")
    print("Check if you are on the plant VPN/Network and if the IP/Port is correct.")
