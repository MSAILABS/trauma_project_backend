from datetime import datetime
import os
import time
import uvicorn
from dotenv import load_dotenv
import logging as log
from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from starlette.middleware.cors import CORSMiddleware
from router.base import api_router

# loading environment variables
load_dotenv()
# setting up logger
logger = log.getLogger(__name__)

def setup_logging(): 
    # Get the current date and time 
    current_time = datetime.now().strftime("date=%Y_%m_%d_time=%H_%M_%S")
    # Check if logs directory exists, if not, create it 
    if not os.path.exists("logs"): 
        os.makedirs("logs")

    log_filename = os.path.join("logs",f'agent_{current_time}.log')
    # Configure logging 
    log.basicConfig( 
        level=log.INFO, # Set the log level 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', # Format for the log messages 
        handlers=[ 
            log.FileHandler(log_filename), # Log messages to a file named bot.log 
            log.StreamHandler() # Also print log messages to the console 
        ] 
    ) 
    return log_filename


@asynccontextmanager
async def lifespan(app: FastAPI):
    # this code will run when application starts
    log.info('app Starting................')
    time.sleep(30)
    yield

    # this code will run when application shutdown
    log.info('app Shutting down................')


def application_setup():
    lfp = setup_logging()

    app = FastAPI(docs_url="/msai-docs", swagger_ui_parameters={"tryItOutEnabled": True}, title="MSAI ECG VISUALIZATION", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    if lfp:
        log.info('Log has been setup at '+ os.path.abspath(lfp))

    app.include_router(api_router)

    return app

app = application_setup()

@app.get("/")
async def read_root():
    return {"Message": "Welcome to MSAI LABS Visualization API."}

if __name__ == "__main__": 
    uvicorn.run("main:app", host="0.0.0.0", port=5001)