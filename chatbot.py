# Meal tracker
# Auto-categorization (breakfast, lunch, dinner)
# Excercise tracker
# History Dashboard -- React
from fastapi import FastAPI, Request, BackgroundTasks
from google import genai
from google.genai import types
from datetime import datetime, date, timezone
import zoneinfo
import httpx
from typing import Optional
from pydantic import BaseModel, Field
from supabase import create_client, Client
import asyncio
from groq import Groq
import json
from dotenv import load_dotenv
import os

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
gemini_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

PENDING_LOGS = {}

ACTIVE_EXERCISE_SESSIONS = {}

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

USDA_API_KEY = os.getenv("USDA_API_KEY")

PROGRESSION_SCHEMA = {
    # PHASE 1
    "cuffed behind-the-back lateral raise": {1: {"min_reps": 10, "max_reps": 12, "increment": 2.5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 2.5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 2.5}},
    "cross-body lat pull-around": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "low incline smith machine press": {1: {"min_reps": 8, "max_reps": 10, "increment": 5}, 2: {"min_reps": 8, "max_reps": 10, "increment": 5}, 3: {"min_reps": 8, "max_reps": 10, "increment": 5}, 4: {"max_reps": 10, "increment": 5}},
    "chest-supported machine row": {1: {"min_reps": 8, "max_reps": 10, "increment": 10}, 2: {"min_reps": 8, "max_reps": 10, "increment": 10}, 3: {"min_reps": 8, "max_reps": 10, "increment": 10}},
    "overhead cable tricep extensions (bar)": {1: {"min_reps": 8, "max_reps": 10, "increment": 5}, 2: {"min_reps": 8, "max_reps": 10, "increment": 5}},
    "straight-bar lat prayer": {1: {"min_reps": 12, "max_reps": 15, "increment": 5}, 2: {"min_reps": 12, "max_reps": 15, "increment": 5}, 3: {"min_reps": 12, "max_reps": 15, "increment": 5}},
    "pec deck (with integrated partials)": {1: {"min_reps": 12, "max_reps": 15, "increment": 15}, 2: {"min_reps": 12, "max_reps": 15, "increment": 15}, 3: {"min_reps": 12, "max_reps": 15, "increment": 15}},

    "seated leg curl": {1: {"min_reps": 8, "max_reps": 10, "increment": 10}, 2: {"min_reps": 8, "max_reps": 10, "increment": 10}, 3: {"min_reps": 8, "max_reps": 10, "increment": 10}},
    "machine hip adduction": {1: {"min_reps": 10, "max_reps": 12, "increment": 10}, 2: {"min_reps": 10, "max_reps": 12, "increment": 10}, 3: {"min_reps": 10, "max_reps": 12, "increment": 10}},
    "hack squat": {1: {"min_reps": 4, "max_reps": 4, "increment": 5}, 2: {"min_reps": 6, "max_reps": 6, "increment": 5}, 3: {"min_reps": 8, "max_reps": 8, "increment": 5}},
    "leg extension": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "leg press calf press": {1: {"min_reps": 12, "max_reps": 15, "increment": 20}, 2: {"min_reps": 12, "max_reps": 15, "increment": 20}, 3: {"min_reps": 12, "max_reps": 15, "increment": 20}},

    "super-rom overhand cable row": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "machine shoulder press": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "assisted pull-up": {1: {"min_reps": 8, "max_reps": 10, "increment": 5}, 2: {"min_reps": 8, "max_reps": 10, "increment": 5}, 3: {"min_reps": 8, "max_reps": 10, "increment": 5}},
    "paused assisted dip": {1: {"min_reps": 8, "max_reps": 10, "increment": 5}, 2: {"min_reps": 8, "max_reps": 10, "increment": 5}, 3: {"min_reps": 8, "max_reps": 10, "increment": 5}},
    "inverse db zottman curl": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "super-rom db lateral raise": {1: {"min_reps": 12, "max_reps": 15, "increment": 5}, 2: {"min_reps": 12, "max_reps": 15, "increment": 5}, 3: {"min_reps": 12, "max_reps": 15, "increment": 5}},
    "cable reverse flye (mechanical dropset)": {1: {"min_reps": 5, "max_reps": 5, "increment": 5}, 2: {"min_reps": 4, "max_reps": 4, "increment": 5}, 3: {"min_reps": 3, "max_reps": 3, "increment": 5}},

    "lying leg curl": {1: {"min_reps": 8, "max_reps": 10, "increment": 5}, 2: {"min_reps": 8, "max_reps": 10, "increment": 5}, 3: {"min_reps": 8, "max_reps": 10, "increment": 5}},
    "leg press": {1: {"min_reps": 8, "max_reps": 8, "increment": 5}, 2: {"min_reps": 8, "max_reps": 8, "increment": 5}, 3: {"min_reps": 8, "max_reps": 8, "increment": 5}},
    "paused barbell rdl": {1: {"min_reps": 8, "max_reps": 8, "increment": 5}, 2: {"min_reps": 8, "max_reps": 8, "increment": 5}},
    "sissy squat": {1: {"min_reps": 10, "max_reps": 12, "increment": 0}, 2: {"min_reps": 10, "max_reps": 12, "increment": 0}, 3: {"min_reps": 10, "max_reps": 12, "increment": 0}},
    "standing calf raise": {1: {"min_reps": 10, "max_reps": 12, "increment": 15}, 2: {"min_reps": 10, "max_reps": 12, "increment": 15}, 3: {"min_reps": 10, "max_reps": 12, "increment": 15}},

    "bayesian cable curl": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "seated db french press": {1: {"min_reps": 10, "max_reps": 10, "increment": 5}, 2: {"min_reps": 10, "max_reps": 10, "increment": 5}, 3: {"min_reps": 10, "max_reps": 10, "increment": 5}},
    "bottom-2/3 constant tension preacher curl": {1: {"min_reps": 12, "max_reps": 15, "increment": 5}, 2: {"min_reps": 12, "max_reps": 15, "increment": 5}},
    "cable triceps kickback": {1: {"min_reps": 12, "max_reps": 15, "increment": 5}, 2: {"min_reps": 12, "max_reps": 15, "increment": 5}},
    "cable crunch": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},

    # PHASE 2
    "lat-focused cable row": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "low incline db press": {1: {"min_reps": 8, "max_reps": 10, "increment": 5}, 2: {"min_reps": 8, "max_reps": 10, "increment": 5}, 3: {"min_reps": 8, "max_reps": 10, "increment": 5}},
    "machine chest-supported row + kelso shrug": {1: {"min_reps": 8, "max_reps": 10, "increment": 5}, 2: {"min_reps": 8, "max_reps": 10, "increment": 5}, 3: {"min_reps": 8, "max_reps": 10, "increment": 5}},
    "bent-over cable pec flye (w/ integrated partials)": {1: {"min_reps": 12, "max_reps": 15, "increment": 5}, 2: {"min_reps": 12, "max_reps": 15, "increment": 5}, 3: {"min_reps": 12, "max_reps": 15, "increment": 5}},
    "1-arm lat pull-in": {1: {"min_reps": 12, "max_reps": 15, "increment": 5}, 2: {"min_reps": 12, "max_reps": 15, "increment": 5}},
    "dual-cable triceps press": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "smith machine squat": {1: {"min_reps": 4, "max_reps": 4, "increment": 5}, 2: {"min_reps": 6, "max_reps": 6, "increment": 5}, 3: {"min_reps": 8, "max_reps": 8, "increment": 5}},
    "db calf jumps": {1: {"min_reps": 12, "max_reps": 15, "increment": 5}, 2: {"min_reps": 12, "max_reps": 15, "increment": 5}, 3: {"min_reps": 12, "max_reps": 15, "increment": 5}},
    "dual-handle lat pulldown (mid-back + lats)": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "seated db shoulder press": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "decline machine chest press": {1: {"min_reps": 8, "max_reps": 10, "increment": 5}, 2: {"min_reps": 8, "max_reps": 10, "increment": 5}, 3: {"min_reps": 8, "max_reps": 10, "increment": 5}},
    "concentration cable curl": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "cross-body cable y-raise": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "rear delt 45 degrees cable flye": {1: {"min_reps": 12, "max_reps": 15, "increment": 5}, 2: {"min_reps": 12, "max_reps": 15, "increment": 5}, 3: {"min_reps": 12, "max_reps": 15, "increment": 5}},
    "smith machine reverse lunge": {1: {"min_reps": 8, "max_reps": 8, "increment": 5}, 2: {"min_reps": 8, "max_reps": 8, "increment": 5}, 3: {"min_reps": 8, "max_reps": 8, "increment": 5}},
    "glute-ham raise": {1: {"min_reps": 8, "max_reps": 8, "increment": 5}, 2: {"min_reps": 8, "max_reps": 8, "increment": 5}, 3: {"min_reps": 8, "max_reps": 8, "increment": 5}},
    "machine hip abduction": {1: {"min_reps": 10, "max_reps": 12, "increment": 10}, 2: {"min_reps": 10, "max_reps": 12, "increment": 10}, 3: {"min_reps": 10, "max_reps": 12, "increment": 10}},
    "slow-eccentric ez-bar skull crusher": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "slow-eccentric bayesian curl": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},
    "tricep diverging pressdown (long rope or 2 ropes)": {1: {"min_reps": 12, "max_reps": 15, "increment": 5}, 2: {"min_reps": 12, "max_reps": 15, "increment": 5}},
    "reverse grip cable curl": {1: {"min_reps": 12, "max_reps": 15, "increment": 5}, 2: {"min_reps": 12, "max_reps": 15, "increment": 5}},
    "roman chair leg raise": {1: {"min_reps": 10, "max_reps": 12, "increment": 5}, 2: {"min_reps": 10, "max_reps": 12, "increment": 5}, 3: {"min_reps": 10, "max_reps": 12, "increment": 5}},

    # WEAK POINTS
    "machine lateral raise": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "dumbbell lateral raise": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "smith machine shoulder press": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "standing dumbbell arnold press": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "cable lat prayer": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "dumbbell lat pullover": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "machine lat pullover": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "elbows-in 1-arm db row": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "half-kneeling 1-arm lat pulldown": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "reverse nordics": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "single-leg leg press": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "cable hip abduction": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "lateral band walk": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "barbell hip thrust": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "single-leg db hip thrust": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "low incline db flye": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "low-to-high cable crossover": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "chest press machine (incline if upper pecs are lagging, flat if entire chest is lagging)": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "dumbbell chest press (incline if upper pecs are lagging, flat if entire chest is lagging)": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "plate loaded neck curls": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "head harness neck extension": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
    "plate-loaded neck extension": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}, 2: {"min_reps": 8, "max_reps": 12, "increment": 5}, 3: {"min_reps": 8, "max_reps": 12, "increment": 5}},
}


