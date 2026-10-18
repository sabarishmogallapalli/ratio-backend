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


@app.get("/")
def keep_alive():
    return {"status": "awake"}


EXERCISE_REGISTRY = {
    # EXAMPLE - TESTING
    "test exercise": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Sample advice.",
        "last_set":"*Myo-reps*",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 2.5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 2.5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 2.5},
        },
    },

    "test assisted exercise": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Sample advice.",
        "last_set":"*Myo-reps*",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 2.5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 2.5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 2.5},
        },
    },

    "test reverse pyramid exercise": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Sample advice.",
        "last_set":"*Myo-reps*",
        "sets": {
            1: {"min_reps": 8, "max_reps": 8, "drop_percent": 0.12},
            2: {"min_reps": 10, "max_reps": 12, "drop_percent": 0.12},
            3: {"min_reps": 10, "max_reps": 12, "drop_percent": 0.12},
        },
    },


    # PHASE 1

    "cuffed behind-the-back lateral raise": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Raise cables up/out in a 'Y' motion. Connect with middle delts.",
        "last_set":"*Myo-reps*",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 2.5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 2.5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 2.5},
        },
    },
    "cross-body lat pull-around": {
        "rest_seconds": 120,
        "warmup_sets": 1,
        "advice": "Wrist/cable aligned in a straight line. Deep lat stretch at top.",
        "last_set":"*Long-length Partials*",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "low incline smith machine press": {
        "rest_seconds": 120,
        "warmup_sets": 2,
        "advice": "~15° incline. 1s pause on chest.",
        "last_set":"*30s Pec Static Stretch*",
        "sets": {
            1: {"min_reps": 8, "max_reps": 10, "increment": 5},
            2: {"min_reps": 8, "max_reps": 10, "increment": 5},
            3: {"min_reps": 8, "max_reps": 10, "increment": 5},
            4: {"min_reps": 8, "max_reps": 10, "increment": 5},
        },
    },
    "chest-supported machine row": {
        "rest_seconds": 120,
        "warmup_sets": 1,
        "advice": "Flare elbows ~45° and squeeze blades hard at top.",
        "last_set":"*Long-length Partials*",
        "sets": {
            1: {"min_reps": 8, "max_reps": 10, "increment": 10},
            2: {"min_reps": 8, "max_reps": 10, "increment": 10},
            3: {"min_reps": 8, "max_reps": 10, "increment": 10},
        },
    },
    "overhead cable tricep extensions (bar)": {
        "rest_seconds": 120,
        "warmup_sets": 1,
        "advice": "Nasty stretch on negative, 1s pause at bottom.",
        "last_set":"*Dropset*",
        "sets": {
            1: {"min_reps": 8, "max_reps": 10, "increment": 5},
            2: {"min_reps": 8, "max_reps": 10, "increment": 5},
        },
    },
    "straight-bar lat prayer": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Lean forward for big lat stretch at top, stand upright at bottom.",
        "last_set":"*Long-length Partials*",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 5},
            2: {"min_reps": 12, "max_reps": 15, "increment": 5},
            3: {"min_reps": 12, "max_reps": 15, "increment": 5},
        },
    },
    "pec deck (with integrated partials)": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "*Integrated Partials:* Alternate 1 full-ROM rep with 1 half-ROM rep in stretched position.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 15},
            2: {"min_reps": 12, "max_reps": 15, "increment": 15},
            3: {"min_reps": 12, "max_reps": 15, "increment": 15},
        },
    },
    "seated leg curl": {
        "rest_seconds": 120,
        "warmup_sets": 1,
        "advice": "Lean forward over machine for maximum hamstring stretch.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 10, "increment": 10},
            2: {"min_reps": 8, "max_reps": 10, "increment": 10},
            3: {"min_reps": 8, "max_reps": 10, "increment": 10},
        },
    },
    "machine hip adduction": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Mind-muscle connection with inner thighs. Push hard!",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 10},
            2: {"min_reps": 10, "max_reps": 12, "increment": 10},
            3: {"min_reps": 10, "max_reps": 12, "increment": 10},
        },
    },
    "hack squat": {
        "rest_seconds": 180,
        "warmup_sets": 3,
        "advice": "Reverse Pyramid: Set 1 heaviest (4 reps). Set 2 drop ~10-15% (6 reps). Set 3 drop ~10-15% (8 reps).",
        "last_set":"",
        "sets": {
            1: {"min_reps": 4, "max_reps": 4, "increment": 5},
            2: {"min_reps": 6, "max_reps": 6, "drop_percent": 0.12},
            3: {"min_reps": 8, "max_reps": 8, "drop_percent": 0.12},
        },
    },
    "leg extension": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Pull butt down into seat. 2-3s negative.",
        "last_set":"*Long-length Partials*",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "leg press calf press": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "1-2s pause at bottom. Roll ankles on balls of feet.",
        "last_set":"*30s Calf Static Stretch*",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 20},
            2: {"min_reps": 12, "max_reps": 15, "increment": 20},
            3: {"min_reps": 12, "max_reps": 15, "increment": 20},
        },
    },
    "super-rom overhand cable row": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Wide grip pulldown bar. Lean forward on negative, upright at finish.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "machine shoulder press": {
        "rest_seconds": 60,
        "warmup_sets": 2,
        "advice": "Elbows break 90°. Smooth, controlled reps.",
        "last_set":"*Dropset*",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "assisted pull-up": {
        "rest_seconds": 120,
        "warmup_sets": 1,
        "advice": "Slow 2-3s negative. 0.5-1s pause at bottom.",
        "last_set":"*Long-length Partials*",
        "sets": {
            1: {"min_reps": 8, "max_reps": 10, "increment": 5},
            2: {"min_reps": 8, "max_reps": 10, "increment": 5},
            3: {"min_reps": 8, "max_reps": 10, "increment": 5},
        },
    },
    "paused assisted dip": {
        "rest_seconds": 120,
        "warmup_sets": 2,
        "advice": "Slow 2-3s negative. 1-2s pause at bottom. Break 90° elbow angle.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 10, "increment": 5},
            2: {"min_reps": 8, "max_reps": 10, "increment": 5},
            3: {"min_reps": 8, "max_reps": 10, "increment": 5},
        },
    },
    "inverse dumbbell zottman curl": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Hammer curl on positive, palms-up grip on negative.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "super-rom dumbbell lateral raise": {
        "rest_seconds": 30,
        "warmup_sets": 1,
        "advice": "Hands overhead. Squeeze upper traps at top. Point thumbs up if shoulder hurts.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 5},
            2: {"min_reps": 12, "max_reps": 15, "increment": 5},
            3: {"min_reps": 12, "max_reps": 15, "increment": 5},
        },
    },
    "cable reverse flye (mechanical dropset)": {
        "rest_seconds": 60,
        "warmup_sets": 0,
        "advice": "*Mechanical Dropset:* 3 steps back (5 reps) -> 1 step fwd (4 reps) -> 1 step fwd (3+ reps). No rest!",
        "last_set":"",
        "sets": {
            1: {"min_reps": 5, "max_reps": 5, "increment": 5},
            2: {"min_reps": 5, "max_reps": 5, "increment": 5},
            3: {"min_reps": 5, "max_reps": 5, "increment": 5},
        },
    },
    "lying leg curl": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Big stretch at bottom. Keep hips down.",
        "last_set":"*Long-length Partials*",
        "sets": {
            1: {"min_reps": 8, "max_reps": 10, "increment": 5},
            2: {"min_reps": 8, "max_reps": 10, "increment": 5},
            3: {"min_reps": 8, "max_reps": 10, "increment": 5},
        },
    },
    "leg press": {
        "rest_seconds": 120,
        "warmup_sets": 2,
        "advice": "Feet low for quad focus. Deep stretch with slight pause at bottom.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 8, "increment": 5},
            2: {"min_reps": 8, "max_reps": 8, "increment": 5},
            3: {"min_reps": 8, "max_reps": 8, "increment": 5},
        },
    },
    "paused barbell rdl": {
        "rest_seconds": 180,
        "warmup_sets": 2,
        "advice": "Low RPE (~6-7). 1s pause at bottom. Stop 75% to lockout to keep tension.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 8, "increment": 5},
            2: {"min_reps": 8, "max_reps": 8, "increment": 5},
        },
    },
    "sissy squat": {
        "rest_seconds": 30,
        "warmup_sets": 1,
        "advice": "Knees forward past toes. Push hard!",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 0},
            2: {"min_reps": 10, "max_reps": 12, "increment": 0},
            3: {"min_reps": 10, "max_reps": 12, "increment": 0},
        },
    },
    "seated calf raise": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "1-2s pause at bottom.",
        "last_set":"*30s Calf Static Stretch*",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 15},
            2: {"min_reps": 10, "max_reps": 12, "increment": 15},
            3: {"min_reps": 10, "max_reps": 12, "increment": 15},
        },
    },
    "bayesian cable curl": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Start with weaker arm if imbalanced. Take weaker arm to RPE 9-10, then match reps with other arm.",
        "last_set":"*Long-length Partials*",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "seated dumbbell french press": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Palms under top of dumbbell. Deep stretch at bottom. Avoid pausing at the top of each rep.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 10, "increment": 5},
            2: {"min_reps": 10, "max_reps": 10, "increment": 5},
            3: {"min_reps": 10, "max_reps": 10, "increment": 5},
        },
    },
    "bottom-2/3 constant tension preacher curl": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Stay in bottom 2/3. No pausing at top or bottom—constant tension!",
        "last_set":"",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 5},
            2: {"min_reps": 12, "max_reps": 15, "increment": 5},
        },
    },
    "cable triceps kickback": {
        "rest_seconds": 60,
        "warmup_sets": 0,
        "advice": "Upright or bent over. At full squeeze, keep shoulder positioned behind torso.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 5},
            2: {"min_reps": 12, "max_reps": 15, "increment": 5},
        },
    },
    "cable crunch": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Round your lower back as you crunch. Maintain mind-muscle connection with your 6-pack.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },

    # PHASE 2

    "lat-focused cable row": {
        "rest_seconds": 120,
        "warmup_sets": 1,
        "advice": "Keep elbows tucked close to your sides to bias the lats.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "low incline dumbbell press": {
        "rest_seconds": 120,
        "warmup_sets": 2,
        "advice": "Bench at 15° incline. Slight elbow tuck on negative then flare as you push. Constant tension on pecs.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 10, "increment": 5},
            2: {"min_reps": 8, "max_reps": 10, "increment": 5},
            3: {"min_reps": 8, "max_reps": 10, "increment": 5},
        },
    },
    "machine chest-supported row + kelso shrug": {
        "rest_seconds": 120,
        "warmup_sets": 2,
        "advice": "Row 8-10 reps (elbows ~45°). Without resting, complete 4-6 Kelso shrugs.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 10, "increment": 5},
            2: {"min_reps": 8, "max_reps": 10, "increment": 5},
            3: {"min_reps": 8, "max_reps": 10, "increment": 5},
        },
    },
    "bent-over cable pec flye (w/ integrated partials)": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Torso parallel to floor, flye down toward the floor. Stretched squeeze.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 5},
            2: {"min_reps": 12, "max_reps": 15, "increment": 5},
            3: {"min_reps": 12, "max_reps": 15, "increment": 5},
        },
    },
    "1-arm lat pull-in": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Pull cable from the side. Connect with lats, avoid bicep takeover.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 5},
            2: {"min_reps": 12, "max_reps": 15, "increment": 5},
        },
    },
    "dual-cable triceps press": {
        "rest_seconds": 120,
        "warmup_sets": 1,
        "advice": "Hold cables without handle at chin level. Press forward straight out in front.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "smith machine squat": {
        "rest_seconds": 180,
        "warmup_sets": 2,
        "advice": "Reverse Pyramid: Set 1 heaviest (4 reps). Set 2 drop ~10-15% (6 reps). Set 3 drop ~10-15% (8 reps).",
        "last_set":"",
        "sets": {
            1: {"min_reps": 4, "max_reps": 4, "increment": 5},
            2: {"min_reps": 6, "max_reps": 6, "drop_percent": 0.12},
            3: {"min_reps": 8, "max_reps": 8, "drop_percent": 0.12},
        },
    },
    "dumbbell calf jumps": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Jumping motion without leaving floor; drive jump using calves/ankles.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 5},
            2: {"min_reps": 12, "max_reps": 15, "increment": 5},
            3: {"min_reps": 12, "max_reps": 15, "increment": 5},
        },
    },
    "dual-handle lat pulldown (mid-back + lats)": {
        "rest_seconds": 120,
        "warmup_sets": 1,
        "advice": "Lean back 15° and drive elbows down squeezing shoulder blades together.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "seated dumbbell shoulder press": {
        "rest_seconds": 60,
        "warmup_sets": 2,
        "advice": "Rotate dumbbells slightly inward on negative, flare elbows on push.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "decline machine chest press": {
        "rest_seconds": 120,
        "warmup_sets": 2,
        "advice": "Feel pecs stretch apart on negative. Focus on lower pecs.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 10, "increment": 5},
            2: {"min_reps": 8, "max_reps": 10, "increment": 5},
            3: {"min_reps": 8, "max_reps": 10, "increment": 5},
        },
    },
    "concentration cable curl": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Place working elbow against knee and perform strict form curls.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "cross-body cable y-raise": {
        "rest_seconds": 120,
        "warmup_sets": 3,
        "advice": "Sweep arm up, out, and across body like drawing a sword.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "rear delt 45 degrees cable flye": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Pull 1 arm at a time bracing with other hand. Align arm & cable in a line.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 5},
            2: {"min_reps": 12, "max_reps": 15, "increment": 5},
            3: {"min_reps": 12, "max_reps": 15, "increment": 5},
        },
    },
    "smith machine reverse lunge": {
        "rest_seconds": 60,
        "warmup_sets": 2,
        "advice": "Set leg back on negative; drive weight up through front heel.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 8, "increment": 5},
            2: {"min_reps": 8, "max_reps": 8, "increment": 5},
            3: {"min_reps": 8, "max_reps": 8, "increment": 5},
        },
    },
    "glute-ham raise": {
        "rest_seconds": 180,
        "warmup_sets": 2,
        "advice": "Cut out top 25% of ROM to keep hamstrings fully loaded.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 8, "increment": 5},
            2: {"min_reps": 8, "max_reps": 8, "increment": 5},
            3: {"min_reps": 8, "max_reps": 8, "increment": 5},
        },
    },
    "machine hip abduction": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Mind-muscle connection with glute medius / outer hips. Push hard!",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 10},
            2: {"min_reps": 10, "max_reps": 12, "increment": 10},
            3: {"min_reps": 10, "max_reps": 12, "increment": 10},
        },
    },
    "slow-eccentric ez-bar skull crusher": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "3-4s negative. Arc bar behind head; keep bar behind eye line on extension.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "slow-eccentric bayesian curl": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "3-4s negative with bottom pause.",
        "last_set":"*Long-length partials on all reps*",
        "sets": {
            1: {"min_reps": 10, "max_reps": 12, "increment": 5},
            2: {"min_reps": 10, "max_reps": 12, "increment": 5},
            3: {"min_reps": 10, "max_reps": 12, "increment": 5},
        },
    },
    "tricep diverging pressdown (long rope or 2 ropes)": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Flare elbows slightly out and keep arms back in line with torso. Big bottom squeeze.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 5},
            2: {"min_reps": 12, "max_reps": 15, "increment": 5},
        },
    },
    "reverse grip cable curl": {
        "rest_seconds": 60,
        "warmup_sets": 0,
        "advice": "Palms facing down. Targets forearm extensors, brachialis, and biceps.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 12, "max_reps": 15, "increment": 5},
            2: {"min_reps": 12, "max_reps": 15, "increment": 5},
        },
    },
    "roman chair leg raise": {
        "rest_seconds": 60,
        "warmup_sets": 0,
        "advice": "Allow lower back to round as you curl legs up. Push to RPE 9-10 with clean form.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 10, "max_reps": 20, "increment": 5},
            2: {"min_reps": 10, "max_reps": 20, "increment": 5},
            3: {"min_reps": 10, "max_reps": 20, "increment": 5},
        },
    },

    # WEAK POINTS

    "machine lateral raise": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Focus on pushing the weight out rather than up. Keep a slight bend in the elbows.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "dumbbell lateral raise": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Slight lean forward, lead with elbows. Stop at shoulder height.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "smith machine shoulder press": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Bench to high incline. Lower bar with control to chin/upper chest level.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "standing dumbbell arnold press": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Start with palms facing you, rotate palms forward as you press overhead.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "cable lat prayer": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Lean forward for big lat stretch at top, stand upright at bottom.",
        "last_set":"*Long-length Partials*",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "dumbbell lat pullover": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Keep elbows slightly bent. Feel the stretch in your lats, not your chest.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "machine lat pullover": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Drive elbows down and back. Deep stretch at the top.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "elbows-in 1-arm dumbbell row": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Pull dumbbell toward your hip. Squeeze the lat at the top.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "half-kneeling 1-arm lat pulldown": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Kneel on the same side you are pulling with. Drive elbow straight down.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "reverse nordics": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Keep a straight line from knees to shoulders. Control descent into quad stretch.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "single-leg leg press": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Place foot lower on the platform for quad focus. Avoid locking out knee.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "cable hip abduction": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Keep torso stationary. Pull the cable away using only your glutes.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "lateral band walk": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Keep tension on band at all times. Do not drag trailing foot.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "barbell hip thrust": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Tuck chin, drive through heels, and squeeze glutes hard at lockout.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "single-leg dumbbell hip thrust": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Keep core braced and hinge at hips. Push through working heel.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "low incline dumbbell flye": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Slight bend in elbows. Maximize stretch at bottom without shoulder pain.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "low-to-high cable crossover": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Pull from low to high to target upper pecs. Squeeze at the top.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "chest press machine (incline if upper pecs lagging, flat if entire chest is lagging)": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Keep chest up and shoulders retracted. Push smoothly through palms.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "dumbbell chest press (incline if upper pecs lagging, flat if entire chest is lagging)": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Control negative. Deep stretch at bottom before pressing up.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "plate loaded neck curls": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Slow, controlled reps. Tuck chin to chest at top.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "head harness neck extension": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Do not jerk weight. Extend smoothly to activate neck extensors.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },
    "plate-loaded neck extension": {
        "rest_seconds": 60,
        "warmup_sets": 1,
        "advice": "Maintain strict control. Focus on stretch and contraction.",
        "last_set":"",
        "sets": {
            1: {"min_reps": 8, "max_reps": 12, "increment": 5},
            2: {"min_reps": 8, "max_reps": 12, "increment": 5},
            3: {"min_reps": 8, "max_reps": 12, "increment": 5},
        },
    },

}

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
        "ex1": ["Low Incline Dumbbell Flye", "Low-To-High Cable Crossover"],
        "ex2": ["Chest Press Machine (incline if upper pecs lagging, flat if entire chest is lagging)", "Dumbbell Chest Press (incline if upper pecs lagging, flat if entire chest is lagging)"]
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


