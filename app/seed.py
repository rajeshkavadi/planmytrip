"""Seed the database with India-first travel intelligence.

Run standalone: ``python -m app.seed`` (creates tables + PostGIS, wipes,
reloads). Kept deliberately hand-curated — the curated data *is* the moat;
scraped listings are what the incumbents already have.
"""
from __future__ import annotations

from .database import SessionLocal, init_db
from .domain import Crowd, Intent
from .models import (
    Destination,
    IntentFit,
    Place,
    SeasonMonth,
    ShoppingItem,
    WellnessRetreat,
)

# Crowd shorthands
VL, LO, MO, HI, PK = (c.value for c in (
    Crowd.VERY_LOW, Crowd.LOW, Crowd.MODERATE, Crowd.HIGH, Crowd.PEAK))


def _months(rows):
    """rows: 12 tuples of (weather, crowd, temp, rain, festival_or_None)."""
    out = []
    for i, (w, c, t, r, fest) in enumerate(rows, start=1):
        out.append(SeasonMonth(
            month=i, weather_score=w, crowd=c, avg_temp_c=t,
            rainfall_mm=r, festival=fest, note=""))
    return out


# --------------------------------------------------------------------------- #
# Destinations. Season rows are Jan..Dec.
# --------------------------------------------------------------------------- #
DESTINATIONS = [
    dict(
        slug="rishikesh", name="Rishikesh", state="Uttarakhand", region="himalayas",
        hero_gradient="ganga", base_cost_inr=34000, lat=30.087, lon=78.267, iata="DED",
        summary="Yoga capital on the Ganga — ashrams, aarti, and white water.",
        tags=["Yoga capital", "Ganga aarti", "Silent ashrams"],
        bargaining_norm="Ashram stores and cafés are fixed-price. Rafting/adventure "
                        "operators negotiate ~10–15% in shoulder season.",
        fits={Intent.SPIRITUAL: 97, Intent.DETOX: 92, Intent.WELLNESS: 90,
              Intent.RECHARGE: 78, Intent.ADVENTURE: 70},
        seasons=_months([
            (78, MO, 15, 40, None), (80, MO, 18, 35, None), (82, HI, 24, 30, None),
            (78, HI, 30, 25, None), (60, MO, 36, 45, None), (45, LO, 34, 180, None),
            (35, VL, 30, 320, None), (40, VL, 29, 300, None), (72, MO, 28, 120, None),
            (86, HI, 24, 30, None), (84, HI, 19, 15, None), (78, MO, 15, 20, None)]),
        shopping=[
            ("Rudraksha & prayer malas", "spiritual", False,
             "Ashram-run stores near Ram Jhula", "Ask bead count (mukhi); temple shops are authentic."),
            ("Ayurvedic herbs & oils", "wellness", False,
             "Certified Ayurvedic pharmacies", "Look for a licensed vaidya's dispensary, not roadside stalls."),
        ],
    ),
    dict(
        slug="kerala-hills", name="Munnar & Backwaters", state="Kerala", region="south",
        hero_gradient="backwater", base_cost_inr=42000, lat=10.089, lon=77.059, iata="COK",
        summary="Tea-carpeted hills flowing down to houseboat backwaters.",
        tags=["Tea hills", "Houseboats", "Ayurveda"],
        bargaining_norm="Kerala haggles gently — emporiums are fixed, markets ~15–20% off.",
        fits={Intent.RECHARGE: 96, Intent.WELLNESS: 88, Intent.FOODIE: 80,
              Intent.DETOX: 74, Intent.SPIRITUAL: 55},
        seasons=_months([
            (88, HI, 22, 20, None), (88, HI, 24, 25, None), (74, MO, 27, 45, None),
            (60, LO, 29, 120, None), (48, LO, 28, 240, None), (35, VL, 25, 650, None),
            (32, VL, 24, 700, None), (40, VL, 25, 480, None), (66, LO, 26, 240, None),
            (86, MO, 24, 190, None), (90, HI, 23, 60, None), (90, PK, 22, 25, None)]),
        shopping=[
            ("Munnar tea & cardamom", "spice", True,
             "Estate spice markets, not airport counters", "GI-tagged; buy at source for a third of city prices."),
            ("Aranmula Kannadi mirror", "craft", True,
             "Aranmula co-op with certificate", "Metal-alloy handmade mirror — Kerala-only; insist on authenticity cert."),
            ("Kasavu handloom", "textile", False,
             "Kannur weaver co-ops", "Off-white gold-bordered weave; co-ops over tourist shops."),
        ],
    ),
    dict(
        slug="coorg", name="Coorg", state="Karnataka", region="south",
        hero_gradient="ghats", base_cost_inr=28000, lat=12.421, lon=75.739, iata="IXE",
        summary="Coffee estates, waterfalls and a deliberately slow pace.",
        tags=["Coffee estates", "Waterfalls", "Slow"],
        bargaining_norm="Estate stores fixed-price; spice markets ~15% off.",
        fits={Intent.RECHARGE: 91, Intent.DETOX: 80, Intent.FOODIE: 78,
              Intent.WELLNESS: 76, Intent.ADVENTURE: 60},
        seasons=_months([
            (86, MO, 20, 10, None), (86, MO, 22, 15, None), (74, LO, 26, 30, None),
            (66, LO, 28, 90, None), (55, LO, 27, 160, None), (42, VL, 24, 520, None),
            (35, VL, 23, 720, None), (44, VL, 23, 560, None), (66, LO, 24, 220, None),
            (84, MO, 23, 140, None), (88, HI, 21, 40, None), (88, HI, 19, 15, None)]),
        shopping=[
            ("Coorg coffee & honey", "food", False,
             "Estate stores & plantation stays", "Buy roasted-to-order beans from the estate you tour."),
            ("Kodava spices & wine", "food", False,
             "Local markets in Madikeri", "Homemade wine is a Kodava specialty; sample before buying."),
        ],
    ),
    dict(
        slug="ladakh", name="Ladakh", state="Ladakh", region="himalayas",
        hero_gradient="mountain", base_cost_inr=58000, lat=34.152, lon=77.577, iata="IXL",
        summary="High-desert passes, cobalt lakes and Buddhist monasteries.",
        tags=["High passes", "Monasteries", "Stark beauty"],
        bargaining_norm="Leh market fixed-ish; pashmina and curios negotiate ~20–30%.",
        fits={Intent.ADVENTURE: 98, Intent.DETOX: 88, Intent.SPIRITUAL: 72,
              Intent.RECHARGE: 60, Intent.WELLNESS: 45},
        seasons=_months([
            (10, VL, -8, 10, None), (12, VL, -6, 10, None), (22, VL, 2, 15, None),
            (48, LO, 10, 15, None), (74, MO, 16, 20, None), (86, HI, 21, 15, "Hemis Festival"),
            (86, PK, 22, 25, None), (86, PK, 21, 20, None), (78, HI, 17, 15, None),
            (55, LO, 8, 10, None), (25, VL, 0, 5, None), (12, VL, -6, 10, None)]),
        shopping=[
            ("Pashmina (Changthangi)", "textile", True,
             "Leh government craft emporium", "Real pashmina is feather-light; certificate-backed at the emporium."),
            ("Apricot & sea-buckthorn", "food", False,
             "Roadside co-ops in Nubra", "Dried apricots and juice straight from Nubra growers."),
        ],
    ),
    dict(
        slug="spiti", name="Spiti Valley", state="Himachal Pradesh", region="himalayas",
        hero_gradient="snow", base_cost_inr=46000, lat=32.246, lon=78.017, iata="KUU",
        summary="A cold desert of a thousand-year-old villages, gloriously off-grid.",
        tags=["Cold desert", "Off-grid", "Ancient villages"],
        bargaining_norm="Barely commercial — village co-ops, fixed & fair. Don't haggle hard.",
        fits={Intent.DETOX: 96, Intent.ADVENTURE: 95, Intent.SPIRITUAL: 80,
              Intent.RECHARGE: 58, Intent.WELLNESS: 40},
        seasons=_months([
            (8, VL, -12, 20, None), (8, VL, -10, 20, None), (18, VL, -4, 25, None),
            (44, VL, 4, 20, None), (76, LO, 12, 15, None), (88, MO, 17, 10, None),
            (86, MO, 18, 30, None), (84, MO, 17, 40, None), (80, LO, 12, 20, None),
            (52, VL, 4, 15, None), (22, VL, -4, 15, None), (10, VL, -10, 20, None)]),
        shopping=[
            ("Chumurthi wool & shawls", "textile", False,
             "Village weaver homes in Kaza", "Handspun local wool; buying supports the village directly."),
        ],
    ),
    dict(
        slug="jaipur", name="Jaipur", state="Rajasthan", region="north",
        hero_gradient="desert", base_cost_inr=30000, lat=26.912, lon=75.787, iata="JAI",
        summary="Pink City of forts, bazaars and India's densest craft shopping.",
        tags=["Bazaars", "Forts", "Block prints"],
        bargaining_norm="North India haggles hard — bazaars quote 2–3x; settle ~40–50% off. "
                        "Government emporiums are fixed-price.",
        fits={Intent.SHOPPING: 96, Intent.FOODIE: 82, Intent.ADVENTURE: 55,
              Intent.SPIRITUAL: 50, Intent.RECHARGE: 48},
        seasons=_months([
            (84, HI, 15, 8, None), (84, HI, 20, 5, None), (72, MO, 27, 5, None),
            (55, LO, 33, 5, None), (40, LO, 39, 10, None), (35, LO, 39, 60, None),
            (42, MO, 34, 200, None), (46, MO, 32, 220, None), (60, MO, 32, 90, None),
            (78, HI, 28, 20, "Diwali"), (86, HI, 22, 5, None), (86, PK, 17, 5, None)]),
        shopping=[
            ("Sanganeri & Bagru block prints", "textile", True,
             "Sanganer/Bagru workshops near Jaipur", "GI-tagged hand-block prints; visit a workshop to see the carving."),
            ("Blue pottery", "craft", True,
             "Kripal Kumbh & artisan studios", "GI-tagged Jaipur craft; fragile — buy from a studio that ships."),
            ("Kundan & Meenakari jewellery", "jewellery", False,
             "Johari Bazaar", "Get a hallmark bill; verify gold purity for anything pricey."),
        ],
    ),
    dict(
        slug="varanasi", name="Varanasi", state="Uttar Pradesh", region="north",
        hero_gradient="ganga", base_cost_inr=26000, lat=25.317, lon=83.010, iata="VNS",
        summary="The eternal city — ghats, aarti, and Banarasi silk.",
        tags=["Ghats", "Ganga aarti", "Banarasi silk"],
        bargaining_norm="Silk shops quote high; genuine Banarasi is dear — cheap 'silk' is polyester.",
        fits={Intent.SPIRITUAL: 99, Intent.FOODIE: 74, Intent.SHOPPING: 70,
              Intent.DETOX: 45, Intent.RECHARGE: 45},
        seasons=_months([
            (82, HI, 16, 20, None), (82, HI, 21, 15, None), (70, MO, 28, 15, None),
            (52, LO, 34, 10, None), (38, LO, 40, 20, None), (34, LO, 38, 100, None),
            (40, MO, 33, 300, None), (44, MO, 32, 280, None), (58, MO, 31, 190, None),
            (76, HI, 28, 40, "Dev Deepawali"), (84, HI, 22, 10, None), (84, HI, 17, 8, None)]),
        shopping=[
            ("Banarasi silk saree", "textile", True,
             "Weaver co-ops in Madanpura/Sarai Mohana", "GI-tagged; real ones have a silk-mark. Buy from the weaver, not the tout."),
        ],
    ),
    dict(
        slug="goa-south", name="Goa (South)", state="Goa", region="west",
        hero_gradient="coast", base_cost_inr=36000, lat=15.011, lon=74.021, iata="GOI",
        summary="The quiet half of Goa — palm beaches, cafés and susegad.",
        tags=["Quiet beaches", "Cafés", "Susegad"],
        bargaining_norm="Beach-shack and flea-market goods negotiate ~30–40%.",
        fits={Intent.RECHARGE: 88, Intent.FOODIE: 90, Intent.SHOPPING: 64,
              Intent.DETOX: 62, Intent.ADVENTURE: 55},
        seasons=_months([
            (88, HI, 27, 5, None), (88, HI, 28, 5, None), (78, MO, 30, 10, None),
            (62, LO, 32, 20, None), (48, LO, 33, 90, None), (35, VL, 29, 580, None),
            (32, VL, 28, 720, None), (40, VL, 28, 500, None), (58, LO, 29, 260, None),
            (74, MO, 30, 120, None), (86, HI, 30, 30, None), (86, PK, 28, 10, "Sunburn / NYE")]),
        shopping=[
            ("Feni & cashews", "food", False,
             "Local distilleries & Mapusa market", "Buy cashews by grade; feni from a licensed distillery."),
            ("Anjuna flea-market crafts", "craft", False,
             "Wednesday Anjuna flea market", "Great for textiles/jewellery — expect to negotiate hard."),
        ],
    ),
    dict(
        slug="udaipur", name="Udaipur", state="Rajasthan", region="north",
        hero_gradient="desert", base_cost_inr=32000, lat=24.585, lon=73.712, iata="UDR",
        summary="The City of Lakes — palaces, miniature art and old-town bazaars.",
        tags=["Lake palaces", "Miniature art", "Bazaars"],
        bargaining_norm="North India haggles hard — bazaars quote 2–3x; settle ~40–50% off.",
        fits={Intent.SHOPPING: 88, Intent.RECHARGE: 78, Intent.FOODIE: 80,
              Intent.SPIRITUAL: 60, Intent.WELLNESS: 55},
        seasons=_months([
            (82, HI, 17, 5, None), (82, HI, 21, 4, None), (74, MO, 28, 5, None),
            (56, LO, 34, 4, None), (40, LO, 40, 10, None), (38, LO, 38, 60, None),
            (48, MO, 33, 180, None), (52, MO, 31, 170, None), (64, MO, 31, 90, None),
            (80, HI, 29, 20, None), (86, HI, 23, 6, None), (86, PK, 18, 4, None)]),
        shopping=[
            ("Udaipur miniature painting", "art", True,
             "Artist studios near Jagdish Temple", "GI-tagged Mewar style; buy from a working studio."),
            ("Bandhani tie-dye", "textile", False,
             "Bada Bazaar", "Real bandhani has tiny hand-tied knots you can feel."),
        ],
    ),
    dict(
        slug="andaman", name="Andaman Islands", state="A & N Islands", region="islands",
        hero_gradient="coast", base_cost_inr=62000, lat=11.667, lon=92.735, iata="IXZ",
        summary="Coral reefs, quiet white-sand beaches and world-class diving.",
        tags=["Reefs", "Diving", "Quiet beaches"],
        bargaining_norm="Mostly fixed-price; dive operators may discount multi-day packages.",
        fits={Intent.RECHARGE: 93, Intent.ADVENTURE: 84, Intent.WELLNESS: 68,
              Intent.FOODIE: 64, Intent.DETOX: 66},
        seasons=_months([
            (86, MO, 26, 30, None), (88, HI, 27, 20, None), (88, HI, 28, 15, None),
            (80, MO, 29, 40, None), (60, LO, 29, 220, None), (42, VL, 28, 420, None),
            (40, VL, 28, 430, None), (44, VL, 28, 380, None), (58, LO, 28, 300, None),
            (74, MO, 28, 190, None), (84, HI, 27, 120, None), (86, HI, 26, 50, None)]),
        shopping=[
            ("Shell & pearl craft", "craft", False,
             "Aberdeen Bazaar, Port Blair", "Buy from licensed sellers; avoid protected coral/shell species."),
        ],
    ),
    dict(
        slug="darjeeling", name="Darjeeling", state="West Bengal", region="himalayas",
        hero_gradient="ghats", base_cost_inr=30000, lat=27.036, lon=88.263, iata="IXB",
        summary="Tea slopes under Kanchenjunga, toy trains and misty ridgelines.",
        tags=["Tea gardens", "Toy train", "Kanchenjunga"],
        bargaining_norm="Chowrasta shops mostly fixed; Tibetan markets negotiate ~15–20%.",
        fits={Intent.RECHARGE: 88, Intent.DETOX: 82, Intent.FOODIE: 74,
              Intent.WELLNESS: 70, Intent.SPIRITUAL: 55},
        seasons=_months([
            (70, MO, 8, 20, None), (72, MO, 9, 25, None), (80, HI, 13, 40, None),
            (82, HI, 16, 90, None), (76, MO, 17, 180, None), (50, LO, 18, 350, None),
            (40, VL, 18, 600, None), (44, VL, 18, 560, None), (64, LO, 17, 300, None),
            (82, HI, 14, 90, None), (84, HI, 10, 20, None), (76, MO, 7, 15, None)]),
        shopping=[
            ("Darjeeling tea (first flush)", "tea", True,
             "Estate outlets & Nathmull's", "GI-tagged; buy sealed estate tins, note the flush and garden."),
            ("Himalayan woolens", "textile", False,
             "Tibetan self-help centre", "Handloom shawls; the co-op supports refugee artisans."),
        ],
    ),
    dict(
        slug="pondicherry", name="Pondicherry", state="Puducherry", region="south",
        hero_gradient="coast", base_cost_inr=28000, lat=11.934, lon=79.830, iata="PNY",
        summary="French-quarter cafés, Auroville calm and a slow seafront.",
        tags=["French quarter", "Auroville", "Seafront"],
        bargaining_norm="Boutiques fixed-price; Auroville outlets are non-negotiable and support units.",
        fits={Intent.FOODIE: 86, Intent.RECHARGE: 84, Intent.SPIRITUAL: 78,
              Intent.WELLNESS: 72, Intent.SHOPPING: 66},
        seasons=_months([
            (84, HI, 26, 20, None), (84, HI, 28, 10, None), (78, MO, 30, 15, None),
            (64, MO, 32, 40, None), (50, LO, 34, 60, None), (46, LO, 33, 70, None),
            (48, LO, 32, 90, None), (52, LO, 32, 120, None), (58, MO, 31, 140, None),
            (70, MO, 29, 260, None), (74, HI, 27, 340, None), (80, HI, 26, 180, None)]),
        shopping=[
            ("Auroville handmade goods", "craft", False,
             "Auroville boutiques", "Handmade paper, incense, pottery; proceeds fund the community units."),
        ],
    ),
    dict(
        slug="hampi", name="Hampi", state="Karnataka", region="south",
        hero_gradient="desert", base_cost_inr=24000, lat=15.335, lon=76.462, iata="HBX",
        summary="A boulder-strewn ruined capital — temples, sunsets and stillness.",
        tags=["Ruins", "Boulders", "Temples"],
        bargaining_norm="Small stalls negotiate ~20%; never buy anything resembling a protected artifact.",
        fits={Intent.SPIRITUAL: 86, Intent.ADVENTURE: 84, Intent.DETOX: 82,
              Intent.RECHARGE: 60, Intent.FOODIE: 55},
        seasons=_months([
            (82, MO, 22, 3, None), (80, MO, 25, 2, None), (68, LO, 30, 3, None),
            (52, LO, 35, 10, None), (40, VL, 38, 20, None), (42, VL, 33, 80, None),
            (48, LO, 30, 90, None), (52, LO, 30, 100, None), (62, MO, 29, 120, None),
            (78, MO, 27, 90, None), (84, HI, 24, 30, None), (84, HI, 22, 5, None)]),
        shopping=[
            ("Ilkal & Lambani craft", "textile", False,
             "Hampi bazaar & nearby villages", "Handloom sarees and mirror-work; buy from artisans directly."),
        ],
    ),
    dict(
        slug="meghalaya", name="Shillong & Meghalaya", state="Meghalaya", region="northeast",
        hero_gradient="hills", base_cost_inr=38000, lat=25.578, lon=91.893, iata="SHL",
        summary="Living-root bridges, waterfalls and the cleanest air in India.",
        tags=["Root bridges", "Waterfalls", "Living hills"],
        bargaining_norm="Police Bazaar shops fixed-ish; village craft is fair-priced — don't push hard.",
        fits={Intent.ADVENTURE: 88, Intent.DETOX: 86, Intent.RECHARGE: 82,
              Intent.FOODIE: 60, Intent.WELLNESS: 55},
        seasons=_months([
            (66, MO, 9, 15, None), (70, MO, 11, 30, None), (78, HI, 16, 90, None),
            (80, HI, 18, 220, None), (70, MO, 19, 480, None), (45, LO, 20, 1000, None),
            (38, VL, 20, 1400, None), (42, VL, 20, 1100, None), (62, LO, 19, 500, None),
            (80, HI, 16, 180, None), (82, HI, 12, 40, None), (72, MO, 9, 15, None)]),
        shopping=[
            ("Khasi handloom & cane", "craft", False,
             "Shillong markets & village co-ops", "Handwoven shawls and cane/bamboo work; buy at village level."),
        ],
    ),
]

