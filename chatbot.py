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
from pydantic import BaseModel
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

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

USDA_API_KEY = os.getenv("USDA_API_KEY")

PROGRESSION_SCHEMA = {
    # --- UPPER BODY ---
    "flat dumbbell press": { 
        1: {"max_reps": 6, "increment": 5},   # Heavy Top Set (4-6)
        2: {"max_reps": 10, "increment": 5}   # Back-off Set (8-10)
    },
    "cable fly": { 
        1: {"max_reps": 6, "increment": 5},   # Heavy Top Set (4-6)
        2: {"max_reps": 10, "increment": 5}   # Back-off Set (8-10)
    },
    "lat pulldown": { 
        1: {"max_reps": 12, "increment": 10}, # Overhand Mid (10-12)
        2: {"max_reps": 12, "increment": 10}  # Underhand Close (10-12)
    },
    "overhead cable tricep extension": { 
        1: {"max_reps": 15, "increment": 10}, # Working set (12-15) + Dropset
    },
    "machine lateral raise": { 
        1: {"max_reps": 15, "increment": 5},  # (12-15) - 5lb jump optimal here
    },
    "high incline smith press": { 
        1: {"max_reps": 12, "increment": 10}, # Antagonistic pairing 1 (10-12)
        2: {"max_reps": 12, "increment": 10}
    },
    "t-bar row": { 
        1: {"max_reps": 12, "increment": 10}, # Antagonistic pairing 2 (10-12)
        2: {"max_reps": 12, "increment": 10}
    },
    "ez-bar bicep curl": { 
        1: {"max_reps": 15, "increment": 5},  # (12-15) + Myoreps 
    },
    "cable crunch": { 
        1: {"max_reps": 15, "increment": 10}, # (12-15) + Double drop set
    },

    # --- LOWER BODY ---
    "dumbbell romanian deadlift": { 
        1: {"max_reps": 10, "increment": 10}, # (8-10)
        2: {"max_reps": 10, "increment": 10}  # (8-10)
    },
    "dumbbell step up": { 
        1: {"max_reps": 10, "increment": 5},  # (8-10) per leg - 5lb jump optimal
    },
    "seated leg press toe-press": { 
        1: {"max_reps": 15, "increment": 10}, # (12-15)
    },
    "hack squat": { 
        1: {"max_reps": 6, "increment": 10},  # Heavy Top Set (4-6)
        2: {"max_reps": 10, "increment": 10}  # Back-off Set (8-10)
    },
    "seated leg curl": { 
        1: {"max_reps": 12, "increment": 5}   # (10-12) + Dropset
    },
    
    # --- DEFAULT FALLBACK ---
    "default": {
        1: {"max_reps": 12, "increment": 5},
        2: {"max_reps": 12, "increment": 5},
        3: {"max_reps": 12, "increment": 5}
    }
}

class FoodStructure(BaseModel):
    food_name: str
    calories: int
    protein: int
    carbs: int
    fat: int

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

async def send_telegram_reply(chat_id: int, text: str):
    async with httpx.AsyncClient() as http_client:
        await http_client.post(TELEGRAM_API_URL, json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })

async def get_usda_macros(food_query: str):
    url = f"https://api.nal.usda.gov/fdc/v1/foods/search?api_key={USDA_API_KEY}&query={food_query}&pageSize=1"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            data = response.json()
            if data.get('foods'):
                food = data['foods'][0]
                # Extract nutrients (protein, fat, carbs)
                calories = next((n['value'] for n in food['foodNutrients'] if 'Energy' in n['nutrientName']), 0)
                protein = next((n['value'] for n in food['foodNutrients'] if 'Protein' in n['nutrientName']), 0)
                carbs = next((n['value'] for n in food['foodNutrients'] if 'Carbohydrate' in n['nutrientName']), 0)
                fat = next((n['value'] for n in food['foodNutrients'] if 'Total lipid' in n['nutrientName']), 0)
                return {
                    "food_name": food['description'],
                    "calories": int(calories),
                    "protein": int(protein),
                    "carbs": int(carbs),
                    "fat": int(fat)
                }
        except Exception as e:
            print(f"USDA API Error: {e}")
            return None
    return None

