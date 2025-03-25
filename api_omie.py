import requests
import os
import json
import time
from dotenv import load_dotenv
import config

# Start the timer
start_time = time.time()

def update_config_credentials():
    input_key = input("Please enter your app_key: ")
    input_secret = input("Please enter your app_secret: ")
    
    # Update the config file with new credentials
    with open('config.py', 'a') as f:
        f.write(f'\napp_key = "{input_key}"\n')
        f.write(f'app_secret = "{input_secret}"\n')
    return input_key, input_secret

def get_credentials():
    try:
        app_key = config.app_key
        app_secret = config.app_secret
        
        change = input("Credentials already exist. Would you like to change them? (y/n): ")
        if change.lower() == 'y':
            return update_config_credentials()
        return app_key, app_secret
    except AttributeError:
        print("No credentials found. Please enter your credentials.")
        return update_config_credentials()

def select_call_type():
    print("Please select the call you want to make:")
    for i, call_name in enumerate(config.calltype.keys(), 1):
        print(f"{i}. {call_name}")
    
    while True:
        try:
            selection = int(input("Enter the number of your selection: "))
            if 1 <= selection <= len(config.calltype):
                return list(config.calltype.keys())[selection-1]
            else:
                print("Invalid selection. Please enter a valid number.")
        except ValueError:
            print("Please enter a valid number.")

def api_omie(call, page=1, credentials=None):
    if credentials is None:
        app_key, app_secret = get_credentials()
    else:
        app_key, app_secret = credentials

    API_URL = config.calltype.get(call)
    if not API_URL:
        raise ValueError(f"Invalid call type: {call}")

    print("--------------------------------")
    print(f"Call: {call}")
    print(f"URL: {API_URL}")
    print(f"Page: {page}")
    print("--------------------------------")

    data = {
        "call": call,
        "app_key": app_key,
        "app_secret": app_secret,
        "param": [
            {
                "pagina": page,
                "registros_por_pagina": 50
            }
        ]
    }

    headers = {"Content-Type": "application/json"}
    response = requests.post(API_URL, json=data, headers=headers)
    
    if response.status_code != 200:
        print(f"Error: {response.status_code}")
        return None

    return response.json()

def get_unique_filename(base_name, extension=".json"):
    counter = 1
    new_filename = f"{base_name}{extension}"
    while os.path.exists(new_filename):
        new_filename = f"{base_name}_{counter}{extension}"
        counter += 1
    return new_filename

if __name__ == "__main__":
    try:
        # Get credentials once at the start
        credentials = get_credentials()
        
        # Select call type once at the start
        selected_call = select_call_type()
        
        all_results = []
        current_page = 1
        
        while True:
            result = api_omie(call=selected_call, page=current_page, credentials=credentials)
            if not result:
                break

            all_results.append(result)
            
            # Get total pages from response
            total_pages = result.get('total_de_paginas', 0)
            
            if current_page >= total_pages:
                break
                
            current_page += 1
            print(f"Fetching page {current_page} of {total_pages}")
            
        if all_results:
            # Combine all results into one JSON
            combined_result = json.dumps(all_results, indent=4, ensure_ascii=False)
            #print(combined_result)
            
            # Save combined response to file with unique name
            output_file = get_unique_filename("response")
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(combined_result)
            print(f"Response saved to {output_file}")
            
        # End the timer and calculate execution time
        end_time = time.time()
        execution_time = end_time - start_time
        print(f"Execution completed in {execution_time:.2f} seconds")
    
    except Exception as e:
        print(f"An error occurred: {str(e)}")