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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

USDA_API_KEY = os.getenv("USDA_API_KEY")

PROGRESSION_SCHEMA = {
    # --- UPPER BODY #1---
    "cuffed behind-the-back lateral raise": { 
        1: {"max_reps": 12, "increment": 5}, #whats the increment
        2: {"max_reps": 12, "increment": 5},
        3: {"max_reps": 12, "increment": 5},
    },
    "cross-body lat pull-around": { 
        1: {"max_reps": 12, "increment": 5}, #whats the increment
        2: {"max_reps": 12, "increment": 5},
        3: {"max_reps": 12, "increment": 5},
    },
    "low incline smith machine press": { 
        1: {"max_reps": 10, "increment": 10}, #whats the increment
        2: {"max_reps": 10, "increment": 10},
        3: {"max_reps": 10, "increment": 10},
        4: {"max_reps": 10, "increment": 10},

    },
    "chest-supported machine row": { 
        1: {"max_reps": 10, "increment": 10}, #whats the increment
        2: {"max_reps": 10, "increment": 10},
        3: {"max_reps": 10, "increment": 10},
    },
    "overhead cable tricep extensions (bar)": { 
        1: {"max_reps": 10, "increment": 5},
        2: {"max_reps": 10, "increment": 5},
    },
    "straight-bar lat prayer": { 
        1: {"max_reps": 15, "increment": 10}, #whats the increment
        2: {"max_reps": 15, "increment": 10},
        3: {"max_reps": 15, "increment": 10},
    },
    "pec deck (with integrated partials)": { 
        1: {"max_reps": 15, "increment": 10}, #whats the increment
        2: {"max_reps": 15, "increment": 10},
        3: {"max_reps": 15, "increment": 10},
    },

    # --- LOWER BODY #1---
    "seated leg curl": { 
        1: {"max_reps": 10, "increment": 10}, #whats the increment
        2: {"max_reps": 10, "increment": 10},
        3: {"max_reps": 10, "increment": 10}
    },
    "machine hip adduction": { 
        1: {"max_reps": 12, "increment": 10}, #whats the increment
        2: {"max_reps": 12, "increment": 10},
        3: {"max_reps": 12, "increment": 10}
    },
    "hack squat": { 
        1: {"max_reps": 4, "increment": 5}, #whats the increment
        2: {"max_reps": 6, "increment": 5}, #whats the increment
        3: {"max_reps": 8, "increment": 5}, #whats the increment
    },
    "leg extension": { 
        1: {"max_reps": 10, "increment": 10}, #whats the increment
        2: {"max_reps": 11, "increment": 10},
        3: {"max_reps": 12, "increment": 10},
    },

    "leg press calf press": { 
        1: {"max_reps": 10, "increment": 10}, #whats the increment
        2: {"max_reps": 10, "increment": 10},
        3: {"max_reps": 10, "increment": 10},  
    },

    # --- UPPER BODY #2---
    "super-rom overhand cable row": { 
        1: {"max_reps": 12, "increment": 5}, #whats the increment
        2: {"max_reps": 12, "increment": 5},
        3: {"max_reps": 12, "increment": 5},
    },
    "machine shoulder press": { 
        1: {"max_reps": 12, "increment": 5}, #whats the increment
        2: {"max_reps": 12, "increment": 5},
        3: {"max_reps": 12, "increment": 5},
    },
    "assisted pull-up": { 
        1: {"max_reps": 10, "increment": 5}, #whats the increment
        2: {"max_reps": 10, "increment": 5},
        3: {"max_reps": 10, "increment": 5},
    },
    "paused assisted dip": { 
        1: {"max_reps": 10, "increment": 5},   #whats the increment
        2: {"max_reps": 10, "increment": 5},
        3: {"max_reps": 10, "increment": 5},
    },
    "inverse db zottman curl": { 
        1: {"max_reps": 12, "increment": 5},   #whats the increment
        2: {"max_reps": 12, "increment": 5},
    },
    "super-rom db lateral raise": { 
        1: {"max_reps": 15, "increment": 5},   #whats the increment
        2: {"max_reps": 15, "increment": 5},
        3: {"max_reps": 15, "increment": 5},
    },
    "cable reverse fly (mechanical dropset)": { 
        1: {"max_reps": 5, "increment": 5},   #whats the increment
        2: {"max_reps": 4, "increment": 5},
        3: {"max_reps": 3, "increment": 5},
    },

    # --- LOWER BODY #2---
    "lying leg curl": { 
        1: {"max_reps": 10, "increment": 5}, #whats the increment
        2: {"max_reps": 10, "increment": 5},
        3: {"max_reps": 10, "increment": 5},
    },
    "leg press": { 
        1: {"max_reps": 8, "increment": 5},   #whats the increment
        2: {"max_reps": 8, "increment": 5},
        3: {"max_reps": 8, "increment": 5},
    },
    "paused barbell rdl": { 
        1: {"max_reps": 8, "increment": 5},   #whats the increment
        2: {"max_reps": 8, "increment": 5},
    },
    "machine hip adduction": { 
        1: {"max_reps": 12, "increment": 5},   #whats the increment
        2: {"max_reps": 12, "increment": 5},
        3: {"max_reps": 12, "increment": 5},
    },
    "sissy squat": { 
        1: {"max_reps": 12, "increment": 5},   #whats the increment
        2: {"max_reps": 12, "increment": 5},
        3: {"max_reps": 12, "increment": 5},
    },
    "standing calf raise": { 
        1: {"max_reps": 12, "increment": 5},   #whats the increment
        2: {"max_reps": 12, "increment": 5},
        3: {"max_reps": 12, "increment": 5},
    },

    # --- DEFAULT FALLBACK ---
    "default": {
        1: {"max_reps": 12, "increment": 5},
        2: {"max_reps": 12, "increment": 5},
        3: {"max_reps": 12, "increment": 5}
    }
}