async def delayed_rest_reminder(chat_id: int, exercise_name: str, next_set: int, target_desc: str):
    #3 minute timer
    await asyncio.sleep(180) 
    reminder = f"**3-Minute Rest Over!**\nTime for **Set {next_set}** of *{exercise_name.title()}*.\n🎯 Target: {target_desc}"
    async with httpx.AsyncClient() as http_client:
        await http_client.post(TELEGRAM_API_URL, json={
            "chat_id": chat_id, "text": reminder, "parse_mode": "Markdown"
        })

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
    
        # extract text and chat ID from Telegram's structure
        message = payload.get("message", {})
        chat_id = message.get("chat", {}).get("id")
        user_text = message.get("text", "").strip()
    
        if not user_text or not chat_id:
            return {"status": "ignored"}
        
        if user_text == "/start":
            welcome_message = "Welcome to the workout or meal tracker: Are you logging a workout or meal? If meal start message with '/meal' If workout start message with '/upper' or '/lower' If updating profile with updated BMR information start message with '/profile'"
            await send_telegram_reply(chat_id, welcome_message)
            return {"status": "success"}
        if user_text.lower() == ("/upper"):
            upper_menu = (
                "🏋️‍♂️ **JEFF NIPPARD UPPER DAY CHECKLIST**\n\n"
                "1️⃣ **Flat Dumbbell Press** (Heavy Top Set (4-6 reps) + Back-off (8-10 reps))\n"
                "2️⃣ **Cable Fly** (Heavy Top Set (4-6) + Back-off (8-10 reps))\n"
                "3️⃣ **2-Grip Lat Pulldown** (Overhand Mid (10-12 reps) / Underhand Close (10-12 reps))\n"
                "4️⃣ **Overhead Cable Tricep Extension** (+ Drop Set) (12-15 reps)\n"
                "5️⃣ **Machine Lateral Raise** (12-15 reps)\n"
                "6️⃣ **High Incline Smith Press** (Agnostic Superset) (10-12 reps)\n"
                "7️⃣ **T-Bar Row** (Wide Grip / Close Grip) (Agnostic Superset (10-12 reps)\n"
                "8️⃣ **EZ-Bar Bicep Curl** (+ Myoreps Supination Focus) (12-15 reps + Myo-reps)\n"
                "9️⃣ **Cable Crunch** (12-15 reps + Double Dropset)\n\n"
                "📋 **Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. upper: Flat db press 75 lbs for 6 reps)\n\n"
            )
            await send_telegram_reply(chat_id, upper_menu)
            return {"status": "success"}
        if user_text.lower() == "/lower":
            lower_menu = (
                "🏋️‍♀️ **JEFF NIPPARD LOWER DAY CHECKLIST**\n\n"
                "1️⃣ **Dumbbell Romanian Deadlift (RDL)** (Controlled Hamstring Stretch) (8-10 reps)\n"
                "2️⃣ **Dumbbell Step Up** (Per Leg Isolation with Lifting Straps) (8-10 reps)\n"
                "3️⃣ **Seated Leg Press Toe-Press** (+ Heavy Dropset to Failure) (12-15 reps)\n"
                "4️⃣ **Hack Squat ** (Heavy Top Set (4-6 reps) + Mind-Muscle Back-off (8-10 reps))\n"
                "5️⃣ **Seated Leg Curl** (+ Forward Lean Dropset Finisher) (10-12 reps)\n\n"
                "📋 **Ready to log!** Just conversationally type in your current exercise, weight, and reps below to permanently store your performance set. (ie. lower: RDL 60 lbs 10 reps)\n\n"
            )
            await send_telegram_reply(chat_id, lower_menu)
            return {"status": "success"}
        if user_text.lower() == "/meal":
            meal_instructions = (
                "🍔 **NUTRITION LOGGING ENGINE**\n\n"
                "You can log your food conversationally without worrying about exact serving math. "
                "The system will automatically categorize it based on the time of day and calculate your macros into Supabase.\n\n"
                "📋 **How to log:**\n"
                "Simply text me what you ate naturally. If your message doesn't contain lifting terms (like lbs or reps), it defaults to a food log!\n\n"
                "💬 **Examples:**\n"
                "• *'meal: 3 eggs and a scoop of ascent native fuel whey protein powder'*\n"
                "• *'meal: chicken korma with two pieces of garlic naan'*\n"
                "• *'meal: a slice of homemade tiramisu'* Kettle bell\n\n"
                "👉 *Just start your message with 'meal:' followed by your food to save it!*"
            )
            await send_telegram_reply(chat_id, meal_instructions)
            return {"status": "success"}
        
        if user_text.lower() == "/profile":
            profile_instructions = (
                "Profile Setup \n\n"
                "You can log your Body Scan results and goal to save it and train the machine learning model. "
                "The system will automatically use your goal and categories your food based on the time of day and calculate your macros into Supabase.\n\n"
                "👉 *Just start your message with 'profile:' followed by your data in the following format so I can update your macro targets: Body Composition: [Water], [Dry Lean Mass], [Fat Mass], [Weight]; Muscle-Fat: [Weight], [SMM], [Body Fat Mass]; Obesity: [BMI], [PBF]; Segmental Lean: [Left Arm %], [Right Arm %], [Left Leg %], [Right Leg %]; Goal: [bulk/cut/recomposition]*"
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

            schema_string = json.dumps(ProfileInput.model_json_schema())
            system_instructions = (
                "You are an expert fitness data parser. "
                "The user will provide data in these categories: "
                "1. Body Composition (Total Body Water, Dry Lean Mass, Fat Mass, Weight). "
                "2. Muscle-Fat Analysis (Weight, SMM, Fat Mass). "
                "3. Obesity Analysis (BMI, PBF). "
                "4. Segmental Lean Analysis (Left Arm %, Right Arm %, Left Leg %, Right Leg %). "
                "5. Goal (bulk, cut, or recomposition)"
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
            goal = profile_data.goal.lower()
            lbm_lbs = weight * (1 - (profile_data.body_fat_percentage / 100))
            bmr = 370 + (21.6 * (lbm_lbs / 2.20462)) # Converted to kg for the formula
            tdee = bmr * 1.55 # Using 1.55 as a moderate activity baseline

            # --- THE MACRO MATH ENGINE ---
            if "cut" in goal:
                cals = int(tdee * 12)
            elif "bulk" in goal:
                cals = int(tdee * 18)
            else: 
                # Maintenance or Recomposition
                cals = int(weight * 15)

            protein = int(weight * 1.0)
            fat = int(weight * 0.4)
            
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
        
        workout_keywords = ["bench", "squat", "deadlift", "reps", "sets", "lbs", "lift", "press", "curls", "workout", "pounds", "row", "pulldown", "fly", "raise", "extension", "crunch", "rdl", "step up", "toe-press"] 
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


            if lift_data.weight == 0 or lift_data.reps == 0:
                today_str = date.today().isoformat()
                
                # Fetch the most recent past logs for this exercise
                history = supabase.table("exercise_logs") \
                    .select("weight, reps, set_number, created_at") \
                    .eq("exercise_name", exercise) \
                    .lt("created_at", today_str) \
                    .order("created_at", desc=True) \
                    .limit(5) \
                    .execute()

                if not history.data:
                    reply = f"🆕 **No history found for {exercise.title()}!**\nStart with a light warm-up weight to establish your baseline today."
                else:
                    # Filter to group only the sets from the absolute last session
                    last_date = history.data[0]['created_at'][:10]
                    last_session = [row for row in history.data if row['created_at'].startswith(last_date)]
                    last_session.sort(key=lambda x: x['set_number'])

                    history_text = "\n".join([f"• Set {row['set_number']}: {row['weight']} lbs × {row['reps']} reps" for row in last_session])

                    # --- NEW DYNAMIC OVERLOAD MATH ---
                    set_1 = last_session[0]
                    
                    # Fetch the schema for this exercise, or use default
                    ex_schema = PROGRESSION_SCHEMA.get(exercise, PROGRESSION_SCHEMA["default"])
                    set_1_targets = ex_schema.get(1, {"max_reps": 12, "increment": 5})

                    if set_1['reps'] >= set_1_targets['max_reps']: 
                        # You hit the top of the range (e.g., 6 reps on the heavy set)
                        rec_weight = set_1['weight'] + set_1_targets['increment']
                        rec_text = f"You hit {set_1['reps']} reps last time. Bump your top set up to **{rec_weight} lbs** today!"
                    else:
                        # You didn't max out the range (e.g., 4 reps on the heavy set)
                        rec_weight = set_1['weight']
                        rec_text = f"You got {set_1['reps']} reps last time. Stick to **{rec_weight} lbs** and try to push for {set_1_targets['max_reps']} reps!"

                    reply = f"📊 **Last Session: {exercise.title()}** ({last_date})\n\n{history_text}\n\n💡 **Target:** {rec_text}"

                await send_telegram_reply(chat_id, reply)
                return {"status": "success"} #

            today_str = date.today().isoformat()
            existing_sets = supabase.table("exercise_logs") \
                .select("id") \
                .eq("exercise_name", exercise) \
                .gte("created_at", today_str) \
                .execute()
            
            set_count = len(existing_sets.data) + 1

            supabase.table("exercise_logs").insert({
                "exercise_name": exercise,
                "weight": lift_data.weight,
                "reps": lift_data.reps,
                "set_number": set_count
            }).execute()

            total_target_sets = 1
            rep_guideline = "8-12 reps"
            intensity_advice = "Normal working set to hypertrophy depth."
            message = ""

            progress_message = ""

            if "flat dumbbell" in user_text.lower() or "flat db" in user_text.lower() or "Flat Dumbbell Press" in user_text.lower():
                total_target_sets = 2
                if set_count == 1:
                    rep_guideline = "4-6 reps (Heavy Strength)"
                    intensity_advice = "Keep elbow tuck around 30-45 degrees, flare outward slightly on ascent."
                else:
                    rep_guideline = "8-10 reps (Hypertrophy Back-off)"
                    intensity_advice = "Drop the load back. Maximize mechanical tension."
            elif "cable fly" in exercise:
                total_target_sets = 2
                rep_guideline = "4-6 reps" if set_count == 1 else "8-10 reps (Light Back-off)"
                intensity_advice = "Focus on a deep stretch and tight squeeze at peak contraction."
            elif "lat pulldown" in exercise:
                total_target_sets = 2
                rep_guideline = "10-12 reps"
                intensity_advice = "Set 1: Overhand middle grip. Set 2: Underhand close grip. Drop load immediately after for overhead curls!"
            elif "tricep extension" in exercise or "overhead cable tricep extension" in exercise: 
                total_target_sets = 1
                rep_guideline = "12-15 reps"
                intensity_advice = "**Drop Set Active!** Hit baseline failure, instantly drop weight by 30-40%, then take it to absolute failure once more."
            elif "lateral raise" in exercise:
                total_target_sets = 1
                rep_guideline = "12-15 reps"
                intensity_advice = "Drive through your side delts. Push range of motion to 90 degrees or up comfortably."
            elif "smith machine press" in exercise or "incline smith" in exercise or "high incline smith press":
                total_target_sets = 2  # Part of your antagonistic pairing configuration
                rep_guideline = "10-12 reps"
                intensity_advice = "Ensure your bench incline is set between 45 and 60 degrees."
            elif "t-bar row" in exercise or "supported row" in exercise:
                total_target_sets = 2
                rep_guideline = "10-12 reps"
                intensity_advice = "Set 1: Use wider grip variation. Set 2: Switch to closer grip profile."
            elif "bicep curl" in exercise or "ez-bar" in exercise or "ez-bar bicep curl" in exercise:
                total_target_sets = 1
                rep_guideline = "12-15 reps"
                intensity_advice = "**Myoreps Multiplier!** Hit failure driving through pinkies for supination. Rest 3-4 secs, complete 4 reps; repeat micro-cycles until performance drops."
            elif "cable crunch" in exercise:
                total_target_sets = 1
                rep_guideline = "12-15 reps"
                intensity_advice = "**Double Dropset Matrix!** Hit failure $\rightarrow$ drop load by 30% to failure $\rightarrow$ drop load by another 20-30% to final failure."
            
            #LOWER BODY
            elif "romanian deadlift" in exercise or "rdl" in exercise or "dumbbell romanian deadlift":
                total_target_sets = 2
                rep_guideline = "8-10 reps"
                intensity_advice = "Push hips backward sequentially. Rebound smooth when hamstrings reach full length stretch."
                message = "way to go, one more set left" if set_count == 1 else "way to go, onto the next excercise"
            elif "step up" in exercise or "dumbbell step up":
                total_target_sets = 1
                rep_guideline = "8-10 reps (Per Leg)"
                intensity_advice = "Isolate working leg completely. Lock out and squeeze glutes heavily at the top apex."
                message = "way to go, onto the next excercise"

            elif "toe-press" in exercise or "calf raise" in exercise or "seated leg press toe-press":
                total_target_sets = 1
                rep_guideline = "12-15 reps"
                intensity_advice = "Keep knees static, don't bounce. Hit failure, drop load by 30-40%, then rep to absolute failure."
                message = "way to go, onto the next excercise"

            elif "hack squat" in exercise or "barbell back squat" in exercise:
                total_target_sets = 2
                if set_count == 1:
                    rep_guideline = "4-6 reps (Heavy Top Set)"
                    intensity_advice = "Aim for RPE 9 (1 rep in reserve). Drive through heels with maximum full depth."
                    message = "way to go, one more set left"
                else:
                    rep_guideline = "8-10 reps (Volume Focus)"
                    intensity_advice = "Drop load back. Control eccentric negative phase slowly to enhance mind-muscle connection."
                    message = "way to go, onto the next excercise"

            elif "leg curl" in exercise:
                total_target_sets = 1
                rep_guideline = "10-12 reps"
                intensity_advice = "Lean forward over the machine dashboard interface. Hit failure, drop load by 30-40%, run to secondary failure."
                message = "way to go, onto the next excercise"
                
            # --- UNIFIED PROGRESSION & TIMER LIFE CYCLE ---
            if set_count >= total_target_sets:
                advice = f"**Exercise Complete!** All {total_target_sets} configured sets mapped successfully.\n💡 *Next Move:* Proceed directly to your next movement assignment."
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
                
                # Fetch what they did for this specific set number last week
                past_next_set = supabase.table("exercise_logs") \
                    .select("weight, reps") \
                    .eq("exercise_name", exercise) \
                    .eq("set_number", next_set_count) \
                    .lt("created_at", today_str) \
                    .order("created_at", desc=True) \
                    .limit(1) \
                    .execute()

                if past_next_set.data:
                    last_run = past_next_set.data[0]
                    ex_schema = PROGRESSION_SCHEMA.get(exercise, PROGRESSION_SCHEMA["default"])
                    next_targets = ex_schema.get(next_set_count, {"max_reps": 12, "increment": 5})

                    if last_run['reps'] >= next_targets['max_reps']:
                        next_weight = last_run['weight'] + next_targets['increment']
                        next_set_advice = f"\n\n *Next Set Target:* Grab **{next_weight} lbs** (Last time: {last_run['weight']}lbs x {last_run['reps']})"
                    else:
                        next_weight = last_run['weight']
                        next_set_advice = f"\n\n *Next Set Target:* Stick with **{next_weight} lbs** and push for {next_targets['max_reps']} reps."
            
            # Update your final reply to include the dynamic next set advice
            reply_msg = (
                f" **Set {set_count} Tracked to Supabase:**\n"
                f" *{exercise.title()}*\n"
                f" **{lift_data.weight} lbs × {lift_data.reps} reps**\n"
                f" *Prescription Target:* {rep_guideline}\n\n"
                f" {intensity_advice}\n\n"
                f" {advice}{next_set_advice}"
            )
            await send_telegram_reply(chat_id, reply_msg)
        elif user_text.lower().startswith("meal:"):
            clean_food_text = user_text.lower().replace("meal:", "").replace("f:", "").strip()

            is_complex_meal = "," in clean_food_text or " and " in clean_food_text or " with " in clean_food_text or len(clean_food_text.split()) > 6

            raw_usda_data = None

            if not is_complex_meal:
                raw_usda_data = await get_usda_macros(clean_food_text)

            if raw_usda_data:
            
                # # --- AI Call 1: Extract Macros ---
                # schema_string = json.dumps(FoodStructure.model_json_schema())
                # system_instructions = f"Analyze meal text, extract properties, and estimate nutrition. Return ONLY a valid JSON object matching this schema exactly: {schema_string}"        
            
                # response = groq_client.chat.completions.create(
                #     messages=[
                #         {"role": "system", "content": system_instructions},
                #         {"role": "user", "content": f"Analyze this meal text: '{clean_food_text}'"}
                #     ],
                #     model="llama-3.3-70b-versatile",
                #     response_format={"type": "json_object"}
                # )
        
                food_data = FoodStructure(**raw_usda_data)
            else:
                schema_string = json.dumps(FoodStructure.model_json_schema())
                system_instructions = f"Analyze meal text, extract properties, and estimate nutrition. Return ONLY a valid JSON object matching this schema exactly: {schema_string}"
                response = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_instructions},
                        {"role": "user", "content": f"Analyze this meal text: '{clean_food_text}'"}
                    ],
                    model="llama-3.3-70b-versatile",
                    response_format={"type": "json_object"}
                )
                food_data = FoodStructure.model_validate_json(response.choices[0].message.content)
                
            meal_type = define_meal()

            # Save the current meal to the database
            supabase.table("food_logs").insert({
                "meal_type": meal_type,
                "food_name": food_data.food_name,
                "calories": food_data.calories,
                "protein": food_data.protein,
                "carbs": food_data.carbs,
                "fat": food_data.fat
            }).execute()

            # --- THE DAILY SUMMARY & COACHING ENGINE ---
            today_str = date.today().isoformat()
            
            # 1. Fetch all meals logged today
            daily_logs = supabase.table("food_logs") \
                .select("calories, protein, carbs, fat") \
                .gte("created_at", today_str) \
                .execute()

            # Calculate today's running totals
            total_cal = sum(log['calories'] for log in daily_logs.data)
            total_pro = sum(log['protein'] for log in daily_logs.data)
            total_carb = sum(log['carbs'] for log in daily_logs.data)
            total_fat = sum(log['fat'] for log in daily_logs.data)

            # 2. Fetch your baseline profile targets
            profile = supabase.table("user_profiles") \
                .select("*") \
                .eq("chat_id", chat_id) \
                .execute()

            daily_summary = ""
            
            if profile.data:
                target_pro = profile.data[0]['target_protein']
                target_cal = profile.data[0]['target_calories']
                target_fat = profile.data[0]['target_fat']
                goal = profile.data[0]['goal']

                rem_pro = target_pro - total_pro
                rem_cal = target_cal - total_cal

                # --- AI Call 2: Generate Contextual Advice ---
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
                    model="llama3-8b-8192" # Using the smaller 8B model here because it replies in ~0.2 seconds!
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

            # --- FINAL OUTPUT ---
            reply = (
                f" **Logged for {meal_type.capitalize()}!**\n"
                f" *{food_data.food_name.title()}*\n"
                f" **{food_data.calories} kcal** | {food_data.protein}g P | {food_data.carbs}g C | {food_data.fat}g F"
                f"{daily_summary}"
            )

            await send_telegram_reply(chat_id, reply)
        else: 
            reply = ("Invalid input, try again")
            await send_telegram_reply(chat_id, reply)

        return {"status": "success"}
    
    except Exception as e:
        # 3. Catch any runtime errors (like Groq/Supabase failures)
        print(f"Webhook error: {e}")
        await send_telegram_reply(chat_id, f"Webhook Error: {str(e)}")
        return {"status": "error", "message": str(e)}