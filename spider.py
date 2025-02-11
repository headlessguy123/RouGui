# -*- coding: utf-8 -*-

import os
import json
from config import basePath

def load_video():
    with open(os.path.join(basePath, 'videos.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data