def normalize_str(s: str) -> str:
    s = s.lower().replace("-", " ").replace("/", " ").replace("_", " ")
    words = ["dumbbell" if w == "db" else w for w in s.split()]
    return "".join(words)


def match_exercise(raw_name: str) -> Optional[str]:
    clean = normalize_str(raw_name)
    for ex in EXERCISE_REGISTRY.keys():
        if normalize_str(ex) == clean:
            return ex
    return None


def define_meal() -> str:
    central_tz = zoneinfo.ZoneInfo("America/Chicago")
    current_hour = datetime.now(central_tz).hour
    if 5 <= current_hour < 11:
        return "breakfast"
    elif 11 <= current_hour < 14:
        return "lunch"
    elif 19 <= current_hour < 22:
        return "dinner"
    else:
        return "snack"


def generate_warmup_guide(warmup_count: int, working_weight: float, exercise_name: str = "") -> str:
    if warmup_count == 0 or working_weight <= 0:
        return "• *No warm-up sets required—jump straight into Working Set 1!*"

    is_assisted = any(x in exercise_name.lower() for x in ["assisted pull-up", "assisted dip"])

    if warmup_count == 1:
        multiplier = 1.40 if is_assisted else 0.60
        pct_text = "~140%" if is_assisted else "~60%"
        w1 = round((working_weight * multiplier) / 5) * 5
        return f"• Warm-Up Set 1: {w1} lbs × 6-10 reps ({pct_text})"
    elif warmup_count == 2:
        m1 = 1.50 if is_assisted else 0.50
        m2 = 1.30 if is_assisted else 0.70
        pct1 = "~150%" if is_assisted else "~50%"
        pct2 = "~130%" if is_assisted else "~70%"
        w1 = round((working_weight * m1) / 5) * 5
        w2 = round((working_weight * m2) / 5) * 5
        return f"• Warm-Up Set 1: {w1} lbs × 6-10 reps ({pct1})\n• Warm-Up Set 2: {w2} lbs × 4-6 reps ({pct2})"
    elif warmup_count >= 3:
        m1 = 1.55 if is_assisted else 0.45
        m2 = 1.35 if is_assisted else 0.65
        m3 = 1.15 if is_assisted else 0.85
        pct1 = "~155%" if is_assisted else "~45%"
        pct2 = "~135%" if is_assisted else "~65%"
        pct3 = "~115%" if is_assisted else "~85%"
        w1 = round((working_weight * {m1}) / 5) * 5
        w2 = round((working_weight * {m2}) / 5) * 5
        w3 = round((working_weight * {m3}) / 5) * 5
        return f"• Warm-Up Set 1: {w1} lbs × 6-10 reps ({pct1})\n• Warm-Up Set 2: {w2} lbs × 4-6 reps ({pct2})\n• Warm-Up Set 3: {w3} lbs × 3-4 reps ({pct3})"


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


