# OMIE API Integration Tool

## Overview
This tool allows you to interact with the OMIE API to retrieve various financial and business data in a automatic way without the need to re-write the code for every request.

## Setup

### Credentials
There are two ways to set up your OMIE API credentials:

1. **Interactive Setup**: Run the script and it will prompt you to enter your credentials, which will be saved to `config.py`. (Not recommended if this code will be shared later!!)

2. **Environment Variables**: You can store your credentials in a `.env` file:
   ```
   APP_KEY=123456789
   APP_SECRET=fr98765432112345g6789
   ```
   
   Then uncomment these lines in `config.py`:
   ```python
   # app_key = os.getenv("APP_KEY")
   # app_secret = os.getenv("APP_SECRET")
   ```

## Available API Endpoints
The tool supports the following OMIE API endpoints:
- ListarContasReceber - Accounts Receivable
- ListarContasPagar - Accounts Payable
- ListarDepatartamentos - Departments
- ListarProjetos - Projects
- ListarClientes - Clients
- ListarCategorias - Categories
- ListarContasCorrentes - Bank Accounts

## Usage
Run the main script and follow the interactive prompts to select which API endpoint you want to query.


PS - This code was "Vibe Coded" while watching ThePrimeagen make the tower defence game 2025-03-25 25:50 (YYY-MM-DD)