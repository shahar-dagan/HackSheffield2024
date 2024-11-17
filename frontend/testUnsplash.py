import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_unsplash():
    # Get your access key
    access_key = os.getenv("UNSPLASH_ACCESS_KEY")
    print(f"Using Access Key: {access_key}")

    # Test URL
    url = "https://api.unsplash.com/photos/random"

    # Headers
    headers = {
        "Authorization": f"Client-ID {access_key}",
        "Accept-Version": "v1",
    }

    try:
        # Make request
        response = requests.get(url, headers=headers)

        # Print full response details
        print("\nResponse Status:", response.status_code)
        print("\nResponse Headers:")
        for key, value in response.headers.items():
            print(f"{key}: {value}")
        print("\nResponse Body:")
        print(response.text)

    except Exception as e:
        print(f"Error: {str(e)}")


if __name__ == "__main__":
    test_unsplash()