async def get_usda_macros(food_query: str, upc: Optional[str] = None):
    queries_to_try = []
    if upc:
        clean_upc = upc.strip()
        queries_to_try.append(clean_upc)
        # 14-digit GTIN padded variant
        padded_14 = clean_upc.zfill(14)
        if padded_14 not in queries_to_try:
            queries_to_try.append(padded_14)
        # Extra fallback for datasets padding with 3 zeros
        if len(clean_upc) == 12:
            queries_to_try.append(f"000{clean_upc}")
    else:
        queries_to_try.append(food_query)

    async with httpx.AsyncClient() as client:
        for q in queries_to_try:
            if upc:
                url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={
                    USDA_API_KEY}&query={q}&dataType=Branded&pageSize=3"
            else:
                url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_API_KEY}&query={
                    q}&pageSize=3&dataType=Foundation,Survey%20(FNDDS),Branded,SR%20Legacy"

            try:
                response = await client.get(url)
                data = response.json()
                options = []
                if data.get('foods'):
                    for food in data['foods'][:3]:
                        label_nuts = food.get('labelNutrients')
                        if label_nuts and 'calories' in label_nuts:
                            calories = label_nuts['calories'].get('value', 0)
                            protein = label_nuts.get('protein', {}).get('value', 0)
                            carbs = label_nuts.get('carbohydrates', {}).get('value', 0)
                            fat = label_nuts.get('fat', {}).get('value', 0)
                        else:
                            nutrients = food.get('foodNutrients', [])
                            raw_calories = next((n['value'] for n in nutrients if 'Energy' in n.get('nutrientName', '')), 0)
                            raw_protein = next((n['value'] for n in nutrients if 'Protein' in n.get('nutrientName', '')), 0)
                            raw_carbs = next((n['value'] for n in nutrients if 'Carbohydrate' in n.get('nutrientName', '')), 0)
                            raw_fat = next((n['value'] for n in nutrients if 'Total lipid' in n.get('nutrientName', '')), 0)

                            serving_grams = food.get('servingSize', 100.0)
                            scale_factor = serving_grams / 100.0

                            calories = raw_calories * scale_factor
                            protein = raw_protein * scale_factor
                            carbs = raw_carbs * scale_factor
                            fat = raw_fat * scale_factor
                        serving_unit = food.get('householdServingFullText') or f"{food.get('servingSize', 100)} {food.get('servingSizeUnit', 'g')}"
                        options.append({
                            "food_name": food.get('description', 'Unknown Food'),
                            "serving_size": serving_unit,
                            "calories": round(calories),
                            "protein": round(protein, 1),
                            "carbs": round(carbs, 1),
                            "fat": round(fat, 1)
                        })
                    if options:
                        return options
            except Exception as e:
                print(f"USDA API Error: {e}")
                return []
    return []


async def delayed_rest_reminder(chat_id: int, exercise_name: str, next_set: int, target_desc: str, next_set_advice: str):
    ex_data = EXERCISE_REGISTRY.get(exercise_name.lower(), {})
    rest_seconds = ex_data.get("rest_seconds", 180)

    await asyncio.sleep(rest_seconds)

    today_str = date.today().isoformat()
    existing_sets = supabase.table("exercise_logs") \
        .select("id") \
        .eq("exercise_name", exercise_name) \
        .eq("is_warmup", False) \
        .gte("created_at", today_str) \
        .execute()

    if len(existing_sets.data) >= next_set:
        return

    if rest_seconds >= 60:
        rest_mins = rest_seconds / 60
        rest_label = f"{int(rest_mins) if rest_mins.is_integer() else rest_mins:g}-Minute"
    else:
        rest_label = f"{rest_seconds}-Second"

    reminder = (
        f"*{rest_label} Rest Over!*\n"
        f"Time for *Set {next_set}* of *{exercise_name.title()}*.\n"
        f"{next_set_advice}"
    )
    await send_telegram_reply(chat_id, reminder)


async def handle_workout_completion(chat_id: int) -> str:

    profile_res = supabase.table("user_profiles").select(
        "workouts_completed_this_week, current_week, current_phase"
    ).eq("chat_id", chat_id).execute()

    if not profile_res.data:
        return "Profile not found. Please set up your baseline first!"

    profile = profile_res.data[0]
    workouts_completed = profile.get("workouts_completed_this_week", 0) + 1
    current_week = profile.get("current_week", 1)
    current_phase = profile.get("current_phase", 1)

    if workouts_completed >= 5:
        workouts_completed = 0
        current_week += 1

        if current_week > 5:
            current_week = 1
            if current_phase == "Phase 1":
                current_phase = "Phase 2"
            elif current_phase == "Phase 2":
                current_phase = "Phase 1"

    supabase.table("user_profiles").update({
        "workouts_completed_this_week": workouts_completed,
        "current_week": current_week,
        "current_phase": current_phase
    }).eq("chat_id", chat_id).execute()

    return f" *Workout Complete!*\n\nYou are currently on:\n• Phase {current_phase}\n• Week {current_week}\n• Sessions this week: {workouts_completed}/4"


async def build_exercise_session_targets(exercise_name: str, chat_id: int) -> str:
    profile_res = (
        supabase.table("user_profiles")
        .select("current_phase, current_week")
        .eq("chat_id", chat_id)
        .execute()
    )
    if profile_res.data:
        current_phase = profile_res.data[0].get("current_phase", "Phase 1")
        current_week = profile_res.data[0].get("current_week", 1)
    else:
        current_phase = "Phase 1"
        current_week = 1

    ex_info = EXERCISE_REGISTRY.get(
        exercise_name,
        {
            "warmup_sets": 1,
            "advice": "Hypertrophy depth working set.",
            "last_set": "",
            "sets": {1: {"min_reps": 8, "max_reps": 12, "increment": 5}},
        },
    )
    sets_config = ex_info.get("sets", {})
    intensity_advice = ex_info.get("advice", "Hypertrophy depth working set.")
    warmup_count = ex_info.get("warmup_sets", 0)

    set_1_targets = sets_config.get(1, {"min_reps": 8, "max_reps": 12, "increment": 5})
    target_max_reps = set_1_targets.get("max_reps", 12)
    increment = set_1_targets.get("increment", 5)

    deload_label = " - Semi-Deload Week" if current_week % 5 == 0 else ""
    phase_header = f"Current Plan: {current_phase} (Week {current_week}{deload_label})\n"

    note_res = (
        supabase.table("user_exercise_notes")
        .select("note")
        .eq("chat_id", chat_id)
        .eq("exercise_name", exercise_name)
        .execute()
    )
    custom_note = note_res.data[0]["note"] if note_res.data else None

    today_str = date.today().isoformat()
    history = (
        supabase.table("exercise_logs")
        .select("weight, reps, set_number, created_at")
        .eq("exercise_name", exercise_name)
        .lt("created_at", today_str)
        .order("created_at", desc=True)
        .limit(25)
        .execute()
    )

    if not history.data:
        target_working_weight = 0
        rec_text = f"Load up 0 lbs for Set 1 today and aim for {target_max_reps} reps!"
        last_session_block = (
            f"No history found for {exercise_name.title()}!\n"
            "Start with a light weight to establish your baseline today.\n\n"
        )
    else:
        last_date = history.data[0]["created_at"][:10]
        last_session = [r for r in history.data if r["created_at"].startswith(last_date)]
        history_text = "\n".join(
            f"• Set {r['set_number']}: {r['weight']} lbs × {r['reps']} reps"
            for r in sorted(last_session, key=lambda x: x["set_number"])
        )
        last_session_block = f"*Last Session: {exercise_name.title()}* ({last_date})\n\n{history_text}\n\n"

        heaviest_set = max(last_session, key=lambda x: x["weight"])
        successful_at_top = [s for s in last_session if s["reps"] >= target_max_reps]

        if successful_at_top:
            best_top_set = max(successful_at_top, key=lambda x: x["weight"])
            target_working_weight = best_top_set["weight"] + increment
            rec_text = f"*{target_working_weight} lbs* for *{target_max_reps} reps* Set 1 today!"
        else:
            target_working_weight = heaviest_set["weight"]
            rec_text = ( 
                 f"Keep working with *{target_working_weight} lbs* today until you hit *{target_max_reps} reps*!"
            )

    schema_lines = []
    current_weight = target_working_weight

    for s, data in sorted(sets_config.items()):
        min_reps = data.get("min_reps", 8)
        max_reps = data.get("max_reps", 12)
        if s == 1:
            weight_str = f" @ {current_weight} lbs" if current_weight > 0 else ""
            schema_lines.append(f"• Set 1: {max_reps} reps")
        elif "drop_percent" in data:
            if current_weight > 0:
                drop_pct = data["drop_percent"]
                current_weight = round((current_weight * (1 - drop_pct)) / 5) * 2.5
                schema_lines.append(f"• Set {s}: {min_reps} - {max_reps} reps")
            else:
                schema_lines.append(f"• Set {s}: {min_reps} - {max_reps} reps")
        else:
            schema_lines.append(f"• Set {s}: {min_reps} - {max_reps} reps")

    schema_text = "\n".join(schema_lines)

    # 3. Handle Warmup Guide & Final Formatting
    if not history.data:
        warmup_guide = ""
    else:
        warmup_guide = generate_warmup_guide(warmup_count, target_working_weight, exercise_name)
    
    cues_block = f"Technique Cues: {intensity_advice}"
    if custom_note:
        cues_block += f"\n\n **Setup Note:** {custom_note}"

    last_set = ex_info.get("last_set", "")

    return (
        f"{phase_header}"
        f"{exercise_name.title()}\n"
        # f"{last_session_block}"
        f"{rec_text}\n\n"
        f"{warmup_guide}\n"
        f"{schema_text}\n"
        f"{cues_block}\n"
        f"Last Set Variation: {last_set}"
    )


