from mangum import Mangum
from app.api import create_app

app = create_app()

lambda_handler = Mangum(app, lifespan="off")