EXERCISE_COACHING = {
    # PHASE 1
    "cuffed behind-the-back lateral raise": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Raise cables up/out in a 'Y' motion. Connect with middle delts. **Last Set: Myo-reps!**"},
    "cross-body lat pull-around": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Wrist/cable aligned in a straight line. Deep lat stretch at top. **Last Set: Long-length Partials.**"},
    "low incline smith machine press": {"warmup_sets": 2, "reps": "8-10 reps", "advice": "~15° incline. 1s pause on chest. **Last Set: 30s Pec Static Stretch.**"},
    "chest-supported machine row": {"warmup_sets": 1, "reps": "8-10 reps", "advice": "Flare elbows ~45° and squeeze blades hard at top. **Last Set: Long-length Partials.**"},
    "overhead cable tricep extensions (bar)": {"warmup_sets": 1, "reps": "8-10 reps", "advice": "Nasty stretch on negative, 1s pause at bottom. **Last Set: Dropset.**"},
    "straight-bar lat prayer": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "Lean forward for big lat stretch at top, stand upright at bottom. **Last Set: Long-length Partials.**"},
    "pec deck (with integrated partials)": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "**Integrated Partials:** Alternate 1 full-ROM rep with 1 half-ROM rep in stretched position."},

    "seated leg curl": {"warmup_sets": 1, "reps": "8-10 reps", "advice": "Lean forward over machine for maximum hamstring stretch."},
    "machine hip adduction": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Mind-muscle connection with inner thighs. Push hard!"},
    "hack squat": {"warmup_sets": 3, "reps": "4, 6, 8 reps (Reverse Pyramid)", "advice": "Reverse Pyramid: Set 1 heaviest (4 reps). Set 2 drop ~10-15% (6 reps). Set 3 drop ~10-15% (8 reps)."},
    "leg extension": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Pull butt down into seat. 2-3s negative. **Last Set: Long-length Partials.**"},
    "leg press calf press": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "1-2s pause at bottom. Roll ankles on balls of feet. **Last Set: 30s Calf Static Stretch.**"},

    "super-rom overhand cable row": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Wide grip pulldown bar. Lean forward on negative, upright at finish."},
    "machine shoulder press": {"warmup_sets": 2, "reps": "10-12 reps", "advice": "Elbows break 90°. Smooth, controlled reps. **Last Set: Dropset.**"},
    "assisted pull-up": {"warmup_sets": 1, "reps": "8-10 reps", "advice": "Slow 2-3s negative. 0.5-1s pause at bottom. **Last Set: Long-length Partials.**"},
    "paused assisted dip": {"warmup_sets": 2, "reps": "8-10 reps", "advice": "Slow 2-3s negative. 1-2s pause at bottom. Break 90° elbow angle."},
    "inverse db zottman curl": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Hammer curl on positive, palms-up grip on negative."},
    "super-rom db lateral raise": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "Hands overhead. Squeeze upper traps at top. Point thumbs up if shoulder hurts."},
    "cable reverse fly (mechanical dropset)": {"warmup_sets": 0, "reps": "5, 4, 3+ reps", "advice": "**Mechanical Dropset:** 3 steps back (5 reps) -> 1 step fwd (4 reps) -> 1 step fwd (3+ reps). No rest!"},

    "lying leg curl": {"warmup_sets": 1, "reps": "8-10 reps", "advice": "Big stretch at bottom. Keep hips down. **Last Set: Long-length Partials.**"},
    "leg press": {"warmup_sets": 2, "reps": "8 reps", "advice": "Feet low for quad focus. Deep stretch with slight pause at bottom."},
    "paused barbell rdl": {"warmup_sets": 2, "reps": "8 reps", "advice": "Low RPE (~6-7). 1s pause at bottom. Stop 75% to lockout to keep tension."},
    "sissy squat": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Knees forward past toes. Push hard!"},
    "standing calf raise": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "1-2s pause at bottom. **Last Set: 30s Calf Static Stretch.**"},

    "bayesian cable curl": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Start with weaker arm if imbalanced. Take weaker arm to RPE 9-10, then match reps with other arm. **Last Set: Long-length Partials.**"},
    "seated db french press": {"warmup_sets": 1, "reps": "10 reps", "advice": "Palms under top of dumbbell. Deep stretch at bottom. Avoid pausing at the top of each rep."},
    "bottom-2/3 constant tension preacher curl": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "Stay in bottom 2/3. No pausing at top or bottom—constant tension!"},
    "cable triceps kickback": {"warmup_sets": 0, "reps": "12-15 reps", "advice": "Upright or bent over. At full squeeze, keep shoulder positioned behind torso."},
    "cable crunch": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Round your lower back as you crunch. Maintain mind-muscle connection with your 6-pack."},

    # PHASE 2
    "lat-focused cable row": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep elbows tucked close to your sides to bias the lats."},
    "low incline db press": {"warmup_sets": 2, "reps": "8-10 reps", "advice": "Set the bench at a 15 degree incline. Do a slight elbow tuck on the negative then flare as you push (assuming this doesn't bother your shoulders). Nice smooth reps here. No pausing at the top or bottom: constant tension on the pecs."},
    "chest-supported t-bar row + kelso shrug": {"warmup_sets": 2, "reps": "8-10 reps", "advice": "Do 8-10 reps as a normal T-Bar row, driving your elbows back at roughly 45 degrees and squeezing your shoulder blades together. Without resting, do another 406 reps as Kelso Shrugs (just squeeze your shoulder blades together without rowing all the way back with your arms)"},
    "bent-over cable pec flye (w/ integrated partials)": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "Lean forward until your torso is parallel with the floor, flye straight out and down toward the floor. Stretch and squeeze the pecs. Stay locked in."},
    "1-arm lat pull-in": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "Pull the cable in from the side. Keep a mind-muscle connection with your lats and try to prevent your biceps from taking over. Palpate (feel) your lats with your other hand if that helps you connect with them better."},
    "dual-cable triceps press": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Hold the cables without a handle and get them into position just above your shoulders (around chin level). Press the weight forward (straight out in front of you), not up overhead like in a standard overhead triceps extension."},
    "smith machine squat": {"warmup_sets": 2, "reps": "4, 6, 8 reps", "advice": "We're using a reverse pyramid on this excercise. Warm-up as usual to your first working set for 4 reps. This first set will be your heaviest set. Then for set 2, drop the weight back 10-15 percent and do 6 reps. Then for set 3, drop the weight back another 10-15 percent and do 8 reps."},
    "db calf jumps": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "Hold a dumbbell and perform a jumping motion without actually leaving the floor, using a slight knee bend, but mostly relying on your calves/ankles to drive the jump. I believe I built a lot of calf mass by doing jump rope; these are meant to provide a similar stimulus, but with more tension."},
    "dual-handle lat pulldown (mid-back + lats)": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Lean back by 15 degrees and drive your elbows down as you squeeze your shoulder blades together. This should feel like a mix of lats and mid-traps."},
    "seated db shoulder press": {"warmup_sets": 2, "reps": "10-12 reps", "advice": "Slightly rotate the dumbbells in on the negative and flare your elbows out as you push."},
    "decline machine chest press": {"warmup_sets": 2, "reps": "8-10 reps", "advice": "Feel your pecs stretching apart on the negative. Mind-muscle connection with lower pecs."},
    "concentration cable curl": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Place your working elbow against your knee and perform strict form curls."},
    "cross-body cable y-raise": {"warmup_sets": 3, "reps": "10-12 reps", "advice": "Think about drawing a sword as you do the positive. Sweep your arm up, out, and across your body. It may take a few weeks to get used to these if you haven't done them before, but once they click, they really click."},
    "rear dent 45 degrees cable flye": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "Pull with one arm at a time, bracing with your non-working hand against the machine. Try to align your arm and the cable in a straight line at the bottom of the fly."},
    "smith machine reverse lunge": {"warmup_sets": 2, "reps": "8 reps", "advice": "Set one leg back on the negative and then drive the weight up using your front leg. Try to minimize assistance from your back leg."},
    "glute-ham raise": {"warmup_sets": 2, "reps": "8 reps", "advice": "Cut out the top 25 percent of the ROM, where there will be minimal tension on the hamstrings. Control the negative and squeeze your hamstrings to pull yourself up."},
    "machine hip abduction": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Mind-muscle connection with inner thighs. Push hard!"},
    "slow-eccentric ez-bar skull crusher": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Use a 3-4 second negative. Arc the EZ-bar slightly back behind your head. When you extend, keep the bar behind your eye line. Use the inside (closer) grip option and allow the elbows to flare to a degree that feels comfortable."},
    "slow-eccentric bayesian curl": {"warmup_sets": 1, "reps": "10-12 reps", "advice": "Use a 3-4 second negative and a slight pause at the bottom of each rep to emphasize stretching your biceps **Last Set: Long-length partials (on all reps of the last set)**"},
    "triceps diverging pressdown (long rope or 2 ropes)": {"warmup_sets": 1, "reps": "12-15 reps", "advice": "Use two long reps or one long rope. Lean slightly forward, flare your elbows slightly out and keep your arms back in line with your torso. Then do triceps pressdowns, getting a full, big squeeze at the bottom."},
    "reverse grip cable curl": {"warmup_sets": 0, "reps": "12-15 reps", "advice": "Grab a cable bar with your palms facing down and perform curls. These will work the back of your forearm, brachialis and biceps."},
    "roman chair leg raise": {"warmup_sets": 0, "reps": "10-20 reps", "advice": "Allow your lower back to round as you curl your legs up. 10-20 reps is a broad range on purpose: just go until you hit RPE 9-10 (0-1 reps shy of failure) with controlled form."},

    # Weak points
    "machine lateral raise": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Focus on pushing the weight out rather than up. Keep a slight bend in the elbows."},
    "dumbbell lateral raise": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Slight lean forward, lead with the elbows. Stop at shoulder height."},
    "smith machine shoulder press": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Set bench to a high incline. Lower bar with control to chin/upper chest level."},
    "standing dumbbell arnold press": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Start with palms facing you, rotate palms forward as you press overhead."},
    "cable lat prayer": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Lean forward for big lat stretch at top, stand upright at bottom. **Last Set: Long-length Partials.**"},
    "dumbbell lat pullover": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep elbows slightly bent. Feel the stretch in your lats, not your chest."},
    "machine lat pullover": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Drive elbows down and back. Deep stretch at the top."},
    "elbows-in 1-arm db row": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Pull dumbbell toward your hip. Squeeze the lat at the top."},
    "half-kneeling 1-arm lat pulldown": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Kneel on the same side you are pulling with. Drive elbow straight down."},
    "reverse nordics": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep a straight line from knees to shoulders. Control the descent into a deep quad stretch."},
    "single-leg leg press": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Place foot lower on the platform for quad focus. Avoid completely locking out the knee."},
    "cable hip abduction": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep torso stationary. Pull the cable away using only your glutes."},
    "lateral band walk": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep tension on the band at all times. Do not drag the trailing foot."},
    "barbell hip thrust": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Tuck your chin, drive through the heels, and squeeze glutes hard at lockout."},
    "single-leg dumbbell hip thrust": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep your core braced and hinge at the hips. Push through the working heel."},
    "low incline db flye": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Slight bend in elbows. Maximize the stretch at the bottom without shoulder pain."},
    "low-to-high cable crossover": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Pull from low to high to target the upper pecs. Squeeze at the top."},
    "chest press machine (incline if upper pecs lagging, flat if entire chest is lagging)": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep chest up and shoulders retracted. Push smoothly through the palms."},
    "dumbbell chest press (incline if upper pecs lagging, flat if entire chest is lagging)": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Control the negative. Get a deep stretch at the bottom before pressing up."},
    "plate-loaded neck curls": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Use slow, controlled reps. Tuck chin to chest at the top."},
    "head harness neck extension": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Do not jerk the weight. Extend smoothly to activate the back of the neck."},
    "plate-loaded neck extension": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Maintain strict control. Focus on the stretch and contraction of the neck extensors."},
}

EXERCISE_COACHING.update({
    # Weak points
    "machine lateral raise": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Focus on pushing the weight out rather than up. Keep a slight bend in the elbows."},
    "dumbbell lateral raise": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Slight lean forward, lead with the elbows. Stop at shoulder height."},
    "smith machine shoulder press": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Set bench to a high incline. Lower bar with control to chin/upper chest level."},
    "standing dumbbell arnold press": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Start with palms facing you, rotate palms forward as you press overhead."},
    "cable lat prayer": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Lean forward for big lat stretch at top, stand upright at bottom. **Last Set: Long-length Partials.**"},
    "dumbbell lat pullover": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep elbows slightly bent. Feel the stretch in your lats, not your chest."},
    "machine lat pullover": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Drive elbows down and back. Deep stretch at the top."},
    "elbows-in 1-arm db row": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Pull dumbbell toward your hip. Squeeze the lat at the top."},
    "half-kneeling 1-arm lat pulldown": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Kneel on the same side you are pulling with. Drive elbow straight down."},
    "reverse nordics": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep a straight line from knees to shoulders. Control the descent into a deep quad stretch."},
    "single-leg leg press": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Place foot lower on the platform for quad focus. Avoid completely locking out the knee."},
    "cable hip abduction": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep torso stationary. Pull the cable away using only your glutes."},
    "lateral band walk": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep tension on the band at all times. Do not drag the trailing foot."},
    "barbell hip thrust": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Tuck your chin, drive through the heels, and squeeze glutes hard at lockout."},
    "single-leg dumbbell hip thrust": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep your core braced and hinge at the hips. Push through the working heel."},
    "low incline db flye": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Slight bend in elbows. Maximize the stretch at the bottom without shoulder pain."},
    "low-to-high cable crossover": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Pull from low to high to target the upper pecs. Squeeze at the top."},
    "chest press machine (incline if upper pecs lagging)": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Keep chest up and shoulders retracted. Push smoothly through the palms."},
    "dumbbell chest press (incline if upper pecs lagging)": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Control the negative. Get a deep stretch at the bottom before pressing up."},
    "plate-loaded neck curls": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Use slow, controlled reps. Tuck chin to chest at the top."},
    "head harness neck extension": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Do not jerk the weight. Extend smoothly to activate the back of the neck."},
    "plate-loaded neck extension": {"warmup_sets": 1, "reps": "8-12 reps", "advice": "Maintain strict control. Focus on the stretch and contraction of the neck extensors."},
})