async def process_and_save_meal(chat_id: int, food_data: FoodStructure):
    central_tz = zoneinfo.ZoneInfo("America/Chicago")
    if food_data.extracted_date:
        dt = datetime.strptime(food_data.extracted_date, "%Y-%m-%d").replace(hour=12, tzinfo=central_tz)
        created_timestamp = dt.isoformat()
    else:
        created_timestamp = datetime.now(central_tz).isoformat()
    meal_type = food_data.extracted_meal_type if food_data.extracted_meal_type else define_meal()
    created_timestamp = f"{
        food_data.extracted_date}T12:00:00-05:00" if food_data.extracted_date else datetime.now(central_tz).isoformat()

    insert_payload = {
        "meal_type": meal_type,
        "food_name": food_data.food_name,
        "calories": food_data.calories,
        "protein": food_data.protein,
        "carbs": food_data.carbs,
        "fat": food_data.fat,
        "created_at": created_timestamp
    }

    supabase.table("food_logs").insert(insert_payload).execute()

    central_tz = zoneinfo.ZoneInfo("America/Chicago")
    now = datetime.now(central_tz)
    start_of_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_str = start_of_today.isoformat()
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
        target_carb = profile.data[0]['target_carbs']
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
        )
        advice_res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": advice_prompt}],
            model="openai/gpt-oss-20b"
        )
        coach_advice = advice_res.choices[0].message.content.strip()
        daily_summary = (
            f"\n\n *Daily Status:*\n"
            f" Protein: {total_pro}g / {
                target_pro}g *(Need {rem_pro}g more)*\n"
            f" Carbohydrates: *{total_carb}* / {round(target_carb)}\n"
            f" Fat: *{total_fat}* / {round(target_fat)}\n"
            f" Calories: *{total_cal}* / {round(target_cal)}\n\n"
            f" *{coach_advice}*"
        )
    else:
        daily_summary = "\n\n *Profile not found in database. Add your baseline to get macro coaching!*"

    reply = (
        f" {meal_type.capitalize()}:\n"
        f" *{food_data.food_name.title()}*\n"
        f" {food_data.calories} kcal | {food_data.protein}g P | {
            food_data.carbs}g C | {food_data.fat}g F"
        f"{daily_summary}"
    )

    await send_telegram_reply(chat_id, reply)


