# You can find the API endpoints in the OMIE API documentation: https://developer.omie.com.br/api/
# If there is a new endpoint, you can add it to the calltype dictionary below.
# API endpoints configuration
calltype = {
    "ListarContasReceber": "https://app.omie.com.br/api/v1/financas/contareceber/",
    "ListarContasPagar": "https://app.omie.com.br/api/v1/financas/contapagar/",
    "ListarDepatartamentos": "https://app.omie.com.br/api/v1/geral/departamentos/",    
    "ListarProjetos": "https://app.omie.com.br/api/v1/geral/projetos/",
    "ListarClientes": "https://app.omie.com.br/api/v1/geral/clientes/",
    "ListarCategorias": "https://app.omie.com.br/api/v1/geral/categorias/",
    "ListarContasCorrentes": "https://app.omie.com.br/api/v1/geral/contacorrente/",
    }

# If you want to use your own credentials, you can add them to a .env file and use the os.getenv() function to get them. 
# For ease of use, you can just uncomment the following lines and add your credentials to the .env file.
"""
import os
from dotenv import load_dotenv

load_dotenv() 

app_key = os.getenv("APP_KEY")
app_secret = os.getenv("APP_SECRET")
"""