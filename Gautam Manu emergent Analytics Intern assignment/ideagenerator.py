import os
import time
import json
import logging
import re
from datetime import datetime, timedelta
from typing import List, Dict

import pandas as pd
import google.generativeai as genai  # Gemini SDK
from ratelimit import limits, sleep_and_retry  # Rate-limiting decorator
from rapidfuzz import fuzz  # Fuzzy dedupe
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
datetime_format = '%Y-%m-%d %H:%M:%S'
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt=datetime_format
)


class RateLimiter:
    """Tracks per-minute and per-day quotas."""
    DAY_LIMIT = 1499
    MINUTE_LIMIT = 15

    def __init__(self):
        self.requests_today = 0
        self.requests_this_minute = 0
        self.day_start = datetime.now()
        self.minute_start = datetime.now()

    def reset_if_needed(self):
        now = datetime.now()
        if now.date() != self.day_start.date():
            self.requests_today = 0
            self.day_start = now
        if (now - self.minute_start) >= timedelta(minutes=1):
            self.requests_this_minute = 0
            self.minute_start = now

    def can_request(self) -> bool:
        self.reset_if_needed()
        return (
            self.requests_today < self.DAY_LIMIT and
            self.requests_this_minute < self.MINUTE_LIMIT
        )

    def record(self):
        self.requests_today += 1
        self.requests_this_minute += 1

class ProjectIdeaGenerator:
    def __init__(self,
                 output_path: str,
                 api_key: str,
                 batch_size: int = 500,
                 max_batches: int = 1000,
                 use_prefilter: bool = True):
        """
        output_path: CSV file to append results
        api_key:    Gemini API key
        batch_size: Ideas per API call
        max_batches: Number of batches to run
        use_prefilter: Filter profanity
        """
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        self.rate_limiter = RateLimiter()
        self.batch_size = batch_size
        self.max_batches = max_batches
        self.use_prefilter = use_prefilter
        self.output_path = output_path
        self.seen_ideas: List[str] = []
        self.id_counter = 0
        self._load_existing()

    def _load_existing(self):
        """Load existing CSV to initialize seen_ideas and id_counter."""
        if os.path.isfile(self.output_path):
            try:
                df = pd.read_csv(self.output_path)
                self.seen_ideas = df['idea'].astype(str).tolist() if 'idea' in df.columns else []
                self.id_counter = int(df['id'].max()) if 'id' in df.columns else 0
                logging.info(f"Loaded {len(self.seen_ideas)} existing ideas, starting ID at {self.id_counter+1}")
            except Exception as e:
                logging.error(f"Error reading existing file: {e}")

    def build_prompt(self) -> str:
        return (
            f"Generate {self.batch_size} unique, concise (1–2 line) web or mobile app project ideas "
            f"that could be built end-to-end using AI-native dev tools like v0.dev, bolt.new, cursor, emergent.sh, etc. "
            "For each idea, estimate manual dev hours (e.g., '4 hr'). "
            "Return a valid JSON array with 'idea' and 'manual_dev_hours'."
        )

    @sleep_and_retry
    @limits(calls=RateLimiter.MINUTE_LIMIT, period=60)
    def call_api(self, prompt: str) -> List[Dict]:
        if not self.rate_limiter.can_request():
            logging.info("Rate limit reached; sleeping 5s...")
            time.sleep(5)
        for attempt in range(1, 4):
            text = None
            try:
                response = self.model.generate_content(prompt)
                self.rate_limiter.record()
                text = response.text.strip()
                text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE)
                return json.loads(text)
            except json.JSONDecodeError as jde:
                logging.error(f"JSON parse error on attempt {attempt}: {jde}")
                logging.error(f"Offending JSON snippet (last 1000 chars): {text[-1000:]}")
            except Exception as e:
                logging.error(f"API error on attempt {attempt}: {e}")
            time.sleep(2 ** attempt)
        raise RuntimeError("Gemini API failed after 3 retries")

    def is_duplicate(self, idea: str, threshold: int = 90) -> bool:
        if idea in self.seen_ideas:
            return True
        return any(fuzz.partial_ratio(idea, old) >= threshold for old in self.seen_ideas)

    def post_process(self, entries: List[Dict]) -> pd.DataFrame:
        """
        Clean and format raw entries into a DataFrame,
        converting hours to float.
        """
        df = pd.DataFrame(entries)
        df['manual_dev_hours'] = (
            df['manual_dev_hours']
            .str.extract(r"(\d+\.?\d*)")[0]
            .astype(float)
        )
        df.reset_index(drop=True, inplace=True)
        return df

    def save_batch(self, df: pd.DataFrame):
        """Append cleaned batch to CSV with consistent formatting."""
        file_exists = os.path.isfile(self.output_path)
        df.to_csv(
            self.output_path,
            mode='a',
            header=not file_exists,
            index=False,
            float_format='%.2f'
        )
        logging.info(f"Saved {len(df)} ideas to {self.output_path}")

    def run(self):
        all_entries: List[Dict] = []
        try:
            for batch in range(self.max_batches):
                logging.info(f"Batch {batch+1}/{self.max_batches}")
                try:
                    raw = self.call_api(self.build_prompt())
                except Exception as api_err:
                    logging.error(f"Batch {batch+1} API failed: {api_err}")
                    break
                new_entries = []
                for obj in raw:
                    idea = obj.get('idea', '').strip()
                    # hrs = obj.get('manual_dev_hours', '').strip().
                    raw  = obj.get('manual_dev_hours', '')
                    hrs_str = str(raw).strip()
                    if idea and not self.is_duplicate(idea):
                        self.id_counter += 1
                        self.seen_ideas.append(idea)
                        new_entries.append({
                            'id': self.id_counter,
                            'idea': idea,
                            'manual_dev_hours': hrs_str
                        })
                if new_entries:
                    df = self.post_process(new_entries)
                    self.save_batch(df)
                    all_entries.extend(new_entries)
                else:
                    logging.info("No new entries in this batch.")
                time.sleep(5)
        finally:
            # Always save what we have so far
            if all_entries:
                df_final = self.post_process(all_entries)
                self.save_batch(df_final)
            logging.info(f"Completed run. Total unique ideas now: {len(self.seen_ideas)}")

if __name__ == '__main__':
    API_KEY = os.getenv('GOOGLE_API_KEY')
    if not API_KEY:
        raise ValueError("GOOGLE_API_KEY not set in environment.")
    generator = ProjectIdeaGenerator(
        output_path='project_ideas.csv',
        api_key=API_KEY,
        batch_size=100,
        max_batches=200
    )
    generator.run()