@app.post("/api/v1/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    chat_id = None
    try:
        payload = await request.json()
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return {"status": "error", "message": "Invalid JSON"}

    try:
        if "callback_query" in payload:
            callback = payload["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            callback_data = callback["data"]

            if callback_data == "action_finish_workout":
                reply_text = await handle_workout_completion(chat_id)

                await send_telegram_reply(chat_id, reply_text)

                message_id = callback["message"]["message_id"]

                async with httpx.AsyncClient() as http_client:
                    await http_client.post(
                        f"https://api.telegram.org/bot{
                            TELEGRAM_TOKEN}/answerCallbackQuery",
                        json={"callback_query_id": callback["id"]}
                    )

                    await http_client.post(
                        f"https://api.telegram.org/bot{
                            TELEGRAM_TOKEN}/editMessageReplyMarkup",
                        json={
                            "chat_id": chat_id,
                            "message_id": message_id,
                            "reply_markup": {"inline_keyboard": []}
                        }
                    )
                return {"status": "success"}

            if callback_data.startswith("wp_") and not callback_data.startswith("wp_ex_"):
                wp_key = callback_data.replace("wp_", "")
                if wp_key in WEAK_POINTS_TABLE:
                    wp_data = WEAK_POINTS_TABLE[wp_key]

                    keyboard_buttons = []
                    if isinstance(wp_data, str):
                        reply_text = f"**{wp_key.title()
                                          } Advice:**\n\n{wp_data}"
                    else:
                        reply_text = f"**{
                            wp_data['title']} Weak Point Options**\n\nSelect an exercise below to view its targets and cues. *Do not do all of them in one day!*"
                        for ex in wp_data['ex1']:
                            keyboard_buttons.append(
                                [{"text": f"Ex 1: {ex}", "callback_data": f"wp_ex_{ex.lower()}"}])
                        for ex in wp_data['ex2']:
                            keyboard_buttons.append(
                                [{"text": f"Ex 2: {ex}", "callback_data": f"wp_ex_{ex.lower()}"}])
                    async with httpx.AsyncClient() as http_client:
                        await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", json={
                            "chat_id": chat_id,
                            "message_id": callback["message"]["message_id"],
                            "text": reply_text,
                            "parse_mode": "Markdown",
                            "reply_markup": {"inline_keyboard": keyboard_buttons}
                        })
                        await http_client.post(
                            f"https://api.telegram.org/bot{
                                TELEGRAM_TOKEN}/answerCallbackQuery",
                            json={"callback_query_id": callback["id"]}
                        )
                return {"status": "success"}
            workout_prefixes = ["test_", "p1u1_", "p1u2_", "p1l1_", "p1l2_",
                                "p1a_", "p2u1_", "p2u2_", "p2l1_", "p2l2_", "p2a_", "wp_ex_"]
            if any(callback_data.startswith(p) for p in workout_prefixes):
                raw_slug = callback_data
                for prefix in workout_prefixes:
                    if raw_slug.startswith(prefix):
                        raw_slug = raw_slug.replace(prefix, "")
                        break
                exercise_name = match_exercise(
                    raw_slug) or raw_slug.replace("-", " ").lower().strip()
                ACTIVE_EXERCISE_SESSIONS[chat_id] = exercise_name

                reply_text = await build_exercise_session_targets(exercise_name, chat_id)

                async with httpx.AsyncClient() as http_client:
                    await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", json={
                        "chat_id": chat_id,
                        "message_id": callback["message"]["message_id"],
                        "text": reply_text,
                        "parse_mode": "Markdown",
                        "reply_markup": callback["message"].get("reply_markup")
                    })

                async with httpx.AsyncClient() as http_client:
                    await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback["id"]})
                return {"status": "success"}

            if chat_id not in PENDING_LOGS:
                await send_telegram_reply(chat_id, "Session expired. Please re-enter your meal.")
                return {"status": "success"}

            pending_data = PENDING_LOGS[chat_id]
            raw_text = pending_data["raw_text"]

            if callback_data == "choice_usda":
                usda_results = await get_usda_macros(raw_text)
                
                if usda_results:
                    pending_data["usda_options"] = usda_results
                    keyboard = {"inline_keyboard": []}
                    msg_text = f"Found {len(usda_results)} USDA results for *{raw_text}*:\nSelect the most accurate option:"
                    
                    for i, item in enumerate(usda_results):
                        clean_name = item['food_name'].replace("'", "").replace("*", "")[:28]
                        btn_text = f"{clean_name}... ({item['calories']} kcal)"
                        keyboard["inline_keyboard"].append([{"text": btn_text, "callback_data": f"usda_{i}"}])
                    
                    keyboard["inline_keyboard"].append([{"text": "Fallback to AI Estimation", "callback_data": "choice_ai"}])
                    keyboard["inline_keyboard"].append([{"text": "Manual Macros Entry", "callback_data": "manual_entry"}])
                else:
                    msg_text = f"No exact USDA matches found for *{raw_text}*.\n Try with a different description or Would you like to use AI estimation instead?"
                    keyboard = {
                        "inline_keyboard": [
                            [{"text": "Use AI Estimation", "callback_data": "choice_ai"}],
                            [{"text": "Manual Macros Entry", "callback_data": "manual_entry"}]
                        ]
                    }

                async with httpx.AsyncClient() as http_client:
                    await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", json={
                        "chat_id": chat_id,
                        "message_id": callback["message"]["message_id"],
                        "text": msg_text,
                        "parse_mode": "Markdown",
                        "reply_markup": keyboard
                    })
                    await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback["id"]})
                return {"status": "success"}

            elif callback_data.startswith("usda_"):
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
            elif callback_data == "choice_ai":
                schema_string = json.dumps(FoodStructure.model_json_schema())
                system_instructions = (
                    f"You are an expert nutritionist and precise calorie calculator. "
                    f"Calculate macros for: '{raw_text}'. "
                    f"Return ONLY a valid JSON object matching this schema exactly: {schema_string}. "
                    "CRITICAL: Return a flat JSON object. Extract 'extracted_date' and 'extracted_meal_type' if present."
                )
            elif callback_data == "manual_entry":
                PENDING_LOGS[chat_id] = {"awaiting_manual_input": True}
                msg = (
                    "*Manual Entry Mode*\n\n"
                    "Reply with your meal details in this exact format:\n"
                    "`Food Name | Calories | Protein | Carbs | Fat`\n\n"
                    "_Example: Grilled Chicken | 450 | 40 | 10 | 8_"
                )
                async with httpx.AsyncClient() as http_client:
                    # Remove the inline buttons from the old search message
                    await http_client.post(
                        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup",
                        json={
                            "chat_id": chat_id,
                            "message_id": callback["message"]["message_id"],
                            "reply_markup": {"inline_keyboard": []}
                        }
                    )
                await send_telegram_reply(chat_id, msg)
                return {"status": "success"}
            elif callback_data.startswith("history_"):
                index = int(callback_data.split("_")[1])
                chosen_meal = pending_data["history_options"][index]
                
                food_data = FoodStructure(
                    food_name=chosen_meal["food_name"],
                    calories=float(chosen_meal["calories"]),
                    protein=float(chosen_meal["protein"]),
                    carbs=float(chosen_meal["carbs"]),
                    fat=float(chosen_meal["fat"])
                )
                
                del PENDING_LOGS[chat_id]
                await process_and_save_meal(chat_id, food_data)

                async with httpx.AsyncClient() as http_client:
                    await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup", json={
                        "chat_id": chat_id,
                        "message_id": callback["message"]["message_id"],
                        "reply_markup": {"inline_keyboard": []}
                    })
                    await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback["id"]})
                return {"status": "success"}

            # else:
            #     schema_string = json.dumps(FoodStructure.model_json_schema())
            #     system_instructions = f"You are an expert nutritionist and precise calorie calculator. The user will provide a meal or food, often with specific quantities, measurements, and brands. You MUST calculate the macros step-by-step: identify each distinct ingredient, recall its specific nutritional values for the exact quantity/measurement provided, and sum the total calories, protein, carbs, and fat together. Return ONLY a valid JSON object matching this schema exactly: {
            #         schema_string}. CRITICAL: Return a flat JSON object. Do NOT wrap your response in a 'properties' key. IMPORTANT: If the user specifies a past date (like 6/10/26) or a meal type (like lunch), extract them into 'extracted_date' (format as YYYY-MM-DD) and 'extracted_meal_type'. IMPORTANT: If the food item is branded query for documented nutritional facts regarding that item and adjust based on quantity."

            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": f"Analyze this meal text: '{raw_text}'"}],
                model="openai/gpt-oss-120b",
                response_format={"type": "json_object"}
            )
            response_dict = json.loads(response.choices[0].message.content)
            clean_dict = {k: v for k,
                          v in response_dict.items() if v is not None}
            food_data = FoodStructure.model_validate(clean_dict)
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

        current_phase = 1
        current_week = 1

        profile_res = supabase.table("user_profiles").select(
        "current_phase, current_week").eq("chat_id", chat_id).execute()
        if profile_res.data:
            current_phase = profile_res.data[0].get("current_phase", 1)
            current_week = profile_res.data[0].get("current_week", 1)

        if not user_text or not chat_id:
            return {"status": "ignored"}

        if chat_id in PENDING_LOGS and PENDING_LOGS[chat_id].get("awaiting_manual_input"):
            parts = [p.strip() for p in user_text.split("|")]

            if len(parts) == 5:
                try:
                    food_data = FoodStructure(
                        food_name=parts[0],
                        calories=float(parts[1]),
                        protein=float(parts[2]),
                        carbs=float(parts[3]),
                        fat=float(parts[4])
                    )
                    # Clear pending state once parsed successfully
                    del PENDING_LOGS[chat_id]
                    
                    # Direct database save — NO LLM call needed!
                    await process_and_save_meal(chat_id, food_data)
                    return {"status": "success"}

                except ValueError:
                    await send_telegram_reply(
                        chat_id, 
                        "⚠️ *Invalid numbers detected.*\nPlease reply using numbers for macros:\n`Food Name | Calories | Protein | Carbs | Fat`"
                    )
                    return {"status": "success"}
            else:
                await send_telegram_reply(
                    chat_id, 
                    "⚠️ *Incorrect format.*\nPlease split values using 4 pipe `|` symbols:\n`Food Name | Calories | Protein | Carbs | Fat`"
                )
                return {"status": "success"}

        if user_text == "/start":
            welcome_message = "Welcome to the workout and meal tracker: Type '/meal' to log a nutrition, '/profile' for baseline body stats and in-body scans, or the specific phase and area '/phase_1_upper_1'"
            await send_telegram_reply(chat_id, welcome_message)
            return {"status": "success"}
        if user_text.lower() == ("/phase_test_exercise"):
            test_msg_text = f"JEFF NIPPARD TEST EXERCISE\n\n Phase {current_phase} (Week {current_week})\n" \
                            "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n" \
                            "test exercise (10-12 reps) (3 sets)\n\n" \
                            "Ready to log! Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            test_keyboard = {
                "inline_keyboard": [
                    [{"text": "test exercise",
                      "callback_data": "test_test exercise"}],
                    [{"text": "Finish Workout",
                        "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, test_msg_text, reply_markup=test_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_1_upper_1"):
            p1_u1_msg_text = f"JEFF NIPPARD PHASE 1 UPPER DAY 1 CHECKLIST\n\n Phase {current_phase} (Week {current_week})\n"
            "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "cuffed behind-the-back Lateral Raise (10-12 reps) (3 sets)\n\n"
            "cross-body lat pull-around (10-12 reps) (3 sets)\n\n"
            "low incline smith machine press (8-10 reps) (4 sets)\n\n"
            "chest-supported machine row (8-10 reps) (3 sets)\n\n"
            "overhead cable tricep extensions (bar) (8-10 reps) (2 sets)\n\n"
            "straight-bar lat prayer (12-15 reps) (3 sets)\n\n"
            "pec deck (with integrated partials) (12-15 reps) (3 sets)\n\n"
            "Ready to log! Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
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

                    [{"text": "Finish Workout",
                        "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_u1_msg_text, reply_markup=p1_u1_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_1_upper_2"):
            p1_u2_msg_text = f"JEFF NIPPARD PHASE 1 UPPER DAY 2 CHECKLIST\n\n Phase {current_phase} (Week {current_week})\n"
            "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "super-rom overhand cable row (10-12 reps) (3 sets)\n\n"
            "machine shoulder press (10-12 reps) (3 sets)\n\n"
            "assisted pull-up (8-10 reps) (3 sets)\n\n"
            "paused assisted dip (8-10 reps) (3 sets)\n\n"
            "inverse db zottman curl (10-12 reps) (2 sets)\n\n"
            "super-rom db lateral raise (12-15 reps) (3 sets)\n\n"
            "cable reverse fly (mechanical dropset on all sets) (5,4,3+ reps) (3 sets)\n\n"
            "Ready to log! Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
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
                    [{"text": "cable reverse fly (mechanical dropset on all sets) *Mechanical Dropset:* 3 steps back (5 reps) -> 1 step fwd (4 reps) -> 1 step fwd (3+ reps). No rest!",
                      "callback_data": "p1u2_cable reverse fly (mechanical dropset on all sets)"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_u2_msg_text, reply_markup=p1_u2_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_1_lower_1"):
            p1_l1_msg_text = f"JEFF NIPPARD PHASE 1 LOWER DAY 1 CHECKLIST\n\n Phase: {current_phase} (Week {current_week})\n"
            "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "seated leg curl (8-10 reps) (3 sets)\n\n"
            "machine hip adduction (10-12 reps) (3 sets)\n\n"
            "hack squat (4,6,8 reps) (3 sets)\n\n"
            "leg extension (10-12 reps) (3 sets)\n\n"
            "leg press calf press (12-15 reps) (3 sets)\n\n"
            "Ready to log! Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            p1_l1_keyboard = {
                "inline_keyboard": [
                    [{"text": "seated leg curl", "callback_data": "p1l1_seated-leg-curl"}],
                    [{"text": "machine hip adduction",
                        "callback_data": "p1l1_machine-hip-adduction"}],
                    [{"text": "hack squat", "callback_data": "p1l1_hack-squat"}],
                    [{"text": "leg extension", "callback_data": "p1l1_leg-extension"}],
                    [{"text": "leg press calf press",
                        "callback_data": "p1l1_leg-press-calf-press"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_l1_msg_text, reply_markup=p1_l1_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_1_lower_2"):
            p1_l2_msg_text = f"JEFF NIPPARD PHASE 1 LOWER DAY 2 CHECKLIST\n\n Phase: {current_phase} (Week {current_week})\n"
            "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "lying leg curl (8-10 reps) (3 sets)\n\n"
            "leg press (8 reps) (3 sets)\n\n"
            "paused barbell rdl (8 reps) (2 sets)\n\n"
            "machine hip adduction (super set with sissy squat) (10-12 reps) (3 sets)\n\n"
            "sissy squat (super set with machine hip adduction) (10-12 reps) (3 sets)\n\n"
            "seated calf raise (10-12 reps) (3 sets)\n\n"
            "Ready to log! Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            p1_l2_keyboard = {
                "inline_keyboard": [
                    [{"text": "lying leg curl (8-10 reps) (3 sets)",
                      "callback_data": "p1l2_lying-leg-curl"}],
                    [{"text": "leg press (8 reps) (3 sets)",
                      "callback_data": "p1l2_leg-press"}],
                    [{"text": "paused barbell rdl (8 reps) (2 sets)",
                        "callback_data": "p1l2_paused-barbell-rdl"}],
                    [{"text": "machine hip adduction (super set with sissy squat) (10-12 reps) (3 sets)",
                      "callback_data": "p1l2_machine-hip-adduction"}],
                    [{"text": "sissy squat (super set with machine hip adduction) (10-12 reps) (3 sets)",
                      "callback_data": "p1l2_sissy-squat"}],
                    [{"text": "seated calf raise (10-12 reps) (3 sets)",
                        "callback_data": "p1l2_seated-calf-raise"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_l2_msg_text, reply_markup=p1_l2_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_1_arms"):
            p1_wp1_msg_text = f"JEFF NIPPARD PHASE 1 WEAK POINTS CHECKLIST (Pick a weakpoint)\n\n Phase: {current_phase} (Week {current_week})\n" \
                              "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n Weak Point Exercise (8-12 reps) (Ex 1: 3 sets Ex 2: 2 sets)\n\n"
            p1_wp1_keyboard = {
                "inline_keyboard": [
                    [{"text": "Shoulders (8-12 reps) (3 sets)",
                      "callback_data": "wp_shoulders"}],
                    [{"text": "Lats (8-12 reps) (3 sets)",
                      "callback_data": "wp_lats"}],
                    [{"text": "Quads (8-12 reps) (3 sets)",
                      "callback_data": "wp_quads"}],
                    [{"text": "Glutes (8-12 reps) (3 sets)",
                      "callback_data": "wp_glutes"}],
                    [{"text": "Chest (8-12 reps) (3 sets)",
                      "callback_data": "wp_chest"}],
                    [{"text": "Neck (8-12 reps) (3 sets)",
                      "callback_data": "wp_neck"}],
                    [{"text": "Hamstrings (8-12 reps) (3 sets)",
                      "callback_data": "wp_hamstrings"}],
                    [{"text": "Calves (8-12 reps) (3 sets)",
                      "callback_data": "wp_calves"}],
                    [{"text": "Mid-Back (8-12 reps) (3 sets)",
                      "callback_data": "wp_mid-back"}],
                    [{"text": "Upper Traps (8-12 reps) (3 sets)",
                      "callback_data": "wp_upper traps"}],
                    [{"text": "Abs (8-12 reps) (3 sets)",
                      "callback_data": "wp_abs"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_wp1_msg_text, reply_markup=p1_wp1_keyboard)
            p1_arms_text = "JEFF NIPPARD PHASE 1 ARMS CHECKLIST\n\n"
            "bayesian cable curl (10-12 reps) (3 sets)\n\n"
            "seated db french press (10 reps) (3 sets)\n\n"
            "bottom-2/3 constant tension preacher curl (12-15 reps) (2 sets)\n\n"
            "cable triceps kickback (12-15 reps) (2 sets)\n\n"
            "cable crunch (10-12 reps) (3 sets)\n\n"
            "Ready to log! Just text your sets normally.\n\n"
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
                    [{"text": "cable crunch (10-12 reps) (3 sets)",
                      "callback_data": "p1a_cable-crunch"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p1_arms_text, reply_markup=p1_arms_keyboard)
            return {"status": "success"}

        if user_text.lower() == ("/phase_2_upper_1"):
            p2_u1_msg_text = f"**JEFF NIPPARD PHASE 2 UPPER DAY 1 CHECKLIST**\n\n **Phase:** {current_phase} (Week {current_week})\n"
            "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "cuffed behind-the-back Lateral Raise (10-12 reps) (3 sets)\n\n"
            "lat-focused cable row (10-12 reps) (3 sets)\n\n"
            "low incline dumbbell press (8-10 reps) (3 sets)\n\n"
            "chest-supported machine row + kelso shrug (8-10 + 4-6 reps) (3 sets)\n\n"
            "bent-over cable pec flye (w/ integrated partials) (12-15 reps) (3 sets)\n\n"
            "1-arm lat pull-in (12-15 reps) (2 sets)\n\n"
            "dual-cable triceps press (10-12 reps) (3 sets)\n\n"
            "Ready to log! Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            p2_u1_keyboard = {
                "inline_keyboard": [
                    [{"text": "cuffed behind-the-back Lateral Raise (10-12 reps) (3 sets)",
                        "callback_data": "p2u1_cuffed-behind-the-back-lateral-raise"}],
                    [{"text": "lat-focused cable row (10-12 reps) (3 sets)",
                        "callback_data": "p2u1_lat-focused-cable-row"}],
                    [{"text": "low incline dumbbell press (8-10 reps) (3 sets)",
                        "callback_data": "p2u1_low-incline-db-press"}],
                    [{"text": "machine chest-supported row + kelso shrug (8-10 + 4-6 reps) (3 sets)",
                        "callback_data": "p2u1_machine chest-supported row + kelso shrug"}],
                    [{"text": "bent-over cable pec flye (w/ integrated partials) (12-15 reps) (3 sets)",
                      "callback_data": "p2u1_bent-over-cable-pec-flye-(w/-integrated-partials)"}],
                    [{"text": "1-arm lat pull-in (12-15 reps) (2 sets)",
                        "callback_data": "p2u1_1-arm-lat-pull-in"}],
                    [{"text": "dual-cable triceps press (10-12 reps) (3 sets)",
                        "callback_data": "p2u1_dual-cable-triceps-press"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_u1_msg_text, reply_markup=p2_u1_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_2_upper_2"):
            p2_u2_msg_text = f"JEFF NIPPARD PHASE 2 UPPER DAY 2 CHECKLIST\n\n Phase: {current_phase} (Week {current_week})\n"
            "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "dual-handle lat pulldown (mid-back + lats) (10-12 reps) (3 sets)\n\n"
            "seated dumbbell shoulder press (10-12 reps) (3 sets)\n\n"
            "chest-supported machine row (8-10 reps) (3 sets)\n\n"
            "decline machine chest press (8-10 reps) (3 sets)\n\n"
            "concentration cable curl (10-12 reps) (2 sets)\n\n"
            "cross-body cable y-raise (10-12 reps) (3 sets)\n\n"
            "rear delt 45 degrees cable flye (12-15 reps) (3 sets)\n\n"
            "Ready to log! Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
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

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_u2_msg_text, reply_markup=p2_u2_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_2_lower_1"):
            p2_l1_msg_text = f"JEFF NIPPARD PHASE 2 LOWER DAY 1 CHECKLIST\n\n Phase: {current_phase} (Week {current_week})\n"
            "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "seated leg curl (8-10 reps) (3 sets)\n\n"
            "machine hip adduction (10-12 reps) (3 sets)\n\n"
            "smith machine squat (4,6,8 reps) (3 sets)\n\n"
            "leg extension (10-12 reps) (3 sets)\n\n"
            "dumbbell calf jumps (12-15 reps) (3 sets)\n\n"
            "Ready to log! Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            p2_l1_keyboard = {
                "inline_keyboard": [
                    [{"text": "Seated Leg Curl (8-10 reps) (3 sets)",
                      "callback_data": "p2l1_seated-leg-curl"}],
                    [{"text": "Machine Hip Adduction (10-12 reps) (3 sets)",
                        "callback_data": "p2l1_machine-hip-adduction"}],
                    [{"text": "Smith Machine Squat (4,6,8 reps) (3 sets)",
                        "callback_data": "p2l1_smith-machine-squat"}],
                    [{"text": "Leg Extension (10-12 reps) (3 sets)",
                      "callback_data": "p2l1_leg-extension"}],
                    [{"text": "Dumbbell Calf Jumps (12-15 reps) (3 sets)",
                        "callback_data": "p2l1_dumbbell-calf-jumps"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_l1_msg_text, reply_markup=p2_l1_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_2_lower_2"):
            p2_l2_msg_text = f"JEFF NIPPARD PHASE 2 LOWER DAY 2 CHECKLIST\n\n Phase: {current_phase} (Week {current_week})\n"
            "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n\n"
            "lying leg curl (8-10 reps) (3 sets)\n\n"
            "smith machine reverse lunge (8 reps) (3 sets)\n\n"
            "glute-ham raise (8 reps) (3 sets)\n\n"
            "machine hip adduction (super set with machine hip abduction) (10-12 reps) (3 sets)\n\n"
            "machine hip abduction (super set with machine hip adduction) (10-12 reps) (3 sets)\n\n"
            "seated calf raise (10-12 reps) (3 sets)\n\n"
            "Ready to log! Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            p2_l2_keyboard = {
                "inline_keyboard": [
                    [{"text": "lying leg curl (8-10 reps) (3 sets)",
                      "callback_data": "p2l2_lying-leg-curl"}],
                    [{"text": "smith machine reverse lunge (8 reps) (3 sets)",
                        "callback_data": "p2l2_smith-machine-reverse-lunge"}],
                    [{"text": "glute-ham raise (8 reps) (3 sets)",
                      "callback_data": "p2l2_glute-ham-raise"}],
                    [{
                        "text": "machine hip adduction (super set with machine hip abduction) (10-12 reps) (3 sets)", "callback_data": "p2l2_machine-hip-adduction"}],
                    [{"text": "machine hip abduction (super set with machine hip adduction) (10-12 reps) (3 sets)",
                      "callback_data": "p2l2_machine-hip-abduction"}],
                    [{"text": "seated calf raise (10-12 reps) (3 sets)",
                        "callback_data": "p2l2_seated-calf-raise"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_l2_msg_text, reply_markup=p2_l2_keyboard)
            return {"status": "success"}
        if user_text.lower() == ("/phase_2_arms"):
            p2_wp_msg_text = f"JEFF NIPPARD PHASE 2 ARMS & WEAK POINTS CHECKLIST (Pick a weakpoint)\n\n Phase: {current_phase} (Week {current_week})\n"
            "Warm-Up: 5-10 min cardio, Arm Circles, Arm Swings, Front-to-Back Leg Swings, Side-to-Side Leg Swings (10 reps per side), Cable External Rotational (15 reps per side)\n"
            "Weak Point Exercise (8-12 reps) (Ex 1: 3 sets Ex 2: 2 sets)\n\n"
            p2_wp_keyboard = {
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
                    [{"text": "Abs", "callback_data": "wp_abs"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_wp_msg_text, reply_markup=p2_wp_keyboard)
            p2_arms_msg_text = "Arms"
            p2_arms_keyboard = {
                "inline_keyboard": [
                    [{"text": "slow-eccentric ez-bar skull crusher (10-12 reps) (3 sets)",
                      "callback_data": "p2a_slow-eccentric-ez-bar-skull-crusher"}],
                    [{"text": "slow-eccentric bayesian curl (10-12 reps) (3 sets)",
                      "callback_data": "p2a_slow-eccentric-bayesian-curl"}],
                    [{"text": "triceps diverging pressdown (long rope or 2 ropes) (12-15 reps) (2 sets)", "callback_data": "p2a_triceps-diverging-pressdown-(long-rope-or-2-ropes)"}], [{
                        "text": "reverse grip cable curl (12-15 reps) (2 sets)", "callback_data": "p2a_reverse-grip-cable-curl"}],
                    [{"text": "roman chair leg raise crunch (10-20 reps) (3 sets)",
                        "callback_data": "p2a_roman-chair-leg-raise-crunch"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, p2_arms_msg_text, reply_markup=p2_arms_keyboard)
            return {"status": "success"}
        if user_text.lower() == "/weakpoints":
            wp_msg_text = "Select your Weak Point for today:"
            keyboard = {
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
                    [{"text": "Abs", "callback_data": "wp_abs"}],

                    [{"text": "Finish Workout",
                      "callback_data": "action_finish_workout"}],
                ]
            }
            await send_telegram_reply(chat_id, wp_msg_text, reply_markup=keyboard)
            return {"status": "success"}
        if user_text.lower().startswith("/meal") or user_text.lower().startswith("m:") or user_text.lower().startswith("meal:"):
            # Extract the actual food text by removing the command
            raw_food_text = user_text.lower().replace("meal:", "").replace("m:", "").replace("/meal", "").strip()
                
            if not raw_food_text:
                await send_telegram_reply(chat_id, "Please include the food you ate starting with /meal or meal: or m:! Example: /meal 2 eggs and toast")
                return {"status": "success"}
            
            history_res = supabase.table("food_logs") \
                .select("food_name, calories, protein, carbs, fat") \
                .ilike("food_name", f"%{raw_food_text}%") \
                .limit(5) \
                .execute()
            keyboard_buttons = []

            if history_res.data:
                seen_names = set()
                unique_matches = []
                for item in history_res.data:
                    name = item["food_name"]
                    if name not in seen_names:
                        seen_names.add(name)
                        unique_matches.append(item)

                msg_text = f"🔍 Found *{len(unique_matches)} matching meal(s)* in your history for '{raw_food_text}':\nTap one to re-log instantly, or choose a new method below:"
                for item in unique_matches[:3]: # Limit to top 3 history buttons
                    btn_label = f"📜 {item['food_name'].title()} ({item['calories']} kcal)"
                    # We encode the chosen history item data directly or use a history tag
                    # For simplicity, we can pass a special callback prefix like history_
                    # Or save them in PENDING_LOGS. Let's store matches in PENDING_LOGS!
                    pass

                PENDING_LOGS[chat_id] = {
                    "raw_text": raw_food_text,
                    "history_options": unique_matches[:3]
                }

                for i, item in enumerate(unique_matches[:3]):
                    btn_label = f"{item['food_name'].title()} ({item['calories']} kcal | {item['protein']}g P)"
                    keyboard_buttons.append([{"text": btn_label, "callback_data": f"history_{i}"}])
            else:
            # Save it to the pending logs so your callback_query logic can access it
                PENDING_LOGS[chat_id] = {"raw_text": raw_food_text}
                msg_text = f"Ready to log: *{raw_food_text}*.\nNo past logs found. Choose how to process this:"

            keyboard_buttons.append([{"text": "USDA Database Search", "callback_data": "choice_usda"}])
            keyboard_buttons.append([{"text": "AI Estimation", "callback_data": "choice_ai"}])
            keyboard_buttons.append([{"text": "Manual Entry", "callback_data": "manual_entry"}])
            
            # Send a reply with inline buttons to trigger the callback_query routing
            meal_keyboard = {
                "inline_keyboard": keyboard_buttons
            }
            await send_telegram_reply(chat_id, msg_text, reply_markup=meal_keyboard)
            return {"status": "success"}
        if user_text.lower() == "/meal":
            meal_instructions = (
                "*NUTRITION LOGGING ENGINE*\n\n"
                "You can log your food conversationally without worrying about exact serving math. "
                "The system will automatically categorize it based on the time of day and calculate your macros into Supabase.\n\n"
                "  How to log:\n"
                "Simply text me what you ate naturally. If your message doesn't contain lifting terms (like lbs or reps), it defaults to a food log!\n\n"
                "Examples:\n"
                "• 'meal: 3 eggs and a scoop of ascent native fuel whey protein powder'\n"
                "• 'meal: chicken korma with two pieces of garlic naan'\n"
                "• 'meal: fish pulusu with two pieces of paratha for lunch 06/10/2026'\n"
                "• 'meal: rice with chicken for dinner'\n"
                "• 'meal: a slice of homemade tiramisu'\n\n"
                "*Just start your message with 'meal:' followed by your food to save it!*"
            )
            await send_telegram_reply(chat_id, meal_instructions)
            return {"status": "success"}

        if "note" in user_text.lower():
            central_tz = zoneinfo.ZoneInfo("America/Chicago")
            raw_note = user_text.split("note:", 1)[1].strip()
            active_ex = ACTIVE_EXERCISE_SESSIONS.get(chat_id)
            if raw_note and active_ex:
                supabase.table("user_exercise_notes").upsert({
                    "chat_id": chat_id,
                    "exercise_name": active_ex.lower().strip(),
                    "note": raw_note,
                    "updated_at": datetime.now(central_tz).isoformat()
                }).execute()
                await send_telegram_reply(chat_id, f"Note saved")
                return {"status": "success"}
            elif not active_ex:
                await send_telegram_reply(chat_id, "Please select or log an exercise first before adding a note!")
                return {"status": "success"}

        if user_text.lower() == "/profile":
            profile_instructions = (
                "*Profile Setup*\n\n"
                "You can log your Body Scan results and goal to save it and train the machine learning model. "
                "The system will automatically use your goal and categories your food based on the time of day and calculate your macros into Supabase.\n\n"
                "Just start your message with 'profile:' followed by your data in the following format so I can update your macro targets:\n"
                "InBody Analysis: [Height (in)], [Age]; Body Composition Analysis: [Total Body Water (lb)], [Dry Lean Mass (lb)], [Body Fat Mass (lb)], [Weight (lb)]; Muscle-Fat Analysis: [Weight (lb)], [SMM (lb)], [Body Fat Mass (lb)]; Obesity Analysis: [BMI (KG/M2)], [PBF (%)]; Segmental Lean Analysis: [Left Arm %], [Right Arm %], [Left Leg %], [Right Leg %]; Research Parameters: [Lean Body Mass (lb)], [Basal Metabolic Rate (kcal)], [SMI (kg/m^2)]; Impedance: 20kHz: [RA], [LA], [TR], [RL], [LL], 100kHz: [RA], [LA], [TR], [RL], [LL]; Goal: [bulk/cut/recomposition]"
            )
            await send_telegram_reply(chat_id, profile_instructions)
            return {"status": "success"}
        if user_text.lower().startswith("profile:"):
            clean_profile_text = user_text.lower().replace("profile:", "").strip()

            class ProfileInput(BaseModel):
                height: float
                age: float
                total_body_water: float
                dry_lean_mass: float
                body_fat_mass: float
                weight: float
                skeletal_muscle_mass: float  # SMM
                bmi: float
                body_fat_percentage: float
                segmental_lean_data: list[float]
                lean_body_mass: float
                inbody_bmr: float
                smi: float
                impedance_20khz: list[float]
                impedance_100khz: list[float]
                goal: str

            schema_string = json.dumps(ProfileInput.model_json_schema())
            system_instructions = (
                "You are an expert fitness data parser. "
                "The user will provide data in these categories: "
                "1. InBody Analysis (Height, Age). "
                "2. Body Composition (Total Body Water, Dry Lean Mass, Body Fat Mass, Weight). "
                "3. Muscle-Fat Analysis (Weight, SMM, Body Fat Mass). "
                "4. Obesity Analysis (BMI, PBF / body_fat_percentage). "
                "5. Segmental Lean Analysis (Left Arm %, Right Arm %, Left Leg %, Right Leg %). "
                "6. Research Parameters (Lean Body Mass, Basal Metabolic Rate -> inbody_bmr, SMI). "
                "7. Impedance 20kHz (RA, LA, TR, RL, LL) and 100kHz (RA, LA, TR, RL, LL). "
                "8. Goal (bulk, cut, maintenance, recomposition). "
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
            goal = profile_data.goal.lower()
            bmr = profile_data.inbody_bmr
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

            carbs = int((cals - (protein * 4) - (fat * 9)) / 4)

            central_tz = zoneinfo.ZoneInfo("America/Chicago")

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
                "body_fat_mass": profile_data.body_fat_mass,
                "body_fat_percentage": profile_data.body_fat_percentage,
                "bmi": profile_data.bmi,
                "segmental_lean_data": profile_data.segmental_lean_data,
                "lean_body_mass": profile_data.lean_body_mass,
                "inbody_bmr": profile_data.inbody_bmr,
                "smi": profile_data.smi,
                "impedance_20khz": profile_data.impedance_20khz,
                "impedance_100khz": profile_data.impedance_100khz,
                "created_at": datetime.now(central_tz).isoformat()
            }).execute()

            reply = (
                f"*Smart Profile Generated!*\n"
                f"Weight: {weight} lbs | Goal: {goal.title()}\n\n"
                f"*Your Daily Targets:*\n"
                f"{cals} kcal\n"
                f"Protein: {protein}g\n"
                f"Carbs: {carbs}g\n"
                f"Fat: {fat}g\n"
                f"*Scan Metrics Logged:*\n"
                f"SMM: {profile_data.skeletal_muscle_mass}kg\n"
                f"Body Fat: {profile_data.body_fat_percentage}%\n"
                f"SMI: {profile_data.smi}"
            )

            await send_telegram_reply(chat_id, reply)
            return {"status": "success"}
            # import re

            # raw_upc_match = re.search(r'\b\d{8,14}\b', clean_food_text)
            # direct_upc = raw_upc_match.group(0) if raw_upc_match else None

            # usda_upc_results = []
            # display_query = ""
            # msg_text = ""
            # usda_results = []

            # if direct_upc:
            #     usda_upc_results = await get_usda_macros("", upc=direct_upc)
            #     display_query = f"UPC {direct_upc}"

            #     if not usda_upc_results and clean_food_text.replace(direct_upc, "").strip() == "":
            #         await send_telegram_reply(chat_id, f"⚠️ Barcode {direct_upc} not found!\nThe USDA database doesn't have this exact UPC logged. Please reply with the food's name instead.")
            #         return {"status": "success"}

            # if not usda_upc_results:
            #     classification_prompt = (
            #         "You are an expert food query router for a nutrition engine. "
            #         f"The user logged: '{clean_food_text}'.\n"
            #         "Analyze the meal and decide if it is likely in the USDA FoodData Central database "
            #         "(branded grocery items, raw produce, staple meats, common commercial items, foundation foods, sr legacy, fndds, experimental foods, branded foods) "
            #         "or if it is a complex home-cooked/cultural dish not standardized in USDA "
            #         "(e.g., specific Indian curries like 'spinach dal', 'fish pulusu', 'carrot fry', biryani, homemade desserts).\n\n"
            #         "Return a JSON object with two fields:\n"
            #         "- 'is_usda_compatible': boolean (true if in USDA FoodData Central Database, false if regional/home-cooked curry/dish)\n"
            #         "- 'search_query': standardized commercial search term if true (fix typos, expand brand names, strip portions), "
            #         "or empty string if false.\n"
            #         "Example JSON: {\"is_usda_compatible\": false, \"search_query\": \"\"}"
            #     )
            #     classifier_res = groq_client.chat.completions.create(
            #         messages=[
            #             {"role": "user", "content": classification_prompt}],
            #         model="openai/gpt-oss-20b",
            #         response_format={"type": "json_object"}
            #     )
            #     route_data = json.loads(
            #         classifier_res.choices[0].message.content)
            #     is_usda = route_data.get("is_usda_compatible", False)
            #     search_query = route_data.get("search_query", "").strip()

            #     if is_usda and search_query:
            #         usda_results = await get_usda_macros(search_query)
            #         display_query = search_query

            # PENDING_LOGS[chat_id] = {
            #     "raw_text": clean_food_text,
            #     "usda_options": usda_results or []
            # }

            # keyboard = {"inline_keyboard": []}

            # if usda_results:
            #     clean_display = display_query.replace("'", "").replace("*", "")
            #     msg_text = f" Found {len(usda_results)} results for {
            #         clean_display}.\nSelect the most accurate option to log it:"
            #     for i, item in enumerate(usda_results):
            #         clean_item_name = item['food_name'].replace("'", "").replace("*", "").replace("_", "")[:28]
            #         btn_text = f"{clean_item_name}... ({item['calories']} kcal)"
            #         keyboard["inline_keyboard"].append(
            #             [{"text": btn_text, "callback_data": f"usda_{i}"}])
            #     else:
            #         clean_input = clean_food_text.replace("'", "").replace("*", "")
            #         msg_text = f"No exact USDA matches found for *'{clean_input}'*.\nHow would you like to log this?"

            #     keyboard["inline_keyboard"].append(
            #         [{"text": "Use AI Estimation instead", "callback_data": "ai_fallback"}])
            #     keyboard["inline_keyboard"].append(
            #         [{"text": "Manual Macros Entry", "callback_data": "manual_entry"}])
            #     await send_telegram_reply(chat_id, msg_text, reply_markup=keyboard)
            #     return {"status": "success"}
        base_keywords = ["bench", "squat", "deadlift", "reps", "sets", "lbs", "lift", "press", "curls", "workout",
                         "pounds", "row", "pulldown", "fly", "raise", "extension", "crunch", "rdl", "step up", "toe-press"]
        is_workout = any(w in user_text.lower() for w in base_keywords) or any(normalize_str(k) in normalize_str(user_text)
                                                                               for k in EXERCISE_REGISTRY.keys()) or user_text.lower().startswith("w:") or "upper:" in user_text.lower() or "lower:" in user_text.lower()

        if is_workout:
            clean_text = user_text.replace("workout:", "").replace(
                "upper", "").replace("lower", "").replace("w", "").strip()
            active_ex = ACTIVE_EXERCISE_SESSIONS.get(chat_id)
            if active_ex and not any(normalize_str(ex_word) in normalize_str(clean_text) for ex_word in EXERCISE_REGISTRY.keys()):
                clean_text = f"{active_ex} {clean_text}"
            schema_string = json.dumps(WorkoutStructure.model_json_schema())
            official_names = ", ".join(EXERCISE_REGISTRY.keys())
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
            exercise = match_exercise(
                lift_data.exercise_name) or lift_data.exercise_name.lower().strip()

            if exercise not in EXERCISE_REGISTRY:
                error_reply = (
                    f"Unrecognized Exercise: '_{
                        exercise.title()}_' Check spelling or select via workout menu.\n\n"
                )
                await send_telegram_reply(chat_id, error_reply)
                return {"status": "success"}

            if lift_data.reps == 0:
                reply = await build_exercise_session_targets(exercise, chat_id)
                await send_telegram_reply(chat_id, reply)
                return {"status": "success"}

            today_str = date.today().isoformat()
            existing_sets = supabase.table("exercise_logs") \
                .select("id") \
                .eq("exercise_name", exercise) \
                .gte("created_at", today_str) \
                .execute()
            set_count = 0 if lift_data.is_warmup else len(
                existing_sets.data) + 1

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
                    f"Warm-Up Set Tracked:\n"
                    f"*{exercise.title()
                        }* - {lift_data.weight} lbs × {lift_data.reps} reps\n"
                    f"*(This does not trigger rest timers or affect working set counts)*"
                )
                await send_telegram_reply(chat_id, reply_msg)
                return {"status": "success"}

            ex_info = EXERCISE_REGISTRY.get(exercise, {})
            sets_config = ex_info.get("sets", {})
            total_target_sets = len(sets_config)
            # intensity_advice = ex_info.get("advice", "")
            if set_count >= total_target_sets:
                ACTIVE_EXERCISE_SESSIONS.pop(chat_id, None)
                next_set_advice = f"*Exercise Complete!* {
                    total_target_sets} sets logged."
            else:
                next_set_count = set_count + 1
                curr_targets = sets_config.get(set_count, {"min_reps": 8, "max_reps": 12, "increment": 5})
                increment = curr_targets.get("increment", 5)
                max_reps = curr_targets.get("max_reps", 12)
                is_reverse_pyramid = any(ex in exercise for ex in ["test reverse pyramid exercise", "hack squat", "smith machine squat"])
                is_assisted = any(ex in exercise for ex in ["test assisted exercise", "assisted pull-up", "paused assisted dip"])
                if is_assisted:
                    if lift_data.reps >= max_reps:
                        next_weight = max(0, lift_data.weight - increment)
                        next_set_advice = f"\n\n *Next Set Target:* Hit rep cap! Reduce assistance to {next_weight} lbs."
                    else:
                        next_set_advice = f"\n\n *Next Set Target:* Hold {lift_data.weight} lbs assistance and push closer to {max_reps} reps."
                elif is_reverse_pyramid:
                    next_targets = sets_config.get(next_set_count, curr_targets)
                    drop_percent = next_targets["drop_percent"]
                    drop_weight = round((lift_data.weight * (1 - drop_percent)) / 5) * 5
                    next_set_advice = f"\n\n *Next Set Target:* Drop weight for back-off. Target *{drop_weight} lbs* for *{next_targets['max_reps']} reps*."
                else:
                    if set_count == total_target_sets - 1:
                        next_set_advice = f"\n\n *Next Set Target:* Final set! Variation: {ex_info.get('last_set', 'None')}."
                    else:
                        # Standard progression advice for Set 1 -> Set 2
                        if lift_data.reps >= max_reps:
                            next_set_advice = f"\n\n *Next Set Target:* Hit rep cap! Increase weight for Set {next_set_count}."
                        else:
                            next_set_advice = f"\n\n *Next Set Target:* Hold {lift_data.weight} lbs and push closer to {max_reps} reps."

                # Trigger rest timer for Set 1 AND Set 2 completions
                background_tasks.add_task(
                    delayed_rest_reminder,
                    chat_id=chat_id,
                    exercise_name=exercise,
                    next_set=next_set_count,
                    target_desc=f"{max_reps} reps",
                    next_set_advice=next_set_advice
                )

            # elif set_count == total_target_sets - 1:
            #     next_set_advice = f"\n\n *Next Set Target:* Final set! Variation: {ex_info.get('last_set', 'None')}."
            # else:
            #     next_set_count = set_count + 1
            #     curr_targets = sets_config.get(
            #         set_count, {"min_reps": 8, "max_reps": 12, "increment": 5})
            #     # increment = curr_targets.get("increment", 5)
            #     max_reps = curr_targets.get("max_reps", 12)

            #     is_reverse_pyramid = any(ex in exercise for ex in [
            #                              "hack squat", "smith machine squat"])
            #     is_assisted = any(ex in exercise for ex in [
            #                       "assisted pull-up", "paused assisted dip"])

            #     if is_reverse_pyramid:
            #         next_targets = sets_config.get(
            #             next_set_count, curr_targets)
            #         # drop_weight = max(0, lift_data.weight - increment)
            #         next_set_advice = f"\n\n *Next Set Target:* Drop weight for back-off. Target is {next_targets['max_reps']} reps."
            #         # next_set_advice = f"\n\n *Next Set Target:* Drop weight for back-off. Target {
            #         #     drop_weight} lbs for {next_targets['max_reps']} reps."
            #     elif is_assisted:
            #         if lift_data.reps >= max_reps:
            #             # next_weight = max(0, lift_data.weight - increment)
            #             next_set_advice = f"\n\n *Next Set Target:* Hit rep cap! Reduce assistance."
            #             # next_set_advice = f"\n\n *Next Set Target:* Hit rep cap! Reduce assistance to {
            #             #     next_weight} lbs."
            #         else:
            #             next_set_advice = f"\n\n *Next Set Target:* Hold {
            #                 lift_data.weight} lbs assistance and push closer to {max_reps} reps."
            #     else:
            #         if lift_data.reps >= max_reps:
            #             # next_weight = lift_data.weight + increment
            #             next_set_advice = f"\n\n *Next Set Target:* Hit rep cap! Increase weight for Set {next_set_count}."
            #             # next_set_advice = f"\n\n *Next Set Target:* Hit rep cap! Bump to {
            #             #     next_weight} lbs for Set {next_set_count}."
            #         else:
            #             next_set_advice = f"\n\n *Next Set Target:* Hold {
            #                 lift_data.weight} lbs and push closer to {max_reps} reps."

            # background_tasks.add_task(
            #     delayed_rest_reminder,
            #     chat_id=chat_id,
            #     exercise_name=exercise,
            #     next_set=next_set_count,
            #     target_desc=f"{max_reps} reps",
            #     next_set_advice=next_set_advice
            # )

            reply_msg = (
                f" *{exercise.title()}* - Set {set_count}\n"
                f" {lift_data.weight} lbs × {lift_data.reps} reps\n\n"
                f" {next_set_advice}"
            )
            await send_telegram_reply(chat_id, reply_msg)
            return {"status": "success"}

        await send_telegram_reply(chat_id, "Message received. Type `/meal` to log food or start an exercise checklist to log lifts.")
        return {"status": "success"}

    except Exception as e:
        print(f"Webhook error: {e}")
        try:
            await send_telegram_reply(chat_id, f"Webhook Error: {str(e)}")
        except Exception as inner_e:
            print(f"Failed to even send the error to Telegram: {inner_e}")
        return {"status": "success"}