EXERCISE_COACHING = {
    "cuffed behind-the-back lateral raise": {"reps": "10-12 reps", "advice": "Raise the cables up and out in a 'Y' motion. Connect with middle delt fibers. **Last Set: Myo-reps!**"},
    "cross-body lat pull-around": {"reps": "10-12 reps", "advice":"Keep cable and wrist in a straight line. **Last Set: Long-length Partials on all reps.**"},
    "low incline smith machine press": {"reps": "8-10 reps", "advice":"15° incline. 1s pause on chest. **Last Set: 30s Pec Static Stretch hold.**"},
    "chest-supported machine row": {"reps": "8-10 reps", "advice":"Flare elbows ~45°. Squeeze blades hard at top. **Last Set: Long-length Partials.**"},
    "overhead cable tricep extension": {"reps": "8-10 reps", "advice":"Nasty stretch on negative, 1s pause at bottom. **Last Set: Dropset.**"},
    "straight-bar lat prayer": {"reps": "12-15 reps", "advice":"Deep stretch at top, squeeze lats at bottom. **Last Set: Long-length Partials.**"},
    "pec deck": {"reps": "12-15 reps", "advice":"**Integrated Partials:** Alternate 1 full ROM rep with 1 bottom-half partial rep."},

    "seated leg curl": {"reps": "8-10 reps", "advice":"Lean forward to maximize hamstring stretch."},
    "machine hip abduction": {"reps": "10-12 reps", "advice":"Drive knees outward against the pads. Control the eccentric."},
    "hack squat": {"reps": "4, 6, 8 reps (Reverse Pyramid)", "advice":"Set 1: Heaviest. Set 2: -10-15%. Set 3: -10-15%."},
    "leg extension": {"reps": "10-12 reps (Reverse Pyramid)", "advice":"2-3s negative. Feel quads pulling apart. **Last Set: Long-length Partials.**"},
    "leg press calf press": {"reps": "12-15 reps", "advice":"1-2s pause at bottom. Roll ankles on balls of feet. **Last Set: 30s Static Stretch.**"},

    "super-rom overhand cable row": {"reps": "10-12 reps", "advice":"Wide-grip pulldown bar. Lean forward on negative, upright on pull."},
    "machine shoulder press": {"reps": "10-12 reps", "advice":"Elbows at 90°. Smooth, controlled reps. **Last Set: Dropset.**"},
    "assisted pull-up": {"reps": "8-10 reps", "advice":"2-3s negative, 0.5s pause at bottom. **Last Set: Long-length Partials.**"},
    "paused assisted dip": {"reps": "8-10 reps", "advice":"2-3s negative, 1-2s pause at bottom. Break 90° elbow angle."},
    "inverse db zottman curl": {"reps": "10-12 reps", "advice":"Hammer curl on positive, palms-up grip on the negative."},
    "super-rom db lateral raise": {"reps": "12-15 reps", "advice":"Full ROM to overhead. Squeeze upper traps at the top."},
    "cable reverse fly": {"reps": "5, 4, 3+ reps", "advice":"**Mechanical Dropset:** 3 steps back (5 reps) -> 1 step fwd (4 reps) -> 1 step fwd (3+ reps)."},

    "lying leg curl": {"reps": "8-10 reps", "advice":"Big stretch at bottom. No butt popping! **Last Set: Long-length Partials.**"},
    "leg press": {"reps": "8 reps", "advice":"Feet low on platform. Deep stretch with 1s pause at bottom."},
    "paused barbell rdl": {"reps": "8 reps", "advice":"1s pause at bottom. Bottom 3/4 range of motion only (don't lock out)."},
    "machine hip adduction": {"reps": "10-12 reps", "advice":"Mind-muscle connection with inner thighs—push them hard. Without rest super set with sissy squat"},
    "sissy squat": {"reps": "10-12 reps", "advice":"Knees forward past toes. Push hard!"},
    "standing calf raise": {"reps": "10-12 reps", "advice":"1-2s pause at bottom. **Last Set: 30s Static Stretch.**"},
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

def define_meal() -> str:
    central_tz = zoneinfo.ZoneInfo("America/Chicago")
    current_hour = datetime.now(central_tz).hour

    #sample times
    if 5 <= current_hour < 11: return "breakfast"
    elif 11 <= current_hour < 16: return "lunch"
    elif 16 <= current_hour < 22: return "dinner"
    else: return "snack"

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
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_API_KEY}&query={food_query}&pageSize=3&dataType=Foundation,Survey%20(FNDDS),Branded,SR%20Legacy"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            data = response.json()
            options = []
            if data.get('foods'):
                food = data['foods'][0]
                # Extract nutrients (protein, fat, carbs)
                calories = next((n['value'] for n in food['foodNutrients'] if 'Energy' in n['nutrientName']), 0)
                protein = next((n['value'] for n in food['foodNutrients'] if 'Protein' in n['nutrientName']), 0)
                carbs = next((n['value'] for n in food['foodNutrients'] if 'Carbohydrate' in n['nutrientName']), 0)
                fat = next((n['value'] for n in food['foodNutrients'] if 'Total lipid' in n['nutrientName']), 0)
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
    #3 minute timer
    await asyncio.sleep(180) 
    reminder = f"**3-Minute Rest Over!**\nTime for **Set {next_set}** of *{exercise_name.title()}*.\n Target: {target_desc}"
    async with httpx.AsyncClient() as http_client:
        await http_client.post(TELEGRAM_API_URL, json={
            "chat_id": chat_id, "text": reminder, "parse_mode": "Markdown"
        })