# Schedulable activities for the itinerary builder.
# (name, category, lat, lon, visit_min, open_h, close_h, intensity, time_of_day,
#  weather_sensitive, priority, note)
PLACES = {
    "jaipur": [
        ("Amber Fort", "Fort", 26.9855, 75.8513, 150, 8, 17, "high", "morning", True, 92,
         "Go early to beat heat and crowds"),
        ("City Palace", "Palace museum", 26.9258, 75.8237, 120, 9, 17, "medium", "any", False, 85, ""),
        ("Hawa Mahal", "Landmark", 26.9239, 75.8267, 45, 9, 16, "low", "morning", True, 80,
         "Best light early morning"),
        ("Jantar Mantar", "Heritage observatory", 26.9247, 75.8246, 60, 9, 16, "low", "any", True, 72, ""),
        ("Nahargarh Fort", "Sunset viewpoint", 26.9371, 75.8153, 90, 10, 17, "medium", "evening", True, 78,
         "Sunset over the city"),
        ("Johari Bazaar", "Shopping", 26.9187, 75.8267, 90, 11, 20, "low", "evening", False, 82,
         "Jewellery & block prints — haggle"),
        ("Chokhi Dhani", "Cultural village", 26.7590, 75.8440, 120, 17, 23, "medium", "evening", False, 66,
         "Rajasthani dinner & folk arts"),
    ],
    "kerala-hills": [
        ("Kolukkumalai Sunrise", "Sunrise jeep", 10.1500, 77.2200, 120, 5, 9, "high", "sunrise", False, 90,
         "World's highest tea estate — clouds by 9am"),
        ("Eravikulam National Park", "Wildlife", 10.1760, 77.0530, 120, 8, 16, "medium", "morning", True, 84, ""),
        ("Tea Museum", "Museum", 10.0990, 77.0550, 60, 9, 16, "low", "any", False, 70, ""),
        ("Ayurvedic massage", "Wellness", 10.0890, 77.0590, 60, 10, 19, "low", "afternoon", False, 76,
         "Abhyanga — woven in mid-trip"),
        ("Mattupetty Dam", "Scenic", 10.1080, 77.1260, 45, 9, 17, "low", "afternoon", True, 60, ""),
        ("Munnar Spice Market", "Shopping", 10.0890, 77.0620, 45, 10, 20, "low", "evening", False, 64,
         "Cardamom & tea at source prices"),
    ],
}

