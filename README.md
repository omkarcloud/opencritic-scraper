# 🎮 Opencritic Scraper

Opencritic Scraper is a **free and open-source** scraper that gets you **unlimited** detailed OpenCritic data for free.

## ✨ What Can I Get?

- 🎮 **Full details on 9,000+ games** — Top Critic Score, tier, percentile, platforms, developers, trailers & store links
- 📝 **Every critic review in one call** — score, outlet, critic, snippet & link, plus a score histogram
- 🧑‍💻 **7,300+ critics & 800+ outlets** — profiles, socials, review stats and every review they wrote
- 🔥 **Charts, deals & 36,000+ news articles** — popular, upcoming, Hall of Fame, release calendar & Game Pass

## 🎥 Example: A Full OpenCritic Game

```json
{
  "id": 12090,
  "name": "Elden Ring",
  "link": "https://opencritic.com/game/12090/elden-ring",
  "release_date": "2022-02-25",
  "tier": "Mighty",
  "top_critic_score": 95.1,
  "median_score": 96.5,
  "percentile": 100,
  "percent_recommended": 97.13,
  "review_count": 219,
  "top_critic_review_count": 139,
  "developers": ["FromSoftware Inc."],
  "publishers": ["BANDAI NAMCO Entertainment"],
  "platforms": [
    { "id": 27, "name": "PC", "short_name": "PC", "release_date": "2022-02-25" },
    { "id": 3, "name": "PlayStation 5", "short_name": "PS5", "release_date": "2022-02-25" }
  ],
  "genres": [{ "id": 27, "name": "Action" }, { "id": 77, "name": "RPG" }],
  "review_summary": {
    "summary": "Elden Ring is FromSoftware's best work yet and one of the highest rated games of all time. With refined, accessible, and satisfying combat in a vast, beautiful, and intriguing open world, players will find a lot to love."
  },
  "trailers": [
    { "title": "Elden Ring - Announcement Trailer", "link": "https://www.youtube.com/watch?v=MXl-7Fd-D9Y", "type": "Announcement Trailer" }
  ],
  "images": {
    "box": { "original": "https://img.opencritic.com/game/12090/o/5BXKr5S1.jpg" }
  },
  "dates": { "first_review": "2021-01-28", "critical_mass_review": "2022-02-23", "latest_review": "2025-10-06" }
}
```

*Trimmed for readability.*

## 🚀 Unlimited Free Opencritic Data — Get It in 60 Seconds

1️⃣ Clone and install:
```bash
git clone https://github.com/omkarcloud/opencritic-scraper
cd opencritic-scraper
python -m pip install -r requirements.txt
```

2️⃣ Start the API:
```bash
python run.py
```

3️⃣ Get your first data:
```bash
curl "http://localhost:8000/games/details?game=12090"
```

```json
{
  "id": 12090,
  "name": "Elden Ring",
  "link": "https://opencritic.com/game/12090/elden-ring",
  "release_date": "2022-02-25",
  "tier": "Mighty",
  "top_critic_score": 95.1,
  "median_score": 96.5,
  "percentile": 100,
  "percent_recommended": 97.13,
  "review_count": 219,
  "top_critic_review_count": 139,
  "developers": ["FromSoftware Inc."],
  "publishers": ["BANDAI NAMCO Entertainment"],
  "genres": [{ "id": 27, "name": "Action" }, { "id": 77, "name": "RPG" }],
  "review_summary": {
    "summary": "Elden Ring is FromSoftware's best work yet and one of the highest rated games of all time. With refined, accessible, and satisfying combat in a vast, beautiful, and intriguing open world, players will find a lot to love."
  }
}
```

All 35 endpoints are now live at `http://localhost:8000`.

## 📚 Endpoints

35 endpoints cover everything you need.