# --- NEW: Abstracted Saving & Coaching Engine ---
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
        insert_payload["created_at"] = f"{food_data.extracted_date}T12:00:00-05:00" 

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

    profile = supabase.table("user_profiles").select("*").eq("chat_id", chat_id).execute()

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
            f"My daily totals are now: {total_pro}g protein, {total_fat}g fat, {total_cal} cals. "
            f"I have {rem_pro}g of protein and {rem_cal} calories left to hit my targets. "
            f"Give me exactly ONE short, punchy sentence of advice. "
            f"If protein is lagging, suggest something like a scoop of Ascent Native Fuel Whey or a lean meat. "
            f"If fat or calories are getting too high, tell me to dial it back."
        )

        advice_res = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": advice_prompt}],
            model="llama-3.1-8b-instant"
        )
        coach_advice = advice_res.choices[0].message.content.strip()

        daily_summary = (
            f"\n\n **Daily Status:**\n"
            f" Protein: **{total_pro}g** / {target_pro}g *(Need {rem_pro}g more)*\n"
            f" Calories: **{total_cal}** / {target_cal}\n\n"
            f" *{coach_advice}*"
        )
    else:
        daily_summary = "\n\n *Profile not found in database. Add your baseline to get macro coaching!*"

    reply = (
        f" **Logged for {meal_type.capitalize()}!**\n"
        f" *{food_data.food_name.title()}*\n"
        f" **{food_data.calories} kcal** | {food_data.protein}g P | {food_data.carbs}g C | {food_data.fat}g F"
        f"{daily_summary}"
    )

    await send_telegram_reply(chat_id, reply)