RETREATS = [
    dict(name="Ananda in the Himalayas", location="Narendra Nagar, near Rishikesh",
         dest="rishikesh", tradition="Ayurveda + Yoga", program="7-night detox / Ayurveda",
         price=140000, accredited=False, physician_led=True, silent_option=False,
         credentials=["Palace estate", "Panchakarma physician on-site", "Integrative Ayurveda + Yoga"]),
    dict(name="Kairali Ayurvedic Healing Village", location="Palakkad, Kerala",
         dest="kerala-hills", tradition="Ayurveda (Panchakarma)", program="14-night Panchakarma",
         price=95000, accredited=True, physician_led=True, silent_option=False,
         credentials=["NABH-accredited", "Vaidya-led", "Classical Panchakarma"]),
    dict(name="Vana", location="Dehradun", dest=None,
         tradition="Sowa-Rigpa + TCM + Ayurveda", program="Sadhana wellness journey",
         price=120000, accredited=False, physician_led=True, silent_option=True,
         credentials=["Integrative medicine", "Sowa-Rigpa (Tibetan)", "Physician-designed programs"]),
    dict(name="Shreyas Retreat", location="Bengaluru outskirts", dest="coorg",
         tradition="Hatha Yoga", program="Silent yoga immersion",
         price=70000, accredited=False, physician_led=False, silent_option=True,
         credentials=["Silent-retreat option", "Small groups", "Farm-to-table sattvic"]),
    dict(name="Somatheeram Ayurveda Village", location="Kovalam, Kerala", dest="kerala-hills",
         tradition="Ayurveda (Panchakarma)", program="7–14 night rejuvenation",
         price=85000, accredited=True, physician_led=True, silent_option=False,
         credentials=["Green Leaf classified", "Vaidya-led", "Classical Panchakarma"]),
    dict(name="SwaSwara (CGH Earth)", location="Gokarna, Karnataka", dest=None,
         tradition="Yoga + Ayurveda", program="7-night yoga & art immersion",
         price=110000, accredited=False, physician_led=False, silent_option=True,
         credentials=["CGH Earth", "Yoga + expressive art", "Beachside"]),
    dict(name="Atmantan Wellness Centre", location="Mulshi, Maharashtra", dest=None,
         tradition="Integrative wellness", program="Structured 7-night programmes",
         price=130000, accredited=False, physician_led=True, silent_option=False,
         credentials=["Medical wellness", "Physician-led", "Fitness + spa + Ayurveda"]),
    dict(name="Naad Wellness", location="Sonipat, near Delhi", dest=None,
         tradition="Ayurveda + Naturopathy", program="Detox & Panchakarma",
         price=75000, accredited=True, physician_led=True, silent_option=False,
         credentials=["NABH-accredited", "Naturopathy", "Panchakarma"]),
    dict(name="Soukya", location="Bengaluru", dest="coorg",
         tradition="Integrative (Ayurveda + Homeopathy + Naturopathy)", program="Holistic health programmes",
         price=95000, accredited=True, physician_led=True, silent_option=False,
         credentials=["Integrative medicine", "Physician-led", "Organic farm estate"]),
    dict(name="Niraamaya Retreats", location="Kovalam, Kerala", dest="kerala-hills",
         tradition="Ayurveda + wellness", program="Spa & wellness stays",
         price=90000, accredited=False, physician_led=False, silent_option=False,
         credentials=["Luxury wellness", "Ayurveda", "Beachfront"]),
    dict(name="Carnoustie Ayurveda", location="Alappuzha, Kerala", dest="kerala-hills",
         tradition="Ayurveda (Panchakarma)", program="Panchakarma retreats",
         price=88000, accredited=True, physician_led=True, silent_option=False,
         credentials=["Green Leaf classified", "Vaidya-led", "Backwater setting"]),
]


