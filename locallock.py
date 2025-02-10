# -*- coding: utf-8 -*-

from config import version
import uuid
from datetime import datetime
from tzlocal import get_localzone

local_tz = get_localzone()
local_time = datetime.now(local_tz)
now = datetime.now(local_tz).isoformat()

random_string = str(uuid.uuid4())

def user_license():
    return {'li': random_string,'version': version,}

def user_config():
    li = user_license()['li']
    today = datetime.today().strftime("%Y-%m-%d")
    
    user_config = {
        'id': li,
        'user_type': 'free',
        'payment_time': now,
        'today': today,
        'free_num': 3,
    }
    
    return user_config