# Webhook endpoint
@app.post("/api/v1/webhook")
async def telegram_webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
    except Exception as e:
        # 2. Return a 400 error if JSON is malformed
        print(f"Error parsing JSON: {e}")
        return {"status": "error", "message": "Invalid JSON"}
    
    try:
        # --- NEW: HANDLE BUTTON CLICKS ---
        if "callback_query" in payload:
            callback = payload["callback_query"]
            chat_id = callback["message"]["chat"]["id"]
            callback_data = callback["data"]
            
            if chat_id not in PENDING_LOGS:
                await send_telegram_reply(chat_id, "Session expired. Please re-enter your meal.")
                return {"status": "success"}
                
            pending_data = PENDING_LOGS[chat_id]
            raw_text = pending_data["raw_text"]
            # 1. User clicked a USDA result
            if callback_data.startswith("usda_"):
                index = int(callback_data.split("_")[1])
                selected_food = pending_data["usda_options"][index]
                
                schema_string = json.dumps(FoodStructure.model_json_schema())
                system_instructions = (
                    f"Return a flat JSON object matching this schema: {schema_string}. "
                    f"The user ate: '{raw_text}'. "
                    f"Use this EXACT baseline data to calculate the final macros based on their portion: "
                    f"{json.dumps(selected_food)}. Extract 'extracted_date' and 'extracted_meal_type' if present."
                )
                
                response = groq_client.chat.completions.create(
                    messages=[{"role": "system", "content": system_instructions}],
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"}
                )
                response_dict = json.loads(response.choices[0].message.content)
                clean_dict = {k: v for k, v in response_dict.items() if v is not None}
                food_data = FoodStructure.model_validate(clean_dict)
            # 2. User clicked AI Fallback
            elif callback_data == "ai_fallback":
                schema_string = json.dumps(FoodStructure.model_json_schema())
                system_instructions = f"Analyze meal text, extract properties, and estimate nutrition. Return ONLY a valid JSON object matching this schema exactly: {schema_string}. CRITICAL: Return a flat JSON object. Do NOT wrap your response in a 'properties' key. IMPORTANT: If the user specifies a past date (like 6/10/26) or a meal type (like lunch), extract them into 'extracted_date' (format as YYYY-MM-DD) and 'extracted_meal_type'."
                
                response = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": f"Analyze this meal text: '{raw_text}'"}
                    ],
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"}
                )
                food_data = FoodStructure.model_validate_json(response.choices[0].message.content)

            # Clear memory and trigger saving engine
            del PENDING_LOGS[chat_id]
            await process_and_save_meal(chat_id, food_data)
            
            # Edit the original message to remove the buttons
            async with httpx.AsyncClient() as http_client:
                await http_client.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageReplyMarkup", json={
                    "chat_id": chat_id,
                    "message_id": callback["message"]["message_id"],
                    "reply_markup": {"inline_keyboard": []}
                })

            return {"status": "success"}

        # --- NORMAL MESSAGE LOGIC CONTINUES BELOW ---
        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_text = message.get("text", "").strip()

    
        if not user_text or not chat_id:
            return {"status": "ignored"}
        
        if user_text == "/start":
            welcome_message = "Welcome to the workout or meal tracker: Are you logging a workout or meal? If meal start message with '/meal' If workout start message with '/upper' or '/lower' If updating profile with updated BMR information start message with '/profile'"
            await send_telegram_reply(chat_id, welcome_message)
            return {"status": "success"}
        if user_text.lower() == ("/upper_1"):
            upper_1_menu = (
                "**JEFF NIPPARD UPPER DAY 1 CHECKLIST**\n\n"
                "**cuffed behind-the-back Lateral Raise** (10-12 reps) (3 sets)\n"
                "**cross-body lat pull-around** (10-12 reps) (3 sets)\n"
                "**low incline smith machine press** (8-10 reps) (4 sets)\n"
                "**chest-supported machine row** (8-10 reps) (3 sets)\n"
                "**overhead cable tricep extensions (bar)** (8-10 reps) (2 sets)\n"
                "**straight-bar lat prayer** (12-15 reps) (3 sets)\n"
                "**pec deck (with integrated partials)** (12-15 reps) (3 sets)\n"
                "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            )
            await send_telegram_reply(chat_id, upper_1_menu)
            return {"status": "success"}
        if user_text.lower() == ("/upper_2"):
            upper_2_menu = (
                "**JEFF NIPPARD UPPER DAY 2 CHECKLIST**\n\n"
                "**super-rom overhand cable row** (10-12 reps) (3 sets)\n"
                "**machine shoulder press** (10-12 reps) (3 sets)\n"
                "**assisted pull-up** (8-10 reps) (3 sets)\n"
                "**paused assisted dip** (8-10 reps) (3 sets)\n"
                "**inverse db zottman curl** (10-12 reps) (2 sets)\n"
                "**super-rom db lateral raise** (12-15 reps) (3 sets)\n"
                "**cable reverse fly (mechanical dropset on all sets)** (5,4,3+ reps) (3 sets)\n"
                "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            )
            await send_telegram_reply(chat_id, upper_2_menu)
            return {"status": "success"}
        if user_text.lower() == ("/lower_1"):
            lower_1_menu = (
                "**JEFF NIPPARD LOWER DAY 1 CHECKLIST**\n\n"
                "**seated leg curl** (8-10 reps) (3 sets)\n"
                "**machine hip adduction** (10-12 reps) (3 sets)\n"
                "**hack squat** (4,6,8 reps) (3 sets)\n"
                "**leg extension** (10-12 reps) (3 sets)\n"
                "**leg press calf press** (12-15 reps) (3 sets)\n\n"
                "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            )
            await send_telegram_reply(chat_id, lower_1_menu)
            return {"status": "success"}
        if user_text.lower() == ("/lower_2"):
            lower_2_menu = (
                "**JEFF NIPPARD LOWER DAY 2 CHECKLIST**\n\n"
                "**lying leg curl** (8-10 reps) (3 sets)\n"
                "**leg press** (8 reps) (3 sets)\n"
                "**paused barbell rdl** (8 reps) (2 sets)\n"
                "**machine hip adduction (super set with sissy squat)** (10-12 reps) (3 sets)\n"
                "**sissy squat (super set with machine hip adduction)** (10-12 reps) (3 sets)\n\n"
                "**standing calf raise** (10-12 reps) (3 sets)\n"
                "**Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            )
            await send_telegram_reply(chat_id, lower_2_menu)
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
            
            # Simplified schema: Groq only needs to find 2 variables now
            class ProfileInput(BaseModel):
                weight: float
                goal: str
                body_fat_percentage: float
                total_body_water: float
                dry_lean_mass: float
                skeletal_muscle_mass: float # SMM
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
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
        
            profile_data = ProfileInput.model_validate_json(response.choices[0].message.content)
            weight = profile_data.weight
            height = profile_data.height
            age = profile_data.age
            goal = profile_data.goal.lower()
            bmr = (10 * (weight / 2.2)) + (6.25 * (height * 2.54)) - (5 * age) + 5
            tdee = bmr * 1.55

            # --- THE MACRO MATH ENGINE ---
            if "cut" in goal:
                cals = tdee - 500
            elif "bulk" in goal:
                cals = tdee + 500
            else: 
                cals = tdee - 100

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
        
        base_keywords = ["bench", "squat", "deadlift", "reps", "sets", "lbs", "lift", "press", "curls", "workout", "pounds", "row", "pulldown", "fly", "raise", "extension", "crunch", "rdl", "step up", "toe-press"] 
        workout_keywords = base_keywords + list(PROGRESSION_SCHEMA.keys())
        is_workout = any(word in user_text.lower() for word in workout_keywords) or user_text.lower().startswith("w:") or "upper:" in user_text.lower() or "lower:" in user_text.lower()

        if is_workout:

            clean_text = user_text.replace("workout:", "").replace("upper", "").replace("lower", "").replace("w", "").strip()
            schema_string = json.dumps(WorkoutStructure.model_json_schema())
            official_names = ", ".join(PROGRESSION_SCHEMA.keys())
            system_instructions = f"You are a data extractor. Return ONLY a valid JSON object matching this schema exactly: {schema_string}. IMPORTANT: You must standardize the exercise_name to match one of these official names if it is similar: {official_names}. If the user mentions an exercise but provides no numbers for weight or reps, return 0 for both."            
            response = groq_client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": f"Extract parameters from this performed set text: '{clean_text}'"}
                ],
                model="llama-3.3-70b-versatile",
                response_format={"type": "json_object"}
            )
            lift_data = WorkoutStructure.model_validate_json(response.choices[0].message.content)
            exercise = lift_data.exercise_name.lower().strip()


            if lift_data.reps == 0:
                today_str = date.today().isoformat()

                coaching_data = EXERCISE_COACHING.get(exercise, {"reps": "8-12 reps", "advice": "Normal working set to hypertrophy depth."})
                intensity_advice = coaching_data["advice"]
                
                # Fetch the most recent past logs for this exercise
                history = supabase.table("exercise_logs") \
                    .select("weight, reps, set_number, created_at") \
                    .eq("exercise_name", exercise) \
                    .lt("created_at", today_str) \
                    .order("created_at", desc=True) \
                    .limit(5) \
                    .execute()

                if not history.data:
                    reply = f"**No history found for {exercise.title()}!**\nStart with a light warm-up weight to establish your baseline today.\n\n *Technique Cues:* {intensity_advice}"
                else:
                    last_date = history.data[0]['created_at'][:10]
                    last_session = [row for row in history.data if row['created_at'].startswith(last_date)]

                    history_text = "\n".join([f"• Set {row['set_number']}: {row['weight']} lbs × {row['reps']} reps" for row in sorted(last_session, key=lambda x: x['set_number'])])

                    heaviest_set = max(last_session, key=lambda x: x['weight'])
                    start_weight = heaviest_set['weight']

                    ex_schema = PROGRESSION_SCHEMA.get(exercise, PROGRESSION_SCHEMA["default"])
                    set_1_targets = ex_schema.get(1, {"max_reps": 12, "increment": 5})
                    target_reps = set_1_targets['max_reps']

                    rec_text = f"Your heaviest set last time was **{start_weight} lbs**. Load that up for Set 1 today and aim for **{target_reps} reps**!"

                    reply = f"**Last Session: {exercise.title()}** ({last_date})\n\n{history_text}\n\n **Target:** {rec_text}\n\n *Technique Cues:* {intensity_advice}"

                await send_telegram_reply(chat_id, reply)
                return {"status": "success"}

            today_str = date.today().isoformat()
            existing_sets = supabase.table("exercise_logs") \
                .select("id") \
                .eq("exercise_name", exercise) \
                .gte("created_at", today_str) \
                .execute()
            
            set_count = len(existing_sets.data) + 1

            central_tz = zoneinfo.ZoneInfo("America/Chicago")
            supabase.table("exercise_logs").insert({
                "exercise_name": exercise,
                "weight": lift_data.weight,
                "reps": lift_data.reps,
                "set_number": set_count,
                "created_at": datetime.now(central_tz).isoformat()
            }).execute()

            total_target_sets = 1
            rep_guideline = "8-12 reps"
            intensity_advice = "Normal working set to hypertrophy depth."
            message = ""

            progress_message = ""

            # # --- UPPER #1 ---
            # if "cuffed behind-the-back lateral raise" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "10-12 reps"
            #     intensity_advice = "Raise the cables up and out in a 'Y' motion. Connect with middle delt fibers. **Last Set: Myo-reps!**"
            # elif "cross-body lat pull-around" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "10-12 reps"
            #     intensity_advice = "Keep cable and wrist in a straight line. **Last Set: Long-length Partials on all reps.**"
            # elif "low incline smith machine press" in exercise:
            #     total_target_sets = 4
            #     rep_guideline = "8-10 reps"
            #     intensity_advice = "15° incline. 1s pause on chest. **Last Set: 30s Pec Static Stretch hold.**"
            # elif "chest-supported machine row" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "8-10 reps"
            #     intensity_advice = "Flare elbows ~45°. Squeeze blades hard at top. **Last Set: Long-length Partials.**"
            # elif "overhead cable tricep extension" in exercise:
            #     total_target_sets = 2
            #     rep_guideline = "8-10 reps"
            #     intensity_advice = "Nasty stretch on negative, 1s pause at bottom. **Last Set: Dropset.**"
            # elif "straight-bar lat prayer" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "12-15 reps"
            #     intensity_advice = "Deep stretch at top, squeeze lats at bottom. **Last Set: Long-length Partials.**"
            # elif "pec deck" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "12-15 reps"
            #     intensity_advice = "**Integrated Partials:** Alternate 1 full ROM rep with 1 bottom-half partial rep."

            # # --- LOWER #1 ---
            # elif "seated leg curl" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "8-10 reps"
            #     intensity_advice = "Lean forward to maximize hamstring stretch."
            # elif "machine hip adduction" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "10-12 reps"
            #     intensity_advice = "Mind-muscle connection with inner thighs—push them hard."
            # elif "hack squat" in exercise:
            #     total_target_sets = 3
            #     # Reverse Pyramid logic: 4, 6, 8 reps
            #     reps_map = {1: 4, 2: 6, 3: 8}
            #     rep_guideline = f"{reps_map.get(set_count, 8)} reps (Reverse Pyramid)"
            #     intensity_advice = "Set 1: Heaviest. Set 2: -10-15%. Set 3: -10-15%."
            # elif "leg extension" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "10-12 reps"
            #     intensity_advice = "2-3s negative. Feel quads pulling apart. **Last Set: Long-length Partials.**"
            # elif "leg press calf press" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "12-15 reps"
            #     intensity_advice = "1-2s pause at bottom. Roll ankles on balls of feet. **Last Set: 30s Static Stretch.**"

            # # --- UPPER #2 ---
            # elif "super-rom overhand cable row" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "10-12 reps"
            #     intensity_advice = "Wide-grip pulldown bar. Lean forward on negative, upright on pull."
            # elif "machine shoulder press" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "10-12 reps"
            #     intensity_advice = "Elbows at 90°. Smooth, controlled reps. **Last Set: Dropset.**"
            # elif "assisted pull-up" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "8-10 reps"
            #     intensity_advice = "2-3s negative, 0.5s pause at bottom. **Last Set: Long-length Partials.**"
            # elif "paused assisted dip" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "8-10 reps"
            #     intensity_advice = "2-3s negative, 1-2s pause at bottom. Break 90° elbow angle."
            # elif "inverse db zottman curl" in exercise:
            #     total_target_sets = 2
            #     rep_guideline = "10-12 reps"
            #     intensity_advice = "Hammer curl on positive, palms-up grip on the negative."
            # elif "super-rom db lateral raise" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "12-15 reps"
            #     intensity_advice = "Full ROM to overhead. Squeeze upper traps at the top."
            # elif "cable reverse fly" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "5, 4, 3+ reps"
            #     intensity_advice = "**Mechanical Dropset:** 3 steps back (5 reps) -> 1 step fwd (4 reps) -> 1 step fwd (3+ reps)."

            # # --- LOWER #2 ---
            # elif "lying leg curl" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "8-10 reps"
            #     intensity_advice = "Big stretch at bottom. No butt popping! **Last Set: Long-length Partials.**"
            # elif "leg press" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "8 reps"
            #     intensity_advice = "Feet low on platform. Deep stretch with 1s pause at bottom."
            # elif "paused barbell rdl" in exercise:
            #     total_target_sets = 2
            #     rep_guideline = "8 reps"
            #     intensity_advice = "1s pause at bottom. Bottom 3/4 range of motion only (don't lock out)."
            # elif "machine hip adduction" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "10-12 reps"
            #     intensity_advice = "Mind-muscle connection with inner thighs—push them hard. Without rest super set with sissy squat"
            # elif "sissy squat" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "10-12 reps"
            #     intensity_advice = "Knees forward past toes. Push hard!"
            # elif "standing calf raise" in exercise:
            #     total_target_sets = 3
            #     rep_guideline = "10-12 reps"
            #     intensity_advice = "1-2s pause at bottom. **Last Set: 30s Static Stretch.**"

            # --- DYNAMIC TARGETS & COACHING ENGINE ---
            ex_schema = PROGRESSION_SCHEMA.get(exercise, PROGRESSION_SCHEMA["default"])
            total_target_sets = len(ex_schema)

            coaching_data = EXERCISE_COACHING.get(exercise, {"reps": "8-12 reps", "advice": "Normal working set to hypertrophy depth."})
            rep_guideline = coaching_data["reps"]
            intensity_advice = coaching_data["advice"]
            # --- UNIFIED PROGRESSION & TIMER LIFE CYCLE ---
            if set_count >= total_target_sets:
                advice = f"**Exercise Complete!** All {total_target_sets} configured sets mapped successfully.\n *Next Move:* Proceed directly to your next movement assignment."
            else:
                next_set_count = set_count + 1
                # Generate specific next-set instructions for the rest reminder configuration
                if "flat dumbbell" in exercise or "flat db" in exercise or "hack squat" in exercise:
                    next_guideline = "8-10 reps (Hypertrophy Back-off)"
                else:
                    next_guideline = rep_guideline
                    
                advice = f" **Set logged smoothly.** Prepare for Set {next_set_count} of {total_target_sets}.\n *Next Target:* {next_guideline}"
                
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
                ex_schema = PROGRESSION_SCHEMA.get(exercise, PROGRESSION_SCHEMA["default"])
                current_targets = ex_schema.get(set_count, {"max_reps": 12, "increment": 5})

                max_reps = current_targets['max_reps']
                increment = current_targets['increment']

                if max_reps >= 10:
                    rep_floor = max_reps - 3
                elif max_reps >= 6:
                    rep_floor = max_reps - 2
                else:
                    rep_floor = max_reps - 1

                is_assisted = any(ex in exercise for ex in ["assisted pull-up", "paused assisted dip"])
                is_reverse_pyramid = any(ex in exercise for ex in ["hack squat", "leg extension"])
                if is_reverse_pyramid and set_count > 1:
                    drop_weight = max(0, lift_data.weight - 10)
                    next_set_advice = f"\n\n *Next Set Target:* Drop weight for back-off set. Target **{drop_weight} lbs** for {max_reps} reps (Reverse Pyramid)."
                elif is_assisted:
                    # ASSISTED LOGIC: Less assistance weight = harder (progressing forward)
                    if lift_data.reps >= max_reps:
                        next_weight = max(0, lift_data.weight - increment) # Reduce assistance weight!
                        next_set_advice = f"\n\n *Next Set Target:* You crushed the rep cap! Reduce assistance weight down to **{next_weight} lbs**."
                    elif lift_data.reps < rep_floor:
                        next_weight = lift_data.weight + increment # Add assistance weight if struggling
                        next_set_advice = f"\n\n *Next Set Target:* That looked heavy. Add assistance up to **{next_weight} lbs** to stay in the target zone."
                    else:
                        next_weight = lift_data.weight
                        next_set_advice = f"\n\n *Next Set Target:* Stick with **{next_weight} lbs** assistance and try to push closer to {max_reps} reps."
                else:
                    if lift_data.reps >= max_reps:
                        next_weight = lift_data.weight + increment
                        next_set_advice = f"\n\n *Next Set Target:* You crushed the rep cap! Bump up to **{next_weight} lbs**."
                    elif lift_data.reps < rep_floor:
                        next_weight = max(0, lift_data.weight - increment) 
                        next_set_advice = f"\n\n *Next Set Target:* That looked heavy. Drop to **{next_weight} lbs** to stay in the target zone."
                    else:
                        next_weight = lift_data.weight
                        next_set_advice = f"\n\n *Next Set Target:* Stick with **{next_weight} lbs** and try to push closer to {max_reps} reps."
            
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
        elif user_text.lower().startswith("meal:"):
            clean_food_text = user_text.lower().replace("meal:", "").replace("f:", "").strip()
            search_prompt = f"Extract ONLY the core food ingredient or restaurant item to search in a database from this text: '{clean_food_text}'. Do not include portions, meal types, or dates. Return just the search string."
            search_res = groq_client.chat.completions.create(
                messages=[{"role": "user", "content": search_prompt}],
                model="llama-3.1-8b-instant"
            )
            search_query = search_res.choices[0].message.content.strip().replace('"', '')

            usda_results = await get_usda_macros(search_query)

            PENDING_LOGS[chat_id] = {
                "raw_text": clean_food_text,
                "usda_options": usda_results
            }

            keyboard = {"inline_keyboard": []}
            
            if usda_results:
                msg_text = f" Found {len(usda_results)} results for **{search_query}**.\nSelect the most accurate option to log it:"
                for i, item in enumerate(usda_results):
                    btn_text = f"{item['food_name'][:30]}... ({item['calories']} kcal)"
                    keyboard["inline_keyboard"].append([{"text": btn_text, "callback_data": f"usda_{i}"}])
            else:
                msg_text = f" No exact USDA match found for **{search_query}**. Would you like the AI to estimate the macros?"

            # Always offer the AI fallback button
            keyboard["inline_keyboard"].append([{"text": "Use AI Estimation instead", "callback_data": "ai_fallback"}])

            # Send the approval request
            await send_telegram_reply(chat_id, msg_text, reply_markup=keyboard)

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