WEAK_POINTS_TABLE = {
    "shoulders": {
        "title": "Shoulders",
        "ex1": ["Cuffed Behind-The-Back Lateral Raise", "Machine Lateral Raise", "Dumbbell Lateral Raise"],
        "ex2": ["Machine Shoulder Press", "Smith Machine Shoulder Press", "Standing Dumbbell Arnold Press"]
    },
    "lats": {
        "title": "Lats ('Back Width')",
        "ex1": ["Cable Lat Prayer", "Dumbbell Lat Pullover", "Machine Lat Pullover"],
        "ex2": ["Lat-Focused Cable Row", "Elbows-In 1-Arm DB Row", "Half-Kneeling 1-Arm Lat Pulldown"]
    },
    "quads": {
        "title": "Quads",
        "ex1": ["Leg Extension", "Reverse Nordics"],
        "ex2": ["Single-Leg Leg Press", "Sissy Squat"]
    },
    "glutes": {
        "title": "Glutes",
        "ex1": ["Machine Hip Abduction", "Cable Hip Abduction", "Lateral Band Walk"],
        "ex2": ["Barbell Hip Thrust", "Single-Leg Dumbbell Hip Thrust"]
    },
    "chest": {
        "title": "Chest",
        "ex1": ["Low Incline DB Flye", "Low-To-High Cable Crossover"],
        "ex2": ["Chest Press Machine (incline if upper pecs lagging)", "Dumbbell Chest Press (incline if upper pecs lagging)"]
    },
    "neck": {
        "title": "Neck",
        "ex1": ["Plate-Loaded Neck Curls"],
        "ex2": ["Head Harness Neck Extension", "Plate-Loaded Neck Extension"]
    },
    "hamstrings": "There is a lot of hamstrings volume in this program. If they are a weak point, simply focus on executing the listed exercises with your best effort rather than adding more volume.",
    "calves": "Focus on execution first. Ensure you are pausing at the bottom. Feel free to sprinkle in 1-2 extra sets per exercise if they are a major priority.",
    "mid-back": "There is a lot of mid-back volume. Focus on execution rather than adding volume. Squeeze blades together on the positive, feel the back pull apart on the negative.",
    "upper traps": "Shouldn't require high volume. Focus on execution. Feel free to sprinkle in 1-2 extra sets per exercise if they are a major priority.",
    "abs": "Diet is mainly responsible for abs. Focus on execution of crunches and leg raises. Feel free to sprinkle in 1-2 extra sets if a major priority."
}


class FoodStructure(BaseModel):
    food_name: str
    calories: float
    protein: float
    carbs: float
    fat: float
    extracted_date: Optional[str] = Field(default=None)
    extracted_meal_type: Optional[str] = Field(default=None)


class WorkoutStructure(BaseModel):
    exercise_name: str
    weight: float = 0.0
    reps: int = 0
    is_warmup: bool = Field(
        default=False, description="True if the user indicates this is a warm-up set.")


def define_meal() -> str:
    central_tz = zoneinfo.ZoneInfo("America/Chicago")
    current_hour = datetime.now(central_tz).hour

    # sample times
    if 5 <= current_hour < 11:
        return "breakfast"
    elif 11 <= current_hour < 14:
        return "lunch"
    elif 19 <= current_hour < 22:
        return "dinner"
    else:
        return "snack"


def generate_warmup_guide(warmup_count: int, working_weight: float) -> str:
    if warmup_count == 0:
        return "• *No warm-up sets required—jump straight into Working Set 1!*"
    elif warmup_count == 1:
        w1 = round((working_weight * 0.60) / 5) * 5
        return f"• Warm-Up Set 1: **{w1} lbs** × 6-10 reps (~60%)"
    elif warmup_count == 2:
        w1 = round((working_weight * 0.50) / 5) * 5
        w2 = round((working_weight * 0.70) / 5) * 5
        return f"• Warm-Up Set 1: **{w1} lbs** × 6-10 reps (~50%)\n• Warm-Up Set 2: **{w2} lbs** × 4-6 reps (~70%)"
    elif warmup_count >= 3:
        w1 = round((working_weight * 0.45) / 5) * 5
        w2 = round((working_weight * 0.65) / 5) * 5
        w3 = round((working_weight * 0.85) / 5) * 5
        return f"• Warm-Up Set 1: **{w1} lbs** × 6-10 reps (~45%)\n• Warm-Up Set 2: **{w2} lbs** × 4-6 reps (~65%)\n• Warm-Up Set 3: **{w3} lbs** × 3-4 reps (~85%)"


async def send_telegram_reply(chat_id: int, text: str, reply_markup: dict = None):
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    async with httpx.AsyncClient() as http_client:
        try:
            resp = await http_client.post(TELEGRAM_API_URL, json=payload)
            resp.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                print(f"Telegram Markdown parsing failed. Retrying as plain text.")
                payload.pop("parse_mode", None)
                retry_resp = await http_client.post(TELEGRAM_API_URL, json=payload)
                retry_resp.raise_for_status()
            else:
                raise e


async def get_usda_macros(food_query: str):
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_API_KEY}&query={
        food_query}&pageSize=3&dataType=Foundation,Survey%20(FNDDS),Branded,SR%20Legacy"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            data = response.json()
            options = []
            if data.get('foods'):
                food = data['foods'][0]
                # Extract nutrients (protein, fat, carbs)
                calories = next(
                    (n['value'] for n in food['foodNutrients'] if 'Energy' in n['nutrientName']), 0)
                protein = next(
                    (n['value'] for n in food['foodNutrients'] if 'Protein' in n['nutrientName']), 0)
                carbs = next((n['value'] for n in food['foodNutrients']
                             if 'Carbohydrate' in n['nutrientName']), 0)
                fat = next((n['value'] for n in food['foodNutrients']
                           if 'Total lipid' in n['nutrientName']), 0)
                options.append({
                    "food_name": food['description'],
                    "calories": int(calories),
                    "protein": int(protein),
                    "carbs": int(carbs),
                    "fat": int(fat)
                })
                return options
        except Exception as e:
            print(f"USDA API Error: {e}")
            return []
    return []


async def delayed_rest_reminder(chat_id: int, exercise_name: str, next_set: int, target_desc: str):
    # 3 minute timer
    await asyncio.sleep(180)

    today_str = date.today().isoformat()
    existing_sets = supabase.table("exercise_logs") \
        .select("id") \
        .eq("exercise_name", exercise_name) \
        .eq("is_warmup", False) \
        .gte("created_at", today_str) \
        .execute()

    if len(existing_sets.data) >= next_set:
        return

    reminder = f"**3-Minute Rest Over!**\nTime for **Set {
        next_set}** of *{exercise_name.title()}*.\n Target: {target_desc}"
    async with httpx.AsyncClient() as http_client:
        await http_client.post(TELEGRAM_API_URL, json={
            "chat_id": chat_id, "text": reminder, "parse_mode": "Markdown"
        })


async def process_and_save_meal(chat_id: int, food_data: FoodStructure):
    central_tz = zoneinfo.ZoneInfo("America/Chicago")
    meal_type = food_data.extracted_meal_type if food_data.extracted_meal_type else define_meal()

    insert_payload = {
        "meal_type": meal_type,
        "food_name": food_data.food_name,
        "calories": food_data.calories,
        "protein": food_data.protein,
        "carbs": food_data.carbs,
        "fat": food_data.fat,
        "created_at": datetime.now(central_tz).isoformat()
    }

    if food_data.extracted_date:
        insert_payload["created_at"] = f"{
            food_data.extracted_date}T12:00:00-05:00"

    supabase.table("food_logs").insert(insert_payload).execute()

    today_str = date.today().isoformat()
    daily_logs = supabase.table("food_logs") \
        .select("calories, protein, carbs, fat") \
        .gte("created_at", today_str) \
        .execute()

    total_cal = sum(log['calories'] for log in daily_logs.data)
    total_pro = sum(log['protein'] for log in daily_logs.data)
    total_carb = sum(log['carbs'] for log in daily_logs.data)
    total_fat = sum(log['fat'] for log in daily_logs.data)

    profile = supabase.table("user_profiles").select(
        "*").eq("chat_id", chat_id).execute()

    daily_summary = ""
    if profile.data:
        target_pro = profile.data[0]['target_protein']
        target_cal = profile.data[0]['target_calories']
        target_fat = profile.data[0]['target_fat']
        goal = profile.data[0]['goal']

        rem_pro = target_pro - total_pro
        rem_cal = target_cal - total_cal

        advice_prompt = (
            f"I am focusing on {goal}. I just ate {food_data.food_name}. "
            f"My daily totals are now: {total_pro}g protein, {
                total_fat}g fat, {total_cal} cals. "
            f"I have {rem_pro}g of protein and {
                rem_cal} calories left to hit my targets. "
            f"Give me exactly ONE short, punchy sentence of advice. "
            f"If protein is lagging, suggest something like a scoop of Ascent Native Fuel Whey or a lean meat. "
            f"If fat or calories are getting too high, tell me to dial it back."
        )

        advice_res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": advice_prompt}],
            model="openai/gpt-oss-20b"
        )
        coach_advice = advice_res.choices[0].message.content.strip()

        daily_summary = (
            f"\n\n **Daily Status:**\n"
            f" Protein: **{total_pro}g** / {
                target_pro}g *(Need {rem_pro}g more)*\n"
            f" Calories: **{total_cal}** / {round(target_cal)}\n\n"
            f" *{coach_advice}*"
        )
    else:
        daily_summary = "\n\n *Profile not found in database. Add your baseline to get macro coaching!*"

    reply = (
        f" **Logged for {meal_type.capitalize()}!**\n"
        f" *{food_data.food_name.title()}*\n"
        f" **{food_data.calories} kcal** | {food_data.protein}g P | {
            food_data.carbs}g C | {food_data.fat}g F"
        f"{daily_summary}"
    )

    await send_telegram_reply(chat_id, reply)


