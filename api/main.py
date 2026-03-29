from fastapi import FastAPI

# Initialisation de l'application
app = FastAPI(
    title="NetCapt API",
    description="API d'administration du système NetCapt",
    version="1.0.0"
)


@app.get("/")
def root():
    """
    Endpoint de test pour vérifier que l'API fonctionne.
    """
    return {"message": "NetCapt API is running"}