| Endpoint | Path | Returns |
|---|---|---|
| Game Details | `/games/details` | Everything about one game in a single call |
| Search | `/search` | Games, outlets and critics in one search |
| Search Games | `/games/search` | Games by name, best match first |
| Browse Games | `/games` | Filter by platform, year, tag; sort by score or date |
| Game Reviews | `/games/reviews` | Critic reviews with score, outlet and link, 20 per page |
| All Game Reviews | `/games/reviews/all` | Every critic review of a game in one call |
| Featured Game Reviews | `/games/reviews/featured` | The reviews OpenCritic highlights on the game page |
| Score Distribution | `/games/score-distribution` | Critic score histogram, mean and median |
| Game Media | `/games/media` | Every screenshot, artwork set and trailer |
| User Rating / User Reviews | `/games/user-rating`, `/games/user-reviews` | Player median score, rating count and written reviews |
| Game News | `/games/news` | News articles about a game, full text |
| Popular / Upcoming / Recently Released | `/games/popular`, `/games/upcoming`, `/games/recently-released` | What's hot, what's next, what just dropped |
| Reviewed Today / This Week | `/games/reviewed-today`, `/games/reviewed-this-week` | Games getting the most reviews right now |
| Hall of Fame | `/games/hall-of-fame` | The 12 best-reviewed games of any year since 2016 |
| Game Deals | `/games/deals` | Discounted games with store, price and discount |
| Release Calendar | `/calendar` | Every game releasing in the calendar window |
| Outlets | `/outlets`, `/outlets/details`, `/outlets/reviews` | 800+ outlets: profiles, scoring habits, every review |
| Critics | `/critics/search`, `/critics/details`, `/critics/reviews` | Critic profiles, socials, stats and every review |
| News | `/news`, `/news/details` | Latest gaming news with full article text |
| Collections | `/collections`, `/collections/details`, `/collections/games` | Xbox Game Pass catalogs with tier breakdowns |
| Reference Lists | `/platforms`, `/genres`, `/tags`, `/score-formats` | Filter values for every browse parameter |

## 🔍 Exploring Parameters

The same API is published on RapidAPI, and its playground is the easiest place to try parameters and see raw responses. Once a request looks right, run it locally for **unlimited free** data.

1. [Subscribe to the free plan](https://rapidapi.com/OmkarCloud/api/best-opencritic-scraper-free-1000-calls/pricing) — 1,000 calls/month, no credit card.
2. [Try the endpoints in the playground](https://rapidapi.com/OmkarCloud/api/best-opencritic-scraper-free-1000-calls/playground) — every param is pre-filled, so you see real data in one click.
3. Copy the generated code and replace `https://best-opencritic-scraper-free-1000-calls.p.rapidapi.com` with `http://localhost:8000`. It will now run against your local API.

```python
import requests

# generated by the playground, host swapped for the local API
response = requests.get(
    "http://localhost:8000/games/details",
    params={"game": "12090"},
)
print(response.json())
```

## 💬 Have Questions? We Have Answers.

You're a developer — we know how hard completing a project can be. So we offer full support: just message us and we'll reply ✅ with a solution within 1 working day.

[![Message Us on WhatsApp about Opencritic Scraper](https://raw.githubusercontent.com/omkarcloud/assets/master/images/whatsapp-us.png)](https://api.whatsapp.com/send?phone=918178804274&text=I%20need%20help%20using%20the%20Opencritic%20Scraper%20API.)

[![Ask Us by Email about Opencritic Scraper](https://raw.githubusercontent.com/omkarcloud/assets/master/images/ask-on-email.png)](mailto:happy.to.help@omkar.cloud?subject=Help%20with%20Opencritic%20Scraper%20API&body=I%20need%20help%20using%20the%20Opencritic%20Scraper%20API.)

## ⚡ Popular Scrapers by Omkar Cloud

- [**Google Maps Scraper (3,100+ GitHub Stars)**](https://github.com/omkarcloud/google-maps-scraper) — type "dentists in New York", get every business as a ready-to-call lead list: phones, emails, websites & reviews. Up to 100K free leads/month.
- [**IMDb Scraper**](https://github.com/omkarcloud/imdb-scraper) — movies & TV: ratings, cast, box office & all 6 IMDb charts
- [**G2 Scraper**](https://www.omkar.cloud/tools/g2-scraper) — G2 product details, ratings & AI-found contacts
- [**Website Email Contact Scraper**](https://www.omkar.cloud/tools/website-email-contact-scraper) — emails, phones & socials from any website
- [**AliExpress Scraper**](https://www.omkar.cloud/tools/aliexpress-scraper) — live product details, SKU variants, stock & shipping
- [**Booking Scraper**](https://www.omkar.cloud/tools/booking-scraper) — Booking.com hotels: prices, ratings, rooms & amenities

## ⭐ Love It? [Star It ⭐!](https://github.com/omkarcloud/opencritic-scraper)

Star the repo ⭐ and become a star hero!

It's just 1 click, but it means the world to me.

[![Star us on GitHub](https://raw.githubusercontent.com/omkarcloud/google-maps-scraper/master/screenshots/star-us.png)](https://github.com/omkarcloud/opencritic-scraper)
