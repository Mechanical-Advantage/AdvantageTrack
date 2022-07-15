# Creating a Google Cloud Project

Creating a Google Cloud Project allows the local Python server to interact with files in Google Drive. Google Cloud Projects can be created under a personal account or linked to an organization.

1. Go to the [Google Cloud Console](https://console.cloud.google.com) and log in.

2. Create a new project and select an organization if desired.

3. Go to the navigation menu in the upper left (three lines), then "APIs & Services" > "Library".

4. Search for the "Google Drive API" and click "Enable". Repeat for the "Google Sheets API".

5. Go to "APIs & Services" > "Credentials". Click "Create Credentials" > "Service account". Configure the account and click "Done".

6. Select the new service account. _Save the email address somewhere accessible._

7. Click "Keys" > "Add Key" > "Create new key" > "JSON" > "Create". A JSON file will be downloaded to your computer. These credentials will be used when setting up the server.
