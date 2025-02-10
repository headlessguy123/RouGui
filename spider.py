# -*- coding: utf-8 -*-


import json

def load_video():
    with open('videos.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data