@app.post("/api/v1/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
    except Exception as e:
        # 2. Return a 400 error if JSON is malformed
        print(f"Error parsing JSON: {e}")
        return {"status": "error", "message": "Invalid JSON"}

    try:
        if "callback_query" in payload:
            callback = payload["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            callback_data = callback["data"]

            # 1. HANDLE WEAK POINTS FIRST (Does not require PENDING_LOGS)
            if callback_data.startswith("wp_"):
                wp_key = callback_data.replace("wp_", "")
                if wp_key in WEAK_POINTS_TABLE:
                    wp_data = WEAK_POINTS_TABLE[wp_key]
                    if isinstance(wp_data, str):
                        reply_text = f"**{wp_key.title()
                                          } Advice:**\n\n{wp_data}"
                    else:
                        ex1_list = "\n".join(
                            [f"• {ex}" for ex in wp_data['ex1']])
                        ex2_list = "\n".join(
                            [f"• {ex}" for ex in wp_data['ex2']])
                        reply_text = (
                            f"**{wp_data['title']} Weak Point Options**\n\n"
                            f"**Exercise #1 Options (Pick One):**\n{
                                ex1_list}\n\n"
                            f"**Exercise #2 Options (Pick One):**\n{
                                ex2_list}\n\n"
                            f"*Note: Do not do all of them in one day!*"
                        )
                    async with httpx.AsyncClient() as http_client:
                        await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", json={
                            "chat_id": chat_id,
                            "message_id": callback["message"]["message_id"],
                            "text": reply_text,
                            "parse_mode": "Markdown",
                            "reply_markup": callback["message"].get("reply_markup")
                        })
                return {"status": "success"}

            # 2. HANDLE PHASE WORKOUT CHECKLIST BUTTONS (Does not require PENDING_LOGS)
            workout_prefixes = ["p1u1_", "p1u2_", "p1l1_", "p1l2_",
                                "p1a_", "p2u1_", "p2u2_", "p2l1_", "p2l2_", "p2a_"]
            if any(callback_data.startswith(p) for p in workout_prefixes):
                raw_slug = callback_data
                for prefix in workout_prefixes:
                    if raw_slug.startswith(prefix):
                        raw_slug = raw_slug.replace(prefix, "")
                        break

                matched_exercise = None
                for ex in PROGRESSION_SCHEMA.keys():
                    if ex.replace(" ", "-").replace("/", "-").lower() == raw_slug.lower():
                        matched_exercise = ex
                        break
                if matched_exercise:
                    exercise_name = matched_exercise
                else:
                    exercise_name = raw_slug.replace("-", " ").lower().strip()

                ACTIVE_EXERCISE_SESSIONS[chat_id] = exercise_name

                today_str = date.today().isoformat()
                coaching_data = EXERCISE_COACHING.get(exercise_name, {
                                                      "reps": "8-12 reps", "advice": "Normal working set to hypertrophy depth."})
                intensity_advice = coaching_data.get(
                    "advice", "Normal working set to hypertrophy depth.")
                warmup_count = coaching_data.get("warmup_sets", 0)

                ex_schema = PROGRESSION_SCHEMA.get(exercise_name, {})
                schema_text_lines = []
                for s, targets in ex_schema.items():
                    schema_text_lines.append(f"• Working Set {s}: {
                                             targets['max_reps']} reps (+{targets['increment']} lbs incr.)")
                schema_text = "\n".join(
                    schema_text_lines) if schema_text_lines else "• Normal working progression"

                # Fetch the most recent past logs for this exercise from Supabase
                history = supabase.table("exercise_logs") \
                    .select("weight, reps, set_number, created_at") \
                    .eq("exercise_name", exercise_name) \
                    .lt("created_at", today_str) \
                    .order("created_at", desc=True) \
                    .limit(25) \
                    .execute()

                if not history.data:
                    reply_text = f"**No history found for {exercise_name.title()}!**\nStart with a light warm-up weight to establish your baseline today.\n\n**Progression Schema:**\n{
                        schema_text}\n\n *Technique Cues:* {intensity_advice}"
                else:
                    last_date = history.data[0]['created_at'][:10]
                    last_session = [
                        row for row in history.data if row['created_at'].startswith(last_date)]

                    history_text = "\n".join([f"• Set {row['set_number']}: {row['weight']} lbs × {
                                             row['reps']} reps" for row in sorted(last_session, key=lambda x: x['set_number'])])

                    set_1_targets = ex_schema.get(
                        1, {"min_reps": 8, "max_reps": 12, "increment": 5})
                    target_max_reps = set_1_targets.get('max_reps', 12)
                    target_min_reps = set_1_targets.get('min_reps', 8)
                    increment = set_1_targets.get('increment', 5)

                    upper_1_anchors = [
                        "low incline smith machine press", "low incline db press"]
                    end_of_today = f"{today_str}T23:59:59"

                    upper_1_logs = supabase.table("exercise_logs") \
                        .select("created_at") \
                        .in_("exercise_name", upper_1_anchors) \
                        .lte("created_at", end_of_today) \
                        .execute()

                    unique_weeks = len(set(
                        row['created_at'][:10] for row in upper_1_logs.data)) if upper_1_logs.data else 1
                    if unique_weeks == 0:
                        unique_weeks = 1

                    is_deload_week = (unique_weeks % 5 == 0)

                    successful_sets = [
                        s for s in last_session if s['reps'] >= target_min_reps]

                    if successful_sets:
                        best_set = max(successful_sets,
                                       key=lambda x: x['weight'])
                        target_working_weight = best_set['weight']

                        if best_set['reps'] >= target_max_reps:
                            target_working_weight += increment
                            rec_text = f"You crushed **{target_max_reps} reps** at {best_set['weight']} lbs last time! Load up **{
                                target_working_weight} lbs** for Set 1 today and aim for **{target_max_reps} reps**!"
                        else:
                            rec_text = f"Your heaviest successful set last time was **{target_working_weight} lbs** for {
                                best_set['reps']} reps. Stick with **{target_working_weight} lbs** for Set 1 today and push for **{target_max_reps} reps**!"
                    else:
                        heaviest_set = max(
                            last_session, key=lambda x: x['weight'])
                        target_working_weight = max(
                            0, heaviest_set['weight'] - increment)
                        rec_text = f"You fell below the {target_min_reps} rep floor last time ({heaviest_set['weight']} lbs × {
                            heaviest_set['reps']} reps). Drop weight to **{target_working_weight} lbs** for Working Set 1 today to stay in the target zone."

                    if is_deload_week:
                        schema_text = " **SEMI-DELOAD WEEK (Week 5)** \n*Avoid failure (RPE 7-8) and drop 1 total working set today to promote recovery! Next week starts Next Block so Update Excercises*\n\n" + schema_text

                    warmup_guide = generate_warmup_guide(
                        warmup_count, target_working_weight)

                    reply_text = f"**Last Session: {exercise_name.title()}** ({last_date})\n\n{history_text}\n\n **Target Working Weight:** {rec_text}\n\n **Recommended Warm-Up Pyramid ({
                        warmup_count} sets): **\n{warmup_guide}\n\n **Working Progression Schema:**\n{schema_text}\n\n *Technique Cues:* {intensity_advice}"

                async with httpx.AsyncClient() as http_client:
                    await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", json={
                        "chat_id": chat_id,
                        "message_id": callback["message"]["message_id"],
                        "text": reply_text,
                        "parse_mode": "Markdown",
                        "reply_markup": callback["message"].get("reply_markup")
                    })
                return {"status": "success"}

            # 3. MEAL LOGGING GUARD (Everything below this requires PENDING_LOGS)
            if chat_id not in PENDING_LOGS:
                await send_telegram_reply(chat_id, "Session expired. Please re-enter your meal.")
                return {"status": "success"}

            pending_data = PENDING_LOGS[chat_id]
            raw_text = pending_data["raw_text"]

            if callback_data.startswith("usda_"):
                index = int(callback_data.split("_")[1])
                selected_food = pending_data["usda_options"][index]

                schema_string = json.dumps(FoodStructure.model_json_schema())
                system_instructions = (
                    f"Return a flat JSON object matching this schema: {
                        schema_string}. "
                    f"The user ate: '{raw_text}'. "
                    f"Use this EXACT baseline data to calculate the final macros based on their portion: "
                    f"{json.dumps(
                        selected_food)}. Extract 'extracted_date' and 'extracted_meal_type' if present."
                )

                response = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instructions}],
                    model="openai/gpt-oss-120b",
                    response_format={"type": "json_object"}
                )
                response_dict = json.loads(response.choices[0].message.content)
                clean_dict = {k: v for k,
                              v in response_dict.items() if v is not None}
                food_data = FoodStructure.model_validate(clean_dict)
            elif callback_data == "ai_fallback":
                schema_string = json.dumps(FoodStructure.model_json_schema())
                system_instructions = f"You are an expert nutritionist and precise calorie calculator. The user will provide a meal, often with specific quantities, measurements, and brands. You MUST calculate the macros step-by-step: identify each distinct ingredient, recall its specific nutritional values for the exact quantity/measurement provided, and sum the total calories, protein, carbs, and fat together. Return ONLY a valid JSON object matching this schema exactly: {
                    schema_string}. CRITICAL: Return a flat JSON object. Do NOT wrap your response in a 'properties' key. IMPORTANT: If the user specifies a past date (like 6/10/26) or a meal type (like lunch), extract them into 'extracted_date' (format as YYYY-MM-DD) and 'extracted_meal_type'."

                response = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": f"Analyze this meal text: '{raw_text}'"}
                    ],
                    model="openai/gpt-oss-120b",
                    response_format={"type": "json_object"}
                )
                response_dict = json.loads(response.choices[0].message.content)
                clean_dict = {k: v for k,
                              v in response_dict.items() if v is not None}
                food_data = FoodStructure.model_validate(clean_dict)
            elif callback_data.startswith("wp_"):
                wp_key = callback_data.replace("wp_", "")
                wp_data = WEAK_POINTS_TABLE.get(wp_key)

                if isinstance(wp_data, str):
                    reply_text = f"**{wp_key.title()} Advice:**\n\n{wp_data}"
                else:
                    # For muscle groups with specific Ex 1 & Ex 2 options
                    ex1_list = "\n".join([f"• {ex}" for ex in wp_data['ex1']])
                    ex2_list = "\n".join([f"• {ex}" for ex in wp_data['ex2']])

                    reply_text = (
                        f"**{wp_data['title']} Weak Point Options**\n\n"
                        f"**Exercise #1 Options (Pick One):**\n{ex1_list}\n\n"
                        f"**Exercise #2 Options (Pick One):**\n{ex2_list}\n\n"
                        f"*Note: Do not do all of them in one day!*"
                    )

                async with httpx.AsyncClient() as http_client:
                    await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", json={
                        "chat_id": chat_id,
                        "message_id": callback["message"]["message_id"],
                        "text": reply_text,
                        "parse_mode": "Markdown"
                    })
                return {"status": "success"}

            del PENDING_LOGS[chat_id]
            await process_and_save_meal(chat_id, food_data)

            async with httpx.AsyncClient() as http_client:
                await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup", json={
                    "chat_id": chat_id,
                    "message_id": callback["message"]["message_id"],
                    "reply_markup": {"inline_keyboard": []}
                })

            return {"status": "success"}

        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_text = message.get("text", "").strip()

        if not user_text or not chat_id:
            return {"status": "ignored"}

        if user_text == "/start":
            welcome_message = "Welcome to the workout or meal tracker: Are you logging a workout or meal? If meal start message with '/meal' If workout start message with '/upper' or '/lower' If updating profile with updated BMR information start message with '/profile'"
            await send_telegram_reply(chat_id, welcome_message)
            return {"status": "success"}
        if user_text.lower() == ("/phase_1_upper_1"):
            # phase_1_upper_1_menu = (
            #     "**JEFF NIPPARD PHASE 1 UPPER DAY 1 CHECKLIST**\n\n"
            #     "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            #     "**cuffed behind-the-back Lateral Raise** (10-12 reps) (3 sets)\n\n"
            #     "**cross-body lat pull-around** (10-12 reps) (3 sets)\n\n"
            #     "**low incline smith machine press** (8-10 reps) (4 sets)\n\n"
            #     "**chest-supported machine row** (8-10 reps) (3 sets)\n\n"
            #     "**overhead cable tricep extensions (bar)** (8-10 reps) (2 sets)\n\n"
            #     "**straight-bar lat prayer** (12-15 reps) (3 sets)\n\n"
            #     "**pec deck (with integrated partials)** (12-15 reps) (3 sets)\n\n"
            #     "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            # )
            # await send_telegram_reply(chat_id, phase_1_upper_1_menu)
            # return {"status": "success"}
            p1_u1_msg_text = "**JEFF NIPPARD PHASE 1 UPPER DAY 1 CHECKLIST**\n\n"
            "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "**cuffed behind-the-back Lateral Raise** (10-12 reps) (3 sets)\n\n"
            "**cross-body lat pull-around** (10-12 reps) (3 sets)\n\n"
            "**low incline smith machine press** (8-10 reps) (4 sets)\n\n"
            "**chest-supported machine row** (8-10 reps) (3 sets)\n\n"
            "**overhead cable tricep extensions (bar)** (8-10 reps) (2 sets)\n\n"
            "**straight-bar lat prayer** (12-15 reps) (3 sets)\n\n"
            "**pec deck (with integrated partials)** (12-15 reps) (3 sets)\n\n"
            "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            p1_u1_keyboard = {
                "inline_keyboard": [
                    [{"text": "cuffed behind-the-back Lateral Raise",
                        "callback_data": "p1u1_cuffed-behind-the-back-lateral-raise"}],
                    [{"text": "cross-body lat pull-around",
                        "callback_data": "p1u1_cross-body-lat-pull-around"}],
                    [{"text": "low incline smith machine press",
                        "callback_data": "p2u1_low-incline-smith-machine-press"}],
                    [{"text": "chest-supported machine row",
                        "callback_data": "p2u1_chest-supported-machine-row"}],
                    [{"text": "overhead cable tricep extensions (bar)",
                      "callback_data": "p2u1_overhead-cable-tricep-extensions (bar)"}],
                    [{"text": "straight-bar lat prayer",
                        "callback_data": "p2u1_straight-bar-lat-prayer"}],
                    [{"text": "pec deck (with integrated partials)",
                      "callback_data": "p2u1_pec-deck (with integrated partials)"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_u1_msg_text, reply_markup=p1_u1_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_1_upper_2"):
            # phase_1_upper_2_menu = (
            #     "**JEFF NIPPARD PHASE 1 UPPER DAY 2 CHECKLIST**\n\n"
            #     "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            #     "**super-rom overhand cable row** (10-12 reps) (3 sets)\n\n"
            #     "**machine shoulder press** (10-12 reps) (3 sets)\n\n"
            #     "**assisted pull-up** (8-10 reps) (3 sets)\n\n"
            #     "**paused assisted dip** (8-10 reps) (3 sets)\n\n"
            #     "**inverse db zottman curl** (10-12 reps) (2 sets)\n\n"
            #     "**super-rom db lateral raise** (12-15 reps) (3 sets)\n\n"
            #     "**cable reverse fly (mechanical dropset on all sets)** (5,4,3+ reps) (3 sets)\n\n"
            #     "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            # )
            # await send_telegram_reply(chat_id, phase_1_upper_2_menu)
            # return {"status": "success"}

            p1_u2_msg_text = "**JEFF NIPPARD PHASE 1 UPPER DAY 2 CHECKLIST**\n\n"
            "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "**super-rom overhand cable row** (10-12 reps) (3 sets)\n\n"
            "**machine shoulder press** (10-12 reps) (3 sets)\n\n"
            "**assisted pull-up** (8-10 reps) (3 sets)\n\n"
            "**paused assisted dip** (8-10 reps) (3 sets)\n\n"
            "**inverse db zottman curl** (10-12 reps) (2 sets)\n\n"
            "**super-rom db lateral raise** (12-15 reps) (3 sets)\n\n"
            "**cable reverse fly (mechanical dropset on all sets)** (5,4,3+ reps) (3 sets)\n\n"
            "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            p1_u2_keyboard = {
                "inline_keyboard": [
                    [{"text": "super-rom overhand cable row",
                        "callback_data": "p1u2_super-rom overhand cable row"}],
                    [{"text": "machine shoulder press",
                        "callback_data": "p1u2_machine shoulder press"}],
                    [{"text": "assisted pull-up",
                        "callback_data": "p1u2_assisted pull-up"}],
                    [{"text": "paused assisted dip",
                        "callback_data": "p1u2_paused assisted dip"}],
                    [{"text": "inverse db zottman curl",
                        "callback_data": "p1u2_inverse db zottman curl"}],
                    [{"text": "super-rom db lateral raise",
                        "callback_data": "p1u2_super-rom db lateral raise"}],
                    [{"text": "cable reverse fly (mechanical dropset on all sets)",
                      "callback_data": "p1u2_cable reverse fly (mechanical dropset on all sets)"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_u2_msg_text, reply_markup=p1_u2_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_1_lower_1"):
            p1_l1_msg_text = "**JEFF NIPPARD PHASE 1 LOWER DAY 1 CHECKLIST**\n\n"
            "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "**seated leg curl** (8-10 reps) (3 sets)\n\n"
            "**machine hip adduction** (10-12 reps) (3 sets)\n\n"
            "**hack squat** (4,6,8 reps) (3 sets)\n\n"
            "**leg extension** (10-12 reps) (3 sets)\n\n"
            "**leg press calf press** (12-15 reps) (3 sets)\n\n"
            "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            p1_l1_keyboard = {
                "inline_keyboard": [
                    [{"text": "seated leg curl", "callback_data": "p1l1_seated-leg-curl"}],
                    [{"text": "machine hip adduction",
                        "callback_data": "p1l1_machine-hip-adduction"}],
                    [{"text": "hack squat", "callback_data": "p1l1_hack-squat"}],
                    [{"text": "leg extension", "callback_data": "p1l1_leg-extension"}],
                    [{"text": "leg press calf press",
                        "callback_data": "p1l1_leg-press-calf-press"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_l1_msg_text, reply_markup=p1_l1_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_1_lower_2"):
            # phase_1_lower_2_menu = (
            #     "**JEFF NIPPARD PHASE 1 LOWER DAY 2 CHECKLIST**\n\n"
            #     "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            #     "**lying leg curl** (8-10 reps) (3 sets)\n\n"
            #     "**leg press** (8 reps) (3 sets)\n\n"
            #     "**paused barbell rdl** (8 reps) (2 sets)\n\n"
            #     "**machine hip adduction (super set with sissy squat)** (10-12 reps) (3 sets)\n\n"
            #     "**sissy squat (super set with machine hip adduction)** (10-12 reps) (3 sets)\n\n"
            #     "**standing calf raise** (10-12 reps) (3 sets)\n\n"
            #     "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            # )
            # await send_telegram_reply(chat_id, phase_1_lower_2_menu)
            # return {"status": "success"}
            p1_l2_msg_text = "**JEFF NIPPARD PHASE 1 LOWER DAY 2 CHECKLIST**\n\n"
            "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "**lying leg curl** (8-10 reps) (3 sets)\n\n"
            "**leg press** (8 reps) (3 sets)\n\n"
            "**paused barbell rdl** (8 reps) (2 sets)\n\n"
            "**machine hip adduction (super set with sissy squat)** (10-12 reps) (3 sets)\n\n"
            "**sissy squat (super set with machine hip adduction)** (10-12 reps) (3 sets)\n\n"
            "**standing calf raise** (10-12 reps) (3 sets)\n\n"
            "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            p1_l2_keyboard = {
                "inline_keyboard": [
                    [{"text": "lying leg curl (8-10 reps) (3 sets)", "callback_data": "p1l2_lying-leg-curl"}],
                    [{"text": "leg press (8 reps) (3 sets)", "callback_data": "p1l2_leg-press"}],
                    [{"text": "paused barbell rdl (8 reps) (2 sets)",
                        "callback_data": "p1l2_paused-barbell-rdl"}],
                    [{"text": "machine hip adduction (super set with sissy squat) (10-12 reps) (3 sets)",
                      "callback_data": "p1l2_machine-hip-adduction"}],
                    [{"text": "sissy squat (super set with machine hip adduction) (10-12 reps) (3 sets)",
                      "callback_data": "p1l2_sissy-squat"}],
                    [{"text": "standing calf raise (10-12 reps) (3 sets)",
                        "callback_data": "p1l2_standing-calf-raise"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_l2_msg_text, reply_markup=p1_l2_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_1_arms"):
            # phase_1_arms_menu = (
            #     "**JEFF NIPPARD PHASE 1 ARMS & WEAK POINTS CHECKLIST**\n\n"
            #     "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n"
            #     "**Weak Point Exercise 1** (8-12 reps) (3 sets)\n\n"
            #     "**Weak Point Exercise 2 (Optional)** (8-12 reps) (2 sets)\n\n"
            #     "**bayesian cable curl** (10-12 reps) (3 sets)\n\n"
            #     "**seated db french press** (10 reps) (3 sets)\n\n"
            #     "**bottom-2/3 constant tension preacher curl** (12-15 reps) (2 sets)\n\n"
            #     "**cable triceps kickback** (12-15 reps) (2 sets)\n\n"
            #     "**cable crunch** (10-12 reps) (3 sets)\n\n"
            #     "**Ready to log!** Just text your sets normally.\n\n"
            # )
            # await send_telegram_reply(chat_id, phase_1_arms_menu)
            # return {"status": "success"}

            p1_wp1_msg_text = "**JEFF NIPPARD PHASE 1 ARMS & WEAK POINTS CHECKLIST**\n\n **Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n **Weak Point Exercise 1** (8-12 reps) (3 sets)\n\n"
            p1_wp1_keyboard = {
                "inline_keyboard": [
                    [{"text": "Shoulders (8-12 reps) (3 sets)", "callback_data": "wp_shoulders"}],
                    [{"text": "Lats (8-12 reps) (3 sets)", "callback_data": "wp_lats"}],
                    [{"text": "Quads (8-12 reps) (3 sets)", "callback_data": "wp_quads"}],
                    [{"text": "Glutes (8-12 reps) (3 sets)", "callback_data": "wp_glutes"}],
                    [{"text": "Chest (8-12 reps) (3 sets)", "callback_data": "wp_chest"}],
                    [{"text": "Neck (8-12 reps) (3 sets)", "callback_data": "wp_neck"}],
                    [{"text": "Hamstrings (8-12 reps) (3 sets)", "callback_data": "wp_hamstrings"}],
                    [{"text": "Calves (8-12 reps) (3 sets)", "callback_data": "wp_calves"}],
                    [{"text": "Mid-Back (8-12 reps) (3 sets)", "callback_data": "wp_mid-back"}],
                    [{"text": "Upper Traps (8-12 reps) (3 sets)", "callback_data": "wp_upper traps"}],
                    [{"text": "Abs (8-12 reps) (3 sets)", "callback_data": "wp_abs"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_wp1_msg_text, reply_markup=p1_wp1_keyboard)
            p1_wp2_msg_text = "**Weak Point Exercise 2 (Optional)** (8-12 reps) (2 sets)\n\n"
            p1_wp2_keyboard = {
                "inline_keyboard": [
                    [{"text": "Shoulders (8-12 reps) (2 sets)", "callback_data": "wp_shoulders"}],
                    [{"text": "Lats (8-12 reps) (2 sets)", "callback_data": "wp_lats"}],
                    [{"text": "Quads (8-12 reps) (2 sets)", "callback_data": "wp_quads"}],
                    [{"text": "Glutes (8-12 reps) (2 sets)", "callback_data": "wp_glutes"}],
                    [{"text": "Chest (8-12 reps) (2 sets)", "callback_data": "wp_chest"}],
                    [{"text": "Neck (8-12 reps) (2 sets)", "callback_data": "wp_neck"}],
                    [{"text": "Hamstrings (8-12 reps) (2 sets)", "callback_data": "wp_hamstrings"}],
                    [{"text": "Calves (8-12 reps) (2 sets)", "callback_data": "wp_calves"}],
                    [{"text": "Mid-Back (8-12 reps) (2 sets)", "callback_data": "wp_mid-back"}],
                    [{"text": "Upper Traps (8-12 reps) (2 sets)", "callback_data": "wp_upper traps"}],
                    [{"text": "Abs (8-12 reps) (2 sets)", "callback_data": "wp_abs"}]
                ]
            }
            await send_telegram_reply(chat_id, p1_wp2_msg_text, reply_markup=p1_wp2_keyboard)
            p1_arms_text = "**bayesian cable curl** (10-12 reps) (3 sets)\n\n"
            "**seated db french press** (10 reps) (3 sets)\n\n"
            "**bottom-2/3 constant tension preacher curl** (12-15 reps) (2 sets)\n\n"
            "**cable triceps kickback** (12-15 reps) (2 sets)\n\n"
            "**cable crunch** (10-12 reps) (3 sets)\n\n"
            "**Ready to log!** Just text your sets normally.\n\n"
            p1_arms_keyboard = {
                "inline_keyboard": [
                    [{"text": "bayesian cable curl (10-12 reps) (3 sets)",
                        "callback_data": "p1a_bayesian-cable-curl"}],
                    [{"text": "seated db french press (10 reps) (3 sets)",
                        "callback_data": "p1a_seated-db-french-press"}],
                    [{"text": "bottom-2/3 constant tension preacher curl (12-15 reps) (2 sets)",
                        "callback_data": "p1a_bottom-2/3-constant-tension-preacher-curl"}],
                    [{"text": "cable triceps kickback (12-15 reps) (2 sets)",
                        "callback_data": "p1a_cable-triceps-kickback"}],
                    [{"text": "cable crunch (10-12 reps) (3 sets)", "callback_data": "p1a_cable-crunch"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_arms_text, reply_markup=p1_arms_keyboard)
            return {"status": "success"}

        if user_text.lower() == ("/phase_2_upper_1"):
            # phase_2_upper_1_menu = (
            #     "**JEFF NIPPARD PHASE 2 UPPER DAY 1 CHECKLIST**\n\n"
            #     "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            #     "**cuffed behind-the-back Lateral Raise** (10-12 reps) (3 sets)\n\n"
            #     "**lat-focused cable row** (10-12 reps) (3 sets)\n\n"
            #     "**low incline db press** (8-10 reps) (3 sets)\n\n"
            #     "**chest-supported t-bar row & kelso shrug** (8-10 + 4-6 reps) (3 sets)\n\n"
            #     "**bent-over cable pec flye (w/ integrated partials)** (12-15 reps) (3 sets)\n\n"
            #     "**1-arm lat pull-in** (12-15 reps) (2 sets)\n\n"
            #     "**dual-cable triceps press** (10-12 reps) (3 sets)\n\n"
            #     "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            # )
            # await send_telegram_reply(chat_id, phase_2_upper_1_menu)
            # return {"status": "success"}
            p2_u1_msg_text = "**JEFF NIPPARD PHASE 2 UPPER DAY 1 CHECKLIST**\n\n"
            "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "**cuffed behind-the-back Lateral Raise** (10-12 reps) (3 sets)\n\n"
            "**lat-focused cable row** (10-12 reps) (3 sets)\n\n"
            "**low incline db press** (8-10 reps) (3 sets)\n\n"
            "**chest-supported t-bar row & kelso shrug** (8-10 + 4-6 reps) (3 sets)\n\n"
            "**bent-over cable pec flye (w/ integrated partials)** (12-15 reps) (3 sets)\n\n"
            "**1-arm lat pull-in** (12-15 reps) (2 sets)\n\n"
            "**dual-cable triceps press** (10-12 reps) (3 sets)\n\n"
            "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            p2_u1_keyboard = {
                "inline_keyboard": [
                    [{"text": "cuffed behind-the-back Lateral Raise (10-12 reps) (3 sets)",
                        "callback_data": "p2u1_cuffed-behind-the-back-lateral-raise"}],
                    [{"text": "lat-focused cable row (10-12 reps) (3 sets)",
                        "callback_data": "p2u1_lat-focused-cable-row"}],
                    [{"text": "low incline db press (8-10 reps) (3 sets)",
                        "callback_data": "p2u1_low-incline-db-press"}],
                    [{"text": "chest-supported t-bar row & kelso shrug (8-10 + 4-6 reps) (3 sets)",
                        "callback_data": "p2u1_chest-supported t-bar-row + kelso shrug"}],
                    [{"text": "bent-over cable pec flye (w/ integrated partials) (12-15 reps) (3 sets)",
                      "callback_data": "p2u1_bent-over-cable-pec-flye-(w/-integrated-partials)"}],
                    [{"text": "1-arm lat pull-in (12-15 reps) (2 sets)",
                        "callback_data": "p2u1_1-arm-lat-pull-in"}],
                    [{"text": "dual-cable triceps press (10-12 reps) (3 sets)",
                        "callback_data": "p2u1_dual-cable-triceps-press"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_u1_msg_text, reply_markup=p2_u1_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_2_upper_2"):
            # phase_2_upper_2_menu = (
            #     "**JEFF NIPPARD PHASE 2 UPPER DAY 2 CHECKLIST**\n\n"
            #     "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            #     "**dual-handle lat pulldown (mid-back + lats)** (10-12 reps) (3 sets)\n\n"
            #     "**seated dumbbell shoulder press** (10-12 reps) (3 sets)\n\n"
            #     "**chest-supported machine row** (8-10 reps) (3 sets)\n\n"
            #     "**decline machine chest press** (8-10 reps) (3 sets)\n\n"
            #     "**concentration cable curl** (10-12 reps) (2 sets)\n\n"
            #     "**cross-body cable y-raise** (10-12 reps) (3 sets)\n\n"
            #     "**rear delt 45 degrees cable flye** (12-15 reps) (3 sets)\n\n"
            #     "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            # )
            # await send_telegram_reply(chat_id, phase_2_upper_2_menu)
            # return {"status": "success"}
            p2_u2_msg_text = "**JEFF NIPPARD PHASE 2 UPPER DAY 2 CHECKLIST**\n\n"
            "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "**dual-handle lat pulldown (mid-back + lats)** (10-12 reps) (3 sets)\n\n"
            "**seated dumbbell shoulder press** (10-12 reps) (3 sets)\n\n"
            "**chest-supported machine row** (8-10 reps) (3 sets)\n\n"
            "**decline machine chest press** (8-10 reps) (3 sets)\n\n"
            "**concentration cable curl** (10-12 reps) (2 sets)\n\n"
            "**cross-body cable y-raise** (10-12 reps) (3 sets)\n\n"
            "**rear delt 45 degrees cable flye** (12-15 reps) (3 sets)\n\n"
            "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            p2_u2_keyboard = {
                "inline_keyboard": [
                    [{"text": "dual-handle lat pulldown (mid-back + lats) (10-12 reps) (3 sets)",
                      "callback_data": "p2u2_dual-handle-lat-pulldown (mid-back + lats)"}],
                    [{"text": "seated dumbbell shoulder press (10-12 reps) (3 sets)",
                        "callback_data": "p2u2_seated-dumbbell-shoulder-press"}],
                    [{"text": "chest-supported machine row (8-10 reps) (3 sets)",
                        "callback_data": "p2u2_chest-supported-machine-row"}],
                    [{"text": "decline machine chest press (8-10 reps) (3 sets)",
                        "callback_data": "p2u2_decline-machine-chest-press"}],
                    [{"text": "concentration cable curl (10-12 reps) (2 sets)",
                        "callback_data": "p2u2_concentration-cable-curl"}],
                    [{"text": "cross-body cable y-raise (10-12 reps) (3 sets)",
                        "callback_data": "p2u2_cross-body-cable-y-raise"}],
                    [{"text": "rear delt 45 degrees cable flye (12-15 reps) (3 sets)",
                        "callback_data": "p2u2_rear-delt-45-degrees-cable-flye"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_u2_msg_text, reply_markup=p2_u2_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_2_lower_1"):
            # phase_2_lower_1_menu = (
            #     "**JEFF NIPPARD PHASE 2 LOWER DAY 1 CHECKLIST**\n\n"
            #     "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            #     "**seated leg curl** (8-10 reps) (3 sets)\n\n"
            #     "**machine hip adduction** (10-12 reps) (3 sets)\n\n"
            #     "**smith machine squat** (4,6,8 reps) (3 sets)\n\n"
            #     "**leg extension** (10-12 reps) (3 sets)\n\n"
            #     "**dumbbell calf jumps** (12-15 reps) (3 sets)\n\n"
            #     "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            # )
            # await send_telegram_reply(chat_id, phase_2_lower_1_menu)
            # return {"status": "success"}

            p2_l1_msg_text = "**JEFF NIPPARD PHASE 2 LOWER DAY 1 CHECKLIST**\n\n"
            "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "**seated leg curl** (8-10 reps) (3 sets)\n\n"
            "**machine hip adduction** (10-12 reps) (3 sets)\n\n"
            "**smith machine squat** (4,6,8 reps) (3 sets)\n\n"
            "**leg extension** (10-12 reps) (3 sets)\n\n"
            "**dumbbell calf jumps** (12-15 reps) (3 sets)\n\n"
            "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            p2_l1_keyboard = {
                "inline_keyboard": [
                    [{"text": "Seated Leg Curl (8-10 reps) (3 sets)", "callback_data": "p2l1_seated-leg-curl"}],
                    [{"text": "Machine Hip Adduction (10-12 reps) (3 sets)",
                        "callback_data": "p2l1_machine-hip-adduction"}],
                    [{"text": "Smith Machine Squat (4,6,8 reps) (3 sets)",
                        "callback_data": "p2l1_smith-machine-squat"}],
                    [{"text": "Leg Extension (10-12 reps) (3 sets)", "callback_data": "p2l1_leg-extension"}],
                    [{"text": "Dumbbell Calf Jumps (12-15 reps) (3 sets)",
                        "callback_data": "p2l1_dumbbell-calf-jumps"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_l1_msg_text, reply_markup=p2_l1_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_2_lower_2"):
            # phase_2_lower_2_menu = (
            #     "**JEFF NIPPARD PHASE 2 LOWER DAY 2 CHECKLIST**\n\n"
            #     "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            #     "**lying leg curl** (8-10 reps) (3 sets)\n\n"
            #     "**smith machine reverse lunge press** (8 reps) (3 sets)\n\n"
            #     "**glute-ham raise** (8 reps) (3 sets)\n\n"
            #     "**machine hip adduction (super set with machine hip abduction)** (10-12 reps) (3 sets)\n\n"
            #     "**machine hip abduction (super set with machine hip adduction)** (10-12 reps) (3 sets)\n\n"
            #     "**standing calf raise** (10-12 reps) (3 sets)\n\n"
            #     "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            # )
            # await send_telegram_reply(chat_id, phase_2_lower_2_menu)
            # return {"status": "success"}

            p2_l2_msg_text = "**JEFF NIPPARD PHASE 2 LOWER DAY 2 CHECKLIST**\n\n"
            "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "**lying leg curl** (8-10 reps) (3 sets)\n\n"
            "**smith machine reverse lunge press** (8 reps) (3 sets)\n\n"
            "**glute-ham raise** (8 reps) (3 sets)\n\n"
            "**machine hip adduction (super set with machine hip abduction)** (10-12 reps) (3 sets)\n\n"
            "**machine hip abduction (super set with machine hip adduction)** (10-12 reps) (3 sets)\n\n"
            "**standing calf raise** (10-12 reps) (3 sets)\n\n"
            "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            p2_l2_keyboard = {
                "inline_keyboard": [
                    [{"text": "lying leg curl (8-10 reps) (3 sets)", "callback_data": "p2l2_lying-leg-curl"}],
                    [{"text": "smith machine reverse lunge press (8 reps) (3 sets)",
                        "callback_data": "p2l2_smith-machine-reverse-lunge-press"}],
                    [{"text": "glute-ham raise (8 reps) (3 sets)", "callback_data": "p2l2_glute-ham-raise"}],
                    [{
                        "text": "machine hip adduction (super set with machine hip abduction) (10-12 reps) (3 sets)", "callback_data": "p2l2_machine-hip-adduction"}],
                    [{"text": "machine hip abduction (super set with machine hip adduction) (10-12 reps) (3 sets)",
                      "callback_data": "p2l2_machine-hip-abduction"}],
                    [{"text": "standing calf raise (10-12 reps) (3 sets)",
                        "callback_data": "p2l2_standing-calf-raise"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_l2_msg_text, reply_markup=p2_l2_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_2_arms"):
            # phase_2_arms_menu = (
            #     "**JEFF NIPPARD ARMS & WEAK POINTS CHECKLIST**\n\n"
            #     "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n"
            #     "**Weak Point Exercise 1** (8-12 reps) (3 sets)\n\n"
            #     "**Weak Point Exercise 2 (Optional)** (8-12 reps) (2 sets)\n\n"
            #     "**slow-eccentric ez-bar skull crusher** (10-12 reps) (3 sets)\n\n"
            #     "**slow-eccentric bayesian curl** (10-12 reps) (3 sets)\n\n"
            #     "**triceps diverging pressdown (long rope or 2 ropes)** (12-15 reps) (2 sets)\n\n"
            #     "**reverse grip cable curl** (12-15 reps) (2 sets)\n\n"
            #     "**roman chair leg raise crunch** (10-20 reps) (3 sets)\n\n"
            #     "**Ready to log!** Just text your sets normally.\n\n"
            # )
            # await send_telegram_reply(chat_id, phase_2_arms_menu)
            # return {"status": "success"}
            p2_wp1_msg_text = "**JEFF NIPPARD PHASE 2 ARMS & WEAK POINTS CHECKLIST**\n\n"
            "**Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n"
            "**Weak Point Exercise 1** (8-12 reps) (3 sets)\n\n"
            p2_wp1_keyboard = {
                "inline_keyboard": [
                    [{"text": "Shoulders", "callback_data": "wp_shoulders"},
                        {"text": "Lats", "callback_data": "wp_lats"}],
                    [{"text": "Quads", "callback_data": "wp_quads"}, {
                        "text": "Glutes", "callback_data": "wp_glutes"}],
                    [{"text": "Chest", "callback_data": "wp_chest"}, {
                        "text": "Neck", "callback_data": "wp_neck"}],
                    [{"text": "Hamstrings", "callback_data": "wp_hamstrings"}, {
                        "text": "Calves", "callback_data": "wp_calves"}],
                    [{"text": "Mid-Back", "callback_data": "wp_mid-back"},
                        {"text": "Upper Traps", "callback_data": "wp_upper traps"}],
                    [{"text": "Abs", "callback_data": "wp_abs"}]
                ]
            }
            await send_telegram_reply(chat_id, p2_wp1_msg_text, reply_markup=p2_wp1_keyboard)
            p2_wp2_msg_text = "**Weak Point Exercise 2 (Optional)** (8-12 reps) (2 sets)\n\n"
            p2_wp2_keyboard = {
                "inline_keyboard": [
                    [{"text": "Shoulders", "callback_data": "wp_shoulders"}],
                    [{"text": "Lats", "callback_data": "wp_lats"}],
                    [{"text": "Quads", "callback_data": "wp_quads"}],
                    [{
                        "text": "Glutes", "callback_data": "wp_glutes"}],
                    [{"text": "Chest", "callback_data": "wp_chest"}], [{
                        "text": "Neck", "callback_data": "wp_neck"}],
                    [{"text": "Hamstrings", "callback_data": "wp_hamstrings"}], [{
                        "text": "Calves", "callback_data": "wp_calves"}],
                    [{"text": "Mid-Back", "callback_data": "wp_mid-back"}],
                    [{"text": "Upper Traps", "callback_data": "wp_upper traps"}],
                    [{"text": "Abs", "callback_data": "wp_abs"}]
                ]
            }
            await send_telegram_reply(chat_id, p2_wp2_msg_text, reply_markup=p2_wp2_keyboard)
            p2_arms_msg_text = "**slow-eccentric ez-bar skull crusher** (10-12 reps) (3 sets)\n\n"
            "**slow-eccentric bayesian curl** (10-12 reps) (3 sets)\n\n"
            "**triceps diverging pressdown (long rope or 2 ropes)** (12-15 reps) (2 sets)\n\n"
            "**reverse grip cable curl** (12-15 reps) (2 sets)\n\n"
            "**roman chair leg raise crunch** (10-20 reps) (3 sets)\n\n"
            "**Ready to log!** Just text your sets normally.\n\n"
            p2_arms_keyboard = {
                "inline_keyboard": [
                    [{"text": "slow-eccentric ez-bar skull crusher (10-12 reps) (3 sets)", "callback_data": "p2a_slow-eccentric-ez-bar-skull-crusher"},
                        {"text": "slow-eccentric bayesian curl (10-12 reps) (3 sets)", "callback_data": "p2a_slow-eccentric-bayesian-curl"}],
                    [{"text": "triceps diverging pressdown (long rope or 2 ropes) (12-15 reps) (2 sets)", "callback_data": "p2a_triceps-diverging-pressdown-(long-rope-or-2-ropes)"}, {
                        "text": "reverse grip cable curl (12-15 reps) (2 sets)", "callback_data": "p2a_reverse-grip-cable-curl"}],
                    [{"text": "roman chair leg raise crunch (10-20 reps) (3 sets)",
                        "callback_data": "p2a_roman-chair-leg-raise-crunch"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_arms_msg_text, reply_markup=p2_arms_keyboard)
            return {"status": "success"}
        if user_text.lower() == "/weakpoints":
            msg_text = "**Select your Weak Point for today:**"
            keyboard = {
                "inline_keyboard": [
                    [{"text": "Shoulders", "callback_data": "wp_shoulders"},
                        {"text": "Lats", "callback_data": "wp_lats"}],
                    [{"text": "Quads", "callback_data": "wp_quads"}, {
                        "text": "Glutes", "callback_data": "wp_glutes"}],
                    [{"text": "Chest", "callback_data": "wp_chest"}, {
                        "text": "Neck", "callback_data": "wp_neck"}],
                    [{"text": "Hamstrings", "callback_data": "wp_hamstrings"}, {
                        "text": "Calves", "callback_data": "wp_calves"}],
                    [{"text": "Mid-Back", "callback_data": "wp_mid-back"},
                        {"text": "Upper Traps", "callback_data": "wp_upper traps"}],
                    [{"text": "Abs", "callback_data": "wp_abs"}]
                ]
            }
            await send_telegram_reply(chat_id, msg_text, reply_markup=keyboard)
            return {"status": "success"}
        if user_text.lower() == "/meal":
            meal_instructions = (
                "**NUTRITION LOGGING ENGINE**\n\n"
                "You can log your food conversationally without worrying about exact serving math. "
                "The system will automatically categorize it based on the time of day and calculate your macros into Supabase.\n\n"
                "  **How to log:**\n"
                "Simply text me what you ate naturally. If your message doesn't contain lifting terms (like lbs or reps), it defaults to a food log!\n\n"
                "**Examples:**\n"
                "• *'meal: 3 eggs and a scoop of ascent native fuel whey protein powder'*\n"
                "• *'meal: chicken korma with two pieces of garlic naan'*\n"
                "• *'meal: fish pulusu with two pieces of paratha for lunch 06/10/2026'*\n"
                "• *'meal: rice with chicken for dinner'*\n"
                "• *'meal: a slice of homemade tiramisu'*\n\n"
                "*Just start your message with 'meal:' followed by your food to save it!*"
            )
            await send_telegram_reply(chat_id, meal_instructions)
            return {"status": "success"}

        if user_text.lower() == "/profile":
            profile_instructions = (
                "Profile Setup \n\n"
                "You can log your Body Scan results and goal to save it and train the machine learning model. "
                "The system will automatically use your goal and categories your food based on the time of day and calculate your macros into Supabase.\n\n"
                "Just start your message with 'profile:' followed by your data in the following format so I can update your macro targets: Body Composition: [Water], [Dry Lean Mass], [Fat Mass], [Weight]; Muscle-Fat: [Weight], [SMM], [Body Fat Mass]; Obesity: [BMI], [PBF]; Segmental Lean: [Left Arm %], [Right Arm %], [Left Leg %], [Right Leg %]; BMR: [Height in inches, Age], Goal: [bulk/cut/recomposition]"
            )
            await send_telegram_reply(chat_id, profile_instructions)
            return {"status": "success"}
        if user_text.lower().startswith("profile:"):
            clean_profile_text = user_text.lower().replace("profile:", "").strip()

            class ProfileInput(BaseModel):
                weight: float
                goal: str
                body_fat_percentage: float
                total_body_water: float
                dry_lean_mass: float
                skeletal_muscle_mass: float  # SMM
                bmi: float
                segmental_lean_data: list[float]
                age: float
                height: float

            schema_string = json.dumps(ProfileInput.model_json_schema())
            system_instructions = (
                "You are an expert fitness data parser. "
                "The user will provide data in these categories: "
                "1. Body Composition (Total Body Water, Dry Lean Mass, Fat Mass, Weight). "
                "2. Muscle-Fat Analysis (Weight, SMM, Fat Mass). "
                "3. Obesity Analysis (BMI, PBF). "
                "4. Segmental Lean Analysis (Left Arm %, Right Arm %, Left Leg %, Right Leg %). "
                "5. BMR Analysis (height, age)"
                "5. Goal (bulk, cut, maintenance, recomposition)"
                "Extract all fields into the ProfileInput schema. "
                f"Return ONLY valid JSON: {schema_string}"
            )

            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": clean_profile_text}
                ],
                model="openai/gpt-oss-120b",
                response_format={"type": "json_object"}
            )

            profile_data = ProfileInput.model_validate_json(
                response.choices[0].message.content)
            weight = profile_data.weight
            height = profile_data.height
            age = profile_data.age
            goal = profile_data.goal.lower()
            bmr = (10 * (weight / 2.2)) + \
                (6.25 * (height * 2.54)) - (5 * age) + 5
            tdee = bmr * 1.55

            if "cut" in goal:
                cals = tdee - 500
            elif "bulk" in goal:
                cals = tdee + 500
            else:
                cals = tdee - 100

            cals = round(cals)

            protein = int(weight * 1.0)
            fat = int(weight * 0.3)

            # Carbs = (Total Calories - Protein Calories - Fat Calories) / 4
            carbs = int((cals - (protein * 4) - (fat * 9)) / 4)

            # Upsert directly to Supabase using the math we just did
            supabase.table("user_profiles").upsert({
                "chat_id": chat_id,
                "current_weight_lbs": weight,
                "goal": goal,
                "target_calories": cals,
                "target_protein": protein,
                "target_carbs": carbs,
                "target_fat": fat,
                "total_body_water": profile_data.total_body_water,
                "dry_lean_mass": profile_data.dry_lean_mass,
                "skeletal_muscle_mass": profile_data.skeletal_muscle_mass,
                "bmi": profile_data.bmi,
                "segmental_lean_data": profile_data.segmental_lean_data
            }).execute()

            reply = (
                f"**Smart Profile Generated!**\n"
                f"Weight: {weight} lbs | Goal: {goal.title()}\n\n"
                f"**Your Daily Targets:**\n"
                f"**{cals} kcal**\n"
                f"Protein: {protein}g\n"
                f"Carbs: {carbs}g\n"
                f"Fat: {fat}g\n"
                f"**Scan Metrics Logged:**\n"
                f"SMM: {profile_data.skeletal_muscle_mass}kg\n"
                f"BMI: {profile_data.bmi}"
            )

            await send_telegram_reply(chat_id, reply)
            return {"status": "success"}

        base_keywords = ["bench", "squat", "deadlift", "reps", "sets", "lbs", "lift", "press", "curls", "workout",
                         "pounds", "row", "pulldown", "fly", "raise", "extension", "crunch", "rdl", "step up", "toe-press"]
        workout_keywords = base_keywords + list(PROGRESSION_SCHEMA.keys())
        is_workout = any(word in user_text.lower() for word in workout_keywords) or user_text.lower(
        ).startswith("w:") or "upper:" in user_text.lower() or "lower:" in user_text.lower()

        if user_text.lower().startswith("meal:"):
            clean_food_text = user_text.lower().replace(
                "meal:", "").replace("f:", "").strip()
            search_prompt = f"Extract ONLY the core food ingredient or restaurant item to search in a database from this text: '{
                clean_food_text}'. Do not include portions, meal types, or dates. Return just the search string."
            search_res = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": search_prompt}],
                model="openai/gpt-oss-20b"
            )
            search_query = search_res.choices[0].message.content.strip().replace(
                '"', '')

            usda_results = await get_usda_macros(search_query)

            PENDING_LOGS[chat_id] = {
                "raw_text": clean_food_text,
                "usda_options": usda_results
            }

            keyboard = {"inline_keyboard": []}

            if usda_results:
                msg_text = f" Found {len(usda_results)} results for **{
                    search_query}**.\nSelect the most accurate option to log it:"
                for i, item in enumerate(usda_results):
                    btn_text = f"{item['food_name'][:30]
                                  }... ({item['calories']} kcal)"
                    keyboard["inline_keyboard"].append(
                        [{"text": btn_text, "callback_data": f"usda_{i}"}])
            else:
                msg_text = f" No exact USDA match found for **{
                    search_query}**. Would you like the AI to estimate the macros?"

            # Always offer the AI fallback button
            keyboard["inline_keyboard"].append(
                [{"text": "Use AI Estimation instead", "callback_data": "ai_fallback"}])

            # Send the approval request
            await send_telegram_reply(chat_id, msg_text, reply_markup=keyboard)

        elif is_workout:
            clean_text = user_text.replace("workout:", "").replace(
                "upper", "").replace("lower", "").replace("w", "").strip()
            active_ex = ACTIVE_EXERCISE_SESSIONS.get(chat_id)
            if active_ex and not any(ex_word in clean_text.lower() for ex_word in PROGRESSION_SCHEMA.keys()):
                clean_text = f"{active_ex} {clean_text}"
            schema_string = json.dumps(WorkoutStructure.model_json_schema())
            official_names = ", ".join(PROGRESSION_SCHEMA.keys())
            system_instructions = f"You are a data extractor. Return ONLY a valid JSON object matching this schema exactly: {schema_string}. IMPORTANT: You must standardize the exercise_name to match one of these official names if it is similar: {
                official_names}. If the user mentions an exercise but provides no numbers for weight or reps, return 0 for both. If the user indicates this set is a warm-up (e.g. 'warmup', 'wu', 'warm up'), set 'is_warmup' to true."
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": f"Extract parameters from this performed set text: '{
                        clean_text}'"}
                ],
                model="openai/gpt-oss-120b",
                response_format={"type": "json_object"}
            )
            lift_data = WorkoutStructure.model_validate_json(
                response.choices[0].message.content)
            exercise = lift_data.exercise_name.lower().strip()

            if exercise not in PROGRESSION_SCHEMA:
                error_reply = (
                    f"**Unrecognized Exercise:** '_{exercise.title()}_'\n\n"
                    f"That exercise is not currently mapped in your program schema. Please check your spelling or choose an exercise from your workout menu!"
                )
                await send_telegram_reply(chat_id, error_reply)
                return {"status": "success"}

            if lift_data.reps == 0:
                today_str = date.today().isoformat()

                coaching_data = EXERCISE_COACHING.get(
                    exercise, {"reps": "8-12 reps", "advice": "Normal working set to hypertrophy depth."})
                intensity_advice = coaching_data["advice"]
                warmup_count = coaching_data.get("warmup_sets", 0)

                ex_schema = PROGRESSION_SCHEMA.get(exercise)
                schema_text_lines = []
                for s, targets in ex_schema.items():
                    schema_text_lines.append(f"• Working Set {s}: {
                                             targets['max_reps']} reps (+{targets['increment']} lbs incr.)")
                schema_text = "\n".join(schema_text_lines)

                # Fetch the most recent past logs for this exercise
                history = supabase.table("exercise_logs") \
                    .select("weight, reps, set_number, created_at") \
                    .eq("exercise_name", exercise) \
                    .lt("created_at", today_str) \
                    .order("created_at", desc=True) \
                    .limit(25) \
                    .execute()

                if not history.data:
                    reply = f"**No history found for {exercise.title()}!**\nStart with a light warm-up weight to establish your baseline today.\n\n**Progression Schema:**\n{
                        schema_text}\n\n *Technique Cues:* {intensity_advice}"
                else:
                    last_date = history.data[0]['created_at'][:10]
                    last_session = [
                        row for row in history.data if row['created_at'].startswith(last_date)]

                    history_text = "\n".join([f"• Set {row['set_number']}: {row['weight']} lbs × {
                                             row['reps']} reps" for row in sorted(last_session, key=lambda x: x['set_number'])])

                    set_1_targets = ex_schema.get(
                        1, {"min_reps": 8, "max_reps": 12, "increment": 5})
                    target_max_reps = set_1_targets['max_reps']
                    target_min_reps = set_1_targets['min_reps']
                    increment = set_1_targets['increment']

                    upper_1_anchors = [
                        "low incline smith machine press", "low incline db press"]
                    end_of_today = f"{today_str}T23:59:59"

                    upper_1_logs = supabase.table("exercise_logs") \
                        .select("created_at") \
                        .in_("exercise_name", upper_1_anchors) \
                        .lte("created_at", end_of_today) \
                        .execute()

                    unique_weeks = len(set(
                        row['created_at'][:10] for row in upper_1_logs.data)) if upper_1_logs.data else 1
                    if unique_weeks == 0:
                        unique_weeks = 1

                    is_deload_week = (unique_weeks % 5 == 0)

                    successful_sets = [
                        s for s in last_session if s['reps'] >= target_min_reps]

                    if successful_sets:
                        best_set = max(successful_sets,
                                       key=lambda x: x['weight'])
                        target_working_weight = best_set['weight']

                        if best_set['reps'] >= target_max_reps:
                            target_working_weight += increment
                            rec_text = f"You crushed **{target_max_reps} reps** at {best_set['weight']} lbs last time! Load up **{
                                target_working_weight} lbs** for Set 1 today and aim for **{target_max_reps} reps**!"
                        else:
                            rec_text = f"Your heaviest successful set last time was **{target_working_weight} lbs** for {
                                best_set['reps']} reps. Stick with **{target_working_weight} lbs** for Set 1 today and push for **{target_max_reps} reps**!"
                    else:
                        heaviest_set = max(
                            last_session, key=lambda x: x['weight'])
                        target_working_weight = max(
                            0, heaviest_set['weight'] - increment)
                        rec_text = f"You fell below the {target_min_reps} rep floor last time ({heaviest_set['weight']} lbs × {
                            heaviest_set['reps']} reps). Drop weight to **{target_working_weight} lbs** for Working Set 1 today to stay in the target zone."

                    if is_deload_week:
                        schema_text = " **SEMI-DELOAD WEEK (Week 5)** \n*Avoid failure (RPE 7-8) and drop 1 total working set today to promote recovery! Next week starts Next Block so Update Excercises*\n\n" + schema_text

                    warmup_guide = generate_warmup_guide(
                        warmup_count, target_working_weight)

                    reply = f"**Last Session: {exercise.title()}** ({last_date})\n\n{history_text}\n\n **Target Working Weight:** {rec_text}\n\n **Recommended Warm-Up Pyramid ({
                        warmup_count} sets): **\n{warmup_guide}\n\n **Working Progression Schema:**\n{schema_text}\n\n *Technique Cues:* {intensity_advice}"

                await send_telegram_reply(chat_id, reply)
                return {"status": "success"}

            today_str = date.today().isoformat()
            existing_sets = supabase.table("exercise_logs") \
                .select("id") \
                .eq("exercise_name", exercise) \
                .gte("created_at", today_str) \
                .execute()

            if lift_data.is_warmup:
                set_count = 0  # Marked as 0 or warm-up in logs
            else:
                set_count = len(existing_sets.data) + 1

            central_tz = zoneinfo.ZoneInfo("America/Chicago")
            supabase.table("exercise_logs").insert({
                "exercise_name": exercise,
                "weight": lift_data.weight,
                "reps": lift_data.reps,
                "set_number": set_count,
                "is_warmup": lift_data.is_warmup,
                "created_at": datetime.now(central_tz).isoformat()
            }).execute()

            if lift_data.is_warmup:
                reply_msg = (
                    f"🔥 **Warm-Up Set Tracked:**\n"
                    f"*{exercise.title()
                        }* - **{lift_data.weight} lbs × {lift_data.reps} reps**\n"
                    f"*(This does not trigger rest timers or affect working set counts)*"
                )
                await send_telegram_reply(chat_id, reply_msg)
                return {"status": "success"}

            total_target_sets = 1
            rep_guideline = "8-12 reps"
            intensity_advice = "Normal working set to hypertrophy depth."
            message = ""

            progress_message = ""

            # --- DYNAMIC TARGETS & COACHING ENGINE ---
            ex_schema = PROGRESSION_SCHEMA.get(exercise)
            total_target_sets = len(ex_schema)

            coaching_data = EXERCISE_COACHING.get(
                exercise, {"reps": "8-12 reps", "advice": "Normal working set to hypertrophy depth."})
            rep_guideline = coaching_data["reps"]
            intensity_advice = coaching_data["advice"]
            # --- UNIFIED PROGRESSION & TIMER LIFE CYCLE ---
            if set_count >= total_target_sets:
                ACTIVE_EXERCISE_SESSIONS.pop(chat_id, None)
                advice = f"**Exercise Complete!** All {
                    total_target_sets} configured sets mapped successfully.\n *Next Move:* Proceed directly to your next movement assignment."
            else:
                next_set_count = set_count + 1
                # Generate specific next-set instructions for the rest reminder configuration
                if "flat dumbbell" in exercise or "flat db" in exercise or "hack squat" in exercise:
                    next_guideline = "8-10 reps (Hypertrophy Back-off)"
                else:
                    next_guideline = rep_guideline

                advice = f" **Set logged smoothly.** Prepare for Set {next_set_count} of {
                    total_target_sets}.\n *Next Target:* {next_guideline}"

                # Append the background rest task for incomplete arrays
                background_tasks.add_task(
                    delayed_rest_reminder,
                    chat_id=chat_id,
                    exercise_name=exercise,
                    next_set=next_set_count,
                    target_desc=next_guideline
                )
            # --- NEW: REAL-TIME SET 2 RECOMMENDATION ---
            next_set_advice = ""
            if set_count < total_target_sets:
                next_set_count = set_count + 1

                # Fetch targets based on the set you JUST completed
                ex_schema = PROGRESSION_SCHEMA.get(exercise)
                current_targets = ex_schema.get(
                    set_count, {"min_reps": 8, "max_reps": 12, "increment": 5})
                min_reps = current_targets['min_reps']
                max_reps = current_targets['max_reps']
                increment = current_targets['increment']

                is_assisted = any(ex in exercise for ex in [
                                  "assisted pull-up", "paused assisted dip"])
                is_reverse_pyramid = any(ex in exercise for ex in [
                                         "hack squat", "smith machine squat"])
                if is_reverse_pyramid:
                    next_targets = ex_schema.get(
                        next_set_count, current_targets)
                    next_max_reps = next_targets['max_reps']
                    drop_weight = max(0, lift_data.weight - increment)
                    next_set_advice = f"\n\n *Next Set Target:* Drop weight for back-off set. Target **{
                        drop_weight} lbs** for {next_max_reps} reps (Reverse Pyramid)."
                elif is_assisted:
                    if lift_data.reps >= max_reps:
                        next_weight = max(0, lift_data.weight - increment)
                        next_set_advice = f"\n\n *Next Set Target:* You crushed the rep cap! Reduce assistance weight down to **{
                            next_weight} lbs**."
                    elif lift_data.reps < min_reps:
                        next_weight = lift_data.weight + increment
                        next_set_advice = f"\n\n *Next Set Target:* That looked heavy. Add assistance up to **{
                            next_weight} lbs** to stay in the target zone."
                    else:
                        next_weight = lift_data.weight
                        next_set_advice = f"\n\n *Next Set Target:* Stick with **{
                            next_weight} lbs** assistance and try to push closer to {max_reps} reps."
                else:
                    if lift_data.reps >= max_reps:
                        next_weight = lift_data.weight + increment
                        next_set_advice = f"\n\n *Next Set Target:* You crushed the rep cap! Bump up to **{
                            next_weight} lbs**."
                    elif lift_data.reps < min_reps:
                        next_weight = max(0, lift_data.weight - increment)
                        next_set_advice = f"\n\n *Next Set Target:* That looked heavy. Drop to **{
                            next_weight} lbs** to stay in the target zone."
                    else:
                        next_weight = lift_data.weight
                        next_set_advice = f"\n\n *Next Set Target:* Stick with **{
                            next_weight} lbs** and try to push closer to {max_reps} reps."

            # Update your final reply to include the dynamic next set advice
            reply_msg = (
                f" **Set {set_count} Tracked to Supabase:**\n"
                f" *{exercise.title()}*\n"
                f" **{lift_data.weight} lbs × {lift_data.reps} reps**\n"
                f" *Prescription Target:* {rep_guideline}\n\n"
                f" {intensity_advice}\n\n"
                f" {next_set_advice}"
            )
            await send_telegram_reply(chat_id, reply_msg)
        else:
            reply = ("Invalid input, try again")
            await send_telegram_reply(chat_id, reply)

        return {"status": "success"}

    except Exception as e:
        print(f"Webhook error: {e}")
        try:
            # Send without Markdown to prevent parsing crashes!
            async with httpx.AsyncClient() as http_client:
                await http_client.post(TELEGRAM_API_URL, json={
                    "chat_id": chat_id,
                    "text": f"Webhook Error: {str(e)}"
                })
        except Exception as inner_e:
            print(f"Failed to even send the error to Telegram: {inner_e}")
        return {"status": "success"}