def seed() -> None:
    init_db()
    db = SessionLocal()
    try:
        # Idempotent reset for a clean dev seed.
        db.query(WellnessRetreat).delete()
        db.query(Place).delete()
        db.query(ShoppingItem).delete()
        db.query(SeasonMonth).delete()
        db.query(IntentFit).delete()
        db.query(Destination).delete()
        db.commit()

        by_slug: dict[str, Destination] = {}
        for d in DESTINATIONS:
            dest = Destination(
                slug=d["slug"], name=d["name"], state=d["state"], region=d["region"],
                summary=d["summary"], hero_gradient=d["hero_gradient"],
                base_cost_inr=d["base_cost_inr"], tags=d["tags"],
                bargaining_norm=d["bargaining_norm"],
                latitude=d["lat"], longitude=d["lon"], iata=d.get("iata", ""),
            )
            dest.intent_fits = [IntentFit(intent=i.value, score=s) for i, s in d["fits"].items()]
            dest.seasons = d["seasons"]
            dest.shopping = [
                ShoppingItem(name=n, category=c, gi_tagged=gi, where_to_buy=w, authenticity_note=a)
                for (n, c, gi, w, a) in d["shopping"]
            ]
            dest.places = [
                Place(name=nm, category=cat, latitude=la, longitude=lo, visit_minutes=vm,
                      open_hour=oh, close_hour=ch, intensity=inten, time_of_day=tod,
                      weather_sensitive=ws, priority=pr, note=nt)
                for (nm, cat, la, lo, vm, oh, ch, inten, tod, ws, pr, nt)
                in PLACES.get(d["slug"], [])
            ]
            db.add(dest)
            by_slug[d["slug"]] = dest
        db.flush()

        for r in RETREATS:
            db.add(WellnessRetreat(
                name=r["name"], location=r["location"], tradition=r["tradition"],
                program=r["program"], price_inr_week=r["price"], accredited=r["accredited"],
                physician_led=r["physician_led"], silent_option=r["silent_option"],
                credentials=r["credentials"],
                destination_id=by_slug[r["dest"]].id if r["dest"] else None,
            ))
        db.commit()
        print(f"Seeded {len(DESTINATIONS)} destinations and {len(RETREATS)} retreats.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
