from typing import Union
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from contextlib import asynccontextmanager
from fastapi.responses import FileResponse
from fastapi.params import Form
from typing import Annotated
from fastapi.responses import PlainTextResponse
from fastapi.responses import HTMLResponse

import logging
import colorlog
import sys
import os
import json
import re
from datetime import datetime, timedelta


class Entry(BaseModel):
	author: str
	entry: str

TIME_BETWEEN_ENTRIES = 60
last_entry_epoch = datetime.now() - timedelta(seconds=TIME_BETWEEN_ENTRIES)

@asynccontextmanager
async def lifespan(app: FastAPI):
	handler = colorlog.StreamHandler()
	handler.setFormatter(colorlog.ColoredFormatter("%(log_color)s[%(levelname)s]%(reset)s %(message)s"))

	# if "debug" is given on command line, set log level to debug
	if "debug" in sys.argv:
		logging.basicConfig(handlers=[handler], level=logging.DEBUG)
	else:
		logging.basicConfig(handlers=[handler], level=logging.INFO)

	yield

# this is a super simple guestbook app
app = FastAPI(lifespans=lifespan)


@app.get("/")
def read_root():
	return FileResponse("html/index.html")

VALID_ID_REGEX = re.compile(r"^[a-zA-Z0-9-]+$")
@app.get("/entries/{entry_id}", response_class=PlainTextResponse)
def read_entry(entry_id: str):
	# we need to prevent directory traversal attacks
	if not VALID_ID_REGEX.match(entry_id):
		raise HTTPException(status_code=400, detail="Invalid entry ID")

	# check if entry file exists
	path = f"entries/{entry_id}.txt"
	if not os.path.exists(path):
		raise HTTPException(status_code=404, detail="Entry not found")
	
	# read entry file
	with open(path, "r") as f:
		entry = f.read()
	return entry

# guestbook entries are simply stored as .txt in "entries" folder
@app.get("/entries/", response_class=HTMLResponse)
def read_entries():
	# get list of files in "entries" folder
	entries = [file for file in os.listdir("entries") if file.endswith(".txt")]
	
	html = "<!DOCTYPE html>"
	html += "<ul>"
	for entry in entries:
		# remove .txt extension
		entry = entry[:-4]
		html += f'<li><a href="/entries/{entry}">{entry}</a></li>'
	html += "</ul>"
	return html

@app.post("/entry/")
def create_entry(author: Annotated[str, Form()], message: Annotated[str, Form()]):
	# prevent spamming
	global last_entry_epoch
	epoch = datetime.now()
	if epoch - last_entry_epoch < timedelta(seconds=TIME_BETWEEN_ENTRIES):
		logging.warning(f"rejected entry from {author} as it was too soon after the last entry")
		raise HTTPException(status_code=429, detail="Too many entries in short time")

	# limit entry length to 1000 characters
	if len(message) > 1000:
		logging.warning(f"rejected entry from {author} as entry was too long")
		raise HTTPException(status_code=400, detail="Entry too long")
	
	# limit author length to 100 characters
	if len(author) > 100:
		logging.warning(f"rejected entry from {author} as author name was too long")
		raise HTTPException(status_code=400, detail="Author name too long")

	# create entry as json file (format: yyyy-mm-dd-hh-mm-ss-rnd.json)
	filename = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

	# append random number to filename to avoid overwriting
	filename += f"-{os.urandom(8).hex()}.txt"
	target_parth = f"entries/{filename}"
	with open(target_parth, "w") as f:
		# syntax for posts
		# 
		# From: author
		# Date: yyyy-mm-dd hh:mm:ss
		# 
		# message
		f.write(f"From: {author}\n")
		f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
		f.write(message)

	last_entry_epoch = epoch
	return PlainTextResponse("Thanks for your entry!")

