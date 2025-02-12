# -*- coding: utf-8 -*-

import os
import json
from config import basePath

def load_video():
    videos_path = os.path.join(basePath, 'videos.json')
    if os.path.exists(videos_path):
        with open(videos_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data
    return None