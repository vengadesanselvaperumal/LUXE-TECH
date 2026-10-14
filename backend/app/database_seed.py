import json
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.database import (
    Collection, Forecast, ImageRecord, Product, Prophecy,
    RetailSignal, Trend, TrendDNA, TrendSignal, User, init_db
)

CATEGORIES_16 = [
    "Color", "Materials", "Silhouettes", "Patterns",
    "Prints", "Textures", "Product", "Accessories",
    "Womenswear", "Menswear", "Streetwear", "Couture",
    "Retail", "Consumer", "Market", "Future Signals"
]

SAMPLE_TRENDS = [
    {
        "slug": "digital-nature",
        "name": "Digital Nature",
        "category": "Color",
        "season": "SS 2027",
        "status": "emerging",
        "confidence": 84.0,
        "momentum": 31.5,
        "velocity": 18.2,
        "acceleration": 6.4,
        "description": "Organic tactility meets synthetic luminescence: a visual language shaped by biophilic algorithms and hyper-natural dyes.",
        "image_url": "https://images.unsplash.com/photo-1579783900882-c0d3dad7b119?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#0D1F22", "rgb": [13, 31, 34], "percentage": 42.0},
            {"hex": "#ADC7B8", "rgb": [173, 199, 184], "percentage": 28.5},
            {"hex": "#FF2A85", "rgb": [255, 42, 133], "percentage": 14.2},
            {"hex": "#E5C9A1", "rgb": [229, 201, 161], "percentage": 10.3},
            {"hex": "#F9F7F1", "rgb": [249, 247, 241], "percentage": 5.0}
        ],
        "materials": ["Technical organza", "Bioluminescent silk", "Recycled ocean polymer", "Cellulose crepe"],
        "textures": ["Iridescent micro-rib", "Crushed membrane", "Porous gossamer"],
        "silhouettes": ["Cocoon drape", "Fluid volume", "Articulated raglan"],
        "patterns": ["Generative cellular repeat", "Algorithmic gradient", "Diffused lichen bloom"],
        "signals": {"runway": 82.0, "social": 76.0, "search": 71.0, "retail": 64.0, "culture": 68.0}
    },
    {
        "slug": "fluid-tailoring",
        "name": "Fluid Tailoring",
        "category": "Silhouettes",
        "season": "SS 2027",
        "status": "accelerating",
        "confidence": 88.0,
        "momentum": 28.0,
        "velocity": 21.0,
        "acceleration": 7.5,
        "description": "Unstructured shoulders and softened canvassing replace corporate rigidity, bridging active comfort with sartorial authority.",
        "image_url": "https://images.unsplash.com/photo-1509631179647-0177331693ae?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#1E252B", "rgb": [30, 37, 43], "percentage": 46.0},
            {"hex": "#8C969E", "rgb": [140, 150, 158], "percentage": 30.0},
            {"hex": "#E3DAC9", "rgb": [227, 218, 201], "percentage": 16.0},
            {"hex": "#DF7E8C", "rgb": [223, 126, 140], "percentage": 8.0}
        ],
        "materials": ["Double-faced wool twill", "High-twist tropical wool", "Cupro lining", "Silk-cotton gabardine"],
        "textures": ["Dry matte finish", "Supple liquid drape", "Airy porous weave"],
        "silhouettes": ["Dropped shoulder unlined jacket", "Extended wide trouser", "Kimono sleeve overcoat"],
        "patterns": ["Tonal micro-houndstooth", "Subtle chalk pinstripe"],
        "signals": {"runway": 89.0, "social": 81.0, "search": 78.0, "retail": 72.0, "culture": 75.0}
    },
    {
        "slug": "electric-fuchsia",
        "name": "Electric Fuchsia",
        "category": "Color",
        "season": "SS 2027",
        "status": "emerging",
        "confidence": 81.0,
        "momentum": 34.0,
        "velocity": 24.5,
        "acceleration": 9.1,
        "description": "A high-chroma, saturated pulse signaling energetic defiance across runway spotlights and digital counter-cultures.",
        "image_url": "https://images.unsplash.com/photo-1515886657613-9f3515b0c78f?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#FF1493", "rgb": [255, 20, 147], "percentage": 52.0},
            {"hex": "#4C364D", "rgb": [76, 54, 77], "percentage": 25.0},
            {"hex": "#102126", "rgb": [16, 33, 38], "percentage": 15.0},
            {"hex": "#F9F7F1", "rgb": [249, 247, 241], "percentage": 8.0}
        ],
        "materials": ["Satin duchesse", "Coated technical ripstop", "Glazed calfskin"],
        "textures": ["Mirror gloss", "Crisp paper-touch", "Micro-sheen"],
        "silhouettes": ["Sharp sculptural lapels", "Body-contouring columns", "Volumetric capelets"],
        "patterns": ["Solid chromatic block", "Cybernetic optical glitch"],
        "signals": {"runway": 85.0, "social": 89.0, "search": 74.0, "retail": 52.0, "culture": 80.0}
    },
    {
        "slug": "technical-organza",
        "name": "Technical Organza",
        "category": "Materials",
        "season": "SS 2027",
        "status": "growing",
        "confidence": 76.0,
        "momentum": 22.0,
        "velocity": 14.0,
        "acceleration": 4.2,
        "description": "Engineering transparency into structural air: high-tenacity monofilaments sculpted into ethereal protective outerwear.",
        "image_url": "https://images.unsplash.com/photo-1558769132-cb1aea458c5e?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#E0E8E3", "rgb": [224, 232, 227], "percentage": 45.0},
            {"hex": "#A8BDB2", "rgb": [168, 189, 178], "percentage": 30.0},
            {"hex": "#173D3B", "rgb": [23, 61, 59], "percentage": 18.0},
            {"hex": "#E5C9A1", "rgb": [229, 201, 161], "percentage": 7.0}
        ],
        "materials": ["Bonded nylon organza", "Polyester monofilament", "Water-repellent mesh"],
        "textures": ["Glassine stiffness", "Ultra-light tactile crinkle"],
        "silhouettes": ["Layered storm anorak", "Translucent shell parka", "Tiered gossamer tunic"],
        "patterns": ["Engineered grid ripstop", "Ghosted shadow seams"],
        "signals": {"runway": 78.0, "social": 73.0, "search": 66.0, "retail": 59.0, "culture": 64.0}
    },
    {
        "slug": "kinetic-pleating",
        "name": "Kinetic Pleating",
        "category": "Textures",
        "season": "SS 2027",
        "status": "emerging",
        "confidence": 79.0,
        "momentum": 19.5,
        "velocity": 12.0,
        "acceleration": 3.8,
        "description": "Three-dimensional origami geometry in motion, responding dynamically to body velocity and posture shifts.",
        "image_url": "https://images.unsplash.com/photo-1490481651871-ab68de25d43d?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#D6BD95", "rgb": [214, 189, 149], "percentage": 40.0},
            {"hex": "#2B3A42", "rgb": [43, 58, 66], "percentage": 35.0},
            {"hex": "#DF7E8C", "rgb": [223, 126, 140], "percentage": 25.0}
        ],
        "materials": ["Permanent heat-set polyester", "Pleated silk chiffon", "Elasticated micro-crepe"],
        "textures": ["Accordion concertina", "Dynamic spring rebound"],
        "silhouettes": ["Fluted column skirt", "Radial cape blouse", "Accordion sleeve trench"],
        "patterns": ["Parametric chevron pleat", "Radial sunburst"],
        "signals": {"runway": 81.0, "social": 69.0, "search": 65.0, "retail": 58.0, "culture": 70.0}
    },
    {
        "slug": "generative-botanicals",
        "name": "Generative Botanicals",
        "category": "Prints",
        "season": "SS 2027",
        "status": "accelerating",
        "confidence": 83.0,
        "momentum": 26.0,
        "velocity": 17.5,
        "acceleration": 5.2,
        "description": "Floral motifs rewritten by recursive neural growth algorithms, resulting in alien flora and synthetic botanical repeats.",
        "image_url": "https://images.unsplash.com/photo-1483985988355-763728e1935b?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#4C364D", "rgb": [76, 54, 77], "percentage": 38.0},
            {"hex": "#ADC7B8", "rgb": [173, 199, 184], "percentage": 32.0},
            {"hex": "#FF5252", "rgb": [255, 82, 82], "percentage": 20.0},
            {"hex": "#F6F4EE", "rgb": [246, 244, 238], "percentage": 10.0}
        ],
        "materials": ["Silk crepe de chine", "Digital printed viscose twill"],
        "textures": ["Ultra-smooth planar silk", "Subtle satin reflection"],
        "silhouettes": ["Bias-cut maxi slip", "Kimono dressing robe", "Band-collar fluid shirt"],
        "patterns": ["Bioluminescent alien orchids", "Pixelated stem networks"],
        "signals": {"runway": 84.0, "social": 86.0, "search": 75.0, "retail": 68.0, "culture": 72.0}
    },
    {
        "slug": "modular-monolith",
        "name": "Modular Monolith",
        "category": "Streetwear",
        "season": "SS 2027",
        "status": "mainstream",
        "confidence": 86.0,
        "momentum": 24.0,
        "velocity": 11.0,
        "acceleration": 1.5,
        "description": "Monochromatic architectural utility garments designed with magnetic fidlock attachments and detachable modular pouches.",
        "image_url": "https://images.unsplash.com/photo-1529139574466-a303027c1d8b?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#102126", "rgb": [16, 33, 38], "percentage": 65.0},
            {"hex": "#4A5859", "rgb": [74, 88, 89], "percentage": 25.0},
            {"hex": "#DF7E8C", "rgb": [223, 126, 140], "percentage": 10.0}
        ],
        "materials": ["Cordura 500D", "Dyneema composite fabric", "Ripstop nylon"],
        "textures": ["Abrasion-resistant ballistic matte", "Tactile webbing"],
        "silhouettes": ["Boxy cropped utility vest", "Multi-pocket cargo pant", "Modular flight jacket"],
        "patterns": ["Tone-on-tone tactical tessellation"],
        "signals": {"runway": 76.0, "social": 88.0, "search": 85.0, "retail": 81.0, "culture": 82.0}
    },
    {
        "slug": "neo-couture-armour",
        "name": "Neo-Couture Armour",
        "category": "Couture",
        "season": "SS 2027",
        "status": "emerging",
        "confidence": 82.0,
        "momentum": 33.0,
        "velocity": 22.0,
        "acceleration": 8.0,
        "description": "3D printed biomimetic exoskeletons hand-embellished with heritage crystal embroidery and titanium leafing.",
        "image_url": "https://images.unsplash.com/photo-1539109136881-3be0616acf4b?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#E5C9A1", "rgb": [229, 201, 161], "percentage": 42.0},
            {"hex": "#173D3B", "rgb": [23, 61, 59], "percentage": 38.0},
            {"hex": "#DF7E8C", "rgb": [223, 126, 140], "percentage": 20.0}
        ],
        "materials": ["SLS printed nylon polymer", "Liquid silk satin", "Precious metal electroplating"],
        "textures": ["Specular bone-finish", "Molten metal polish"],
        "silhouettes": ["Articulated corset bustier", "Segmented shoulder pauldrons"],
        "patterns": ["Biomimetic dragonfly wing lattice"],
        "signals": {"runway": 92.0, "social": 78.0, "search": 63.0, "retail": 42.0, "culture": 77.0}
    },
    {
        "slug": "tactile-parchment",
        "name": "Tactile Parchment",
        "category": "Textures",
        "season": "SS 2027",
        "status": "growing",
        "confidence": 77.0,
        "momentum": 21.0,
        "velocity": 13.0,
        "acceleration": 3.9,
        "description": "Crisp paper-like cellulose fabrics treated with beeswax washes to create delicate folds that remember the wearer's movement.",
        "image_url": "https://images.unsplash.com/photo-1445205170230-053b83016050?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#F2EBD9", "rgb": [242, 235, 217], "percentage": 50.0},
            {"hex": "#C4A482", "rgb": [196, 164, 130], "percentage": 30.0},
            {"hex": "#102126", "rgb": [16, 33, 38], "percentage": 20.0}
        ],
        "materials": ["Japanese washi paper yarn", "Waxed organic cotton", "Raw flax linen"],
        "textures": ["Crisp tactile crinkle", "Dry paper handfeel"],
        "silhouettes": ["Boxy apron dress", "Kimono wrap coat"],
        "patterns": ["Organic fold striations"],
        "signals": {"runway": 75.0, "social": 70.0, "search": 67.0, "retail": 55.0, "culture": 66.0}
    },
    {
        "slug": "luminous-minerals",
        "name": "Luminous Minerals",
        "category": "Color",
        "season": "SS 2027",
        "status": "accelerating",
        "confidence": 85.0,
        "momentum": 29.0,
        "velocity": 19.0,
        "acceleration": 6.8,
        "description": "Deep obsidian and malachite tones shot through with veins of electro-luminescent copper and pale celadon.",
        "image_url": "https://images.unsplash.com/photo-1469334031218-e382a71b716b?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#173D3B", "rgb": [23, 61, 59], "percentage": 45.0},
            {"hex": "#E5C9A1", "rgb": [229, 201, 161], "percentage": 25.0},
            {"hex": "#102126", "rgb": [16, 33, 38], "percentage": 20.0},
            {"hex": "#DF7E8C", "rgb": [223, 126, 140], "percentage": 10.0}
        ],
        "materials": ["Silk velvet", "Reflective laminated poplin"],
        "textures": ["Deep plush pile", "Reflective sheen"],
        "silhouettes": ["Draped cowl neck gown", "Architectural tailored trench"],
        "patterns": ["Agate geode cross-section"],
        "signals": {"runway": 87.0, "social": 82.0, "search": 73.0, "retail": 65.0, "culture": 71.0}
    },
    {
        "slug": "engineered-translucency",
        "name": "Engineered Translucency",
        "category": "Materials",
        "season": "SS 2027",
        "status": "emerging",
        "confidence": 80.0,
        "momentum": 27.0,
        "velocity": 16.5,
        "acceleration": 5.8,
        "description": "Multi-layered frosted textiles revealing internal tailoring canvas and bonded seams beneath translucent veils.",
        "image_url": "https://images.unsplash.com/photo-1492707892479-7bc8d5a4ee93?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#ADC7B8", "rgb": [173, 199, 184], "percentage": 48.0},
            {"hex": "#F9F7F1", "rgb": [249, 247, 241], "percentage": 32.0},
            {"hex": "#4C364D", "rgb": [76, 54, 77], "percentage": 20.0}
        ],
        "materials": ["Polyurethane frosted film", "Silicone-coated organza"],
        "textures": ["Frosted matte translucency"],
        "silhouettes": ["Layered shell parka", "Transparent trench"],
        "patterns": ["Internal skeletal seam tape"],
        "signals": {"runway": 83.0, "social": 75.0, "search": 68.0, "retail": 56.0, "culture": 67.0}
    },
    {
        "slug": "sculpted-monochrome",
        "name": "Sculpted Monochrome",
        "category": "Menswear",
        "season": "SS 2027",
        "status": "growing",
        "confidence": 82.0,
        "momentum": 23.0,
        "velocity": 15.0,
        "acceleration": 4.5,
        "description": "Architectural tailoring for the modern man, characterized by clean unbroken vertical lines and tone-on-tone layering.",
        "image_url": "https://images.unsplash.com/photo-1507679799987-c73779587ccf?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#102126", "rgb": [16, 33, 38], "percentage": 60.0},
            {"hex": "#84958E", "rgb": [132, 149, 142], "percentage": 25.0},
            {"hex": "#F9F7F1", "rgb": [249, 247, 241], "percentage": 15.0}
        ],
        "materials": ["Worsted wool", "Bonded scuba jersey"],
        "textures": ["Crisp worsted", "Ultra-smooth planar"],
        "silhouettes": ["Collarless single-breasted coat", "Wide tapered trouser"],
        "patterns": ["Pure solid"],
        "signals": {"runway": 85.0, "social": 77.0, "search": 72.0, "retail": 69.0, "culture": 70.0}
    },
    {
        "slug": "hyper-craft-accessories",
        "name": "Hyper-Craft Accessories",
        "category": "Accessories",
        "season": "SS 2027",
        "status": "emerging",
        "confidence": 79.0,
        "momentum": 25.0,
        "velocity": 17.0,
        "acceleration": 5.0,
        "description": "Ergonomic leather bags cast in bio-resin shells with machined anodized aluminum hardware.",
        "image_url": "https://images.unsplash.com/photo-1548036328-c9fa89d128fa?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#E5C9A1", "rgb": [229, 201, 161], "percentage": 50.0},
            {"hex": "#102126", "rgb": [16, 33, 38], "percentage": 30.0},
            {"hex": "#DF7E8C", "rgb": [223, 126, 140], "percentage": 20.0}
        ],
        "materials": ["Vegetable tanned leather", "Anodized aerospace aluminum"],
        "textures": ["Supple pebble grain", "Brushed industrial metal"],
        "silhouettes": ["Crescent hobo", "Sculpted clutch"],
        "patterns": ["Precision micro-engraving"],
        "signals": {"runway": 80.0, "social": 74.0, "search": 69.0, "retail": 61.0, "culture": 65.0}
    },
    {
        "slug": "pragmatic-avant-garde",
        "name": "Pragmatic Avant-Garde",
        "category": "Womenswear",
        "season": "SS 2027",
        "status": "accelerating",
        "confidence": 87.0,
        "momentum": 30.0,
        "velocity": 20.0,
        "acceleration": 7.0,
        "description": "Directional silhouette experimentation adapted into washable, wrinkle-resistant technical luxury textiles.",
        "image_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#ADC7B8", "rgb": [173, 199, 184], "percentage": 40.0},
            {"hex": "#4C364D", "rgb": [76, 54, 77], "percentage": 35.0},
            {"hex": "#E5C9A1", "rgb": [229, 201, 161], "percentage": 25.0}
        ],
        "materials": ["Technical washable wool", "Japanese nylon taffeta"],
        "textures": ["Crisp silky memory-touch"],
        "silhouettes": ["Asymmetrical trench gown", "Cocoon sleeve tunic"],
        "patterns": ["Subtle bias seam architecture"],
        "signals": {"runway": 88.0, "social": 84.0, "search": 76.0, "retail": 68.0, "culture": 73.0}
    },
    {
        "slug": "bio-circular-knit",
        "name": "Bio-Circular Knit",
        "category": "Future Signals",
        "season": "SS 2027",
        "status": "emerging",
        "confidence": 83.0,
        "momentum": 35.0,
        "velocity": 23.0,
        "acceleration": 8.5,
        "description": "Zero-waste whole-garment 3D knitting generated directly from algae bio-polymers and regenerative wool fibers.",
        "image_url": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#173D3B", "rgb": [23, 61, 59], "percentage": 50.0},
            {"hex": "#ADC7B8", "rgb": [173, 199, 184], "percentage": 30.0},
            {"hex": "#F9F7F1", "rgb": [249, 247, 241], "percentage": 20.0}
        ],
        "materials": ["Algae bio-filament", "Regenerative Merino wool"],
        "textures": ["Seamless spongy knit", "Varying compression density"],
        "silhouettes": ["Second-skin ergonomic base layer", "Volumetric ribbed cape"],
        "patterns": ["Parametric rib density maps"],
        "signals": {"runway": 89.0, "social": 79.0, "search": 70.0, "retail": 48.0, "culture": 76.0}
    },
    {
        "slug": "tactile-sensory-luxury",
        "name": "Tactile Sensory Luxury",
        "category": "Product",
        "season": "SS 2027",
        "status": "growing",
        "confidence": 81.0,
        "momentum": 22.0,
        "velocity": 14.5,
        "acceleration": 4.1,
        "description": "Product engineering designed around touch therapy and physical sensation: cashmere-silk blends with subtle micro-relief texturing.",
        "image_url": "https://images.unsplash.com/photo-1485230895905-ec40ba36b9bc?auto=format&fit=crop&w=800&q=80",
        "colors": [
            {"hex": "#E5C9A1", "rgb": [229, 201, 161], "percentage": 45.0},
            {"hex": "#DF7E8C", "rgb": [223, 126, 140], "percentage": 30.0},
            {"hex": "#102126", "rgb": [16, 33, 38], "percentage": 25.0}
        ],
        "materials": ["Cashmere-silk fleece", "Unspun alpaca yarn"],
        "textures": ["Ultra-soft cloud loft"],
        "silhouettes": ["Cocoon knit coat", "Shawl collar cardigan"],
        "patterns": ["Textured moss stitch"],
        "signals": {"runway": 80.0, "social": 75.0, "search": 72.0, "retail": 66.0, "culture": 69.0}
    }
]


def seed_database(db: Session):
    init_db()

    # Check if trends already seeded
    existing_count = db.query(Trend).count()
    if existing_count >= 10:
        return

    now = datetime.now(timezone.utc)

    # 1. Seed demo user
    admin_user = db.query(User).filter(User.email == "analyst@luxe.tech").first()
    if not admin_user:
        admin_user = User(
            id=str(uuid.uuid4()),
            email="analyst@luxe.tech",
            name="LUXE Lead Intelligence Analyst",
            role="lead_analyst"
        )
        db.add(admin_user)
        db.commit()

    # 2. Seed Trends and associated intelligence
    for item in SAMPLE_TRENDS:
        existing = db.query(Trend).filter(Trend.slug == item["slug"]).first()
        if existing:
            continue

        trend_id = str(uuid.uuid4())
        trend = Trend(
            id=trend_id,
            slug=item["slug"],
            name=item["name"],
            category=item["category"],
            season=item["season"],
            description=item["description"],
            image_url=item["image_url"],
            status=item["status"],
            confidence=item["confidence"],
            momentum=item["momentum"],
            velocity=item["velocity"],
            acceleration=item["acceleration"],
            data_status="demo"
        )
        db.add(trend)

        # 3. Trend DNA
        dna = TrendDNA(
            id=str(uuid.uuid4()),
            trend_id=trend_id,
            colors_json=json.dumps(item["colors"]),
            materials_json=json.dumps(item["materials"]),
            textures_json=json.dumps(item["textures"]),
            silhouettes_json=json.dumps(item["silhouettes"]),
            patterns_json=json.dumps(item["patterns"]),
            visual_description=item["description"],
            ai_interpretation=f"AI synthesized DNA profile for {item['name']}: high synergy between tactile textiles and contemporary proportion."
        )
        db.add(dna)

        # 4. Historical Signal Observations (6 monthly points for each of the 5 sources)
        sources = ["runway", "social", "search", "retail", "culture"]
        base_signals = item["signals"]
        for src in sources:
            base_val = base_signals.get(src, 70.0)
            for m in range(6, -1, -1):
                obs_time = now - timedelta(days=30 * m)
                drift = (6 - m) * 2.5 + ((hash(item["slug"] + src + str(m)) % 7) - 3)
                sig_strength = max(20.0, min(99.0, base_val - 15.0 + drift))
                signal_rec = TrendSignal(
                    id=str(uuid.uuid4()),
                    trend_id=trend_id,
                    source=src,
                    signal_type="frequency_index",
                    strength=round(sig_strength, 1),
                    direction="up" if drift >= 0 else "steady",
                    timestamp=obs_time,
                    metadata_json=json.dumps({"sample_size": 240 + m * 30, "confidence_band": "95%"}),
                    data_status="demo"
                )
                db.add(signal_rec)

        # 5. Collection
        col = Collection(
            id=str(uuid.uuid4()),
            trend_id=trend_id,
            name=f"{item['name']} Capsule Edition",
            description=f"A complete editorial capsule expressing the {item['name']} aesthetic across primary luxury layers.",
            color_palette_json=json.dumps(item["colors"]),
            materials_json=json.dumps(item["materials"]),
            textures_json=json.dumps(item["textures"]),
            silhouettes_json=json.dumps(item["silhouettes"]),
            patterns_json=json.dumps(item["patterns"]),
            product_opportunities_json=json.dumps([f"{item['name']} Outerwear", f"{item['name']} Layering Staple", f"{item['name']} Signature Accessory"])
        )
        db.add(col)

        # 6. Sample Products
        prod_names = [
            (f"{item['name']} Unstructured Blazer", "Tailoring", item["materials"][0], item["silhouettes"][0], item["colors"][0]["hex"], 85.0),
            (f"{item['name']} Technical Cocoon Parka", "Outerwear", item["materials"][1] if len(item["materials"]) > 1 else "Tech Nylon", "Cocoon volume", item["colors"][1]["hex"] if len(item["colors"]) > 1 else "#ADC7B8", 82.5),
            (f"{item['name']} Fluid Drape Top", "Tops", "Liquid Cupro", "Second skin", item["colors"][2]["hex"] if len(item["colors"]) > 2 else "#DF7E8C", 78.0)
        ]
        for p_name, p_cat, p_mat, p_sil, p_col, p_score in prod_names:
            prod = Product(
                id=str(uuid.uuid4()),
                trend_id=trend_id,
                name=p_name,
                category=p_cat,
                description=f"Commercial execution exploring {item['name']} visual codes in {p_mat}.",
                material=p_mat,
                silhouette=p_sil,
                color=p_col,
                target_consumer="Contemporary post-digital luxury demographic",
                opportunity_score=p_score,
                ai_reasoning="Demand momentum exceeds current retail stock levels by 34%, creating clear market whitespace.",
                data_status="demo"
            )
            db.add(prod)

        # 7. Retail Signals
        regions = ["EU", "US", "UK", "JP"]
        for r_idx, reg in enumerate(regions):
            ret_sig = RetailSignal(
                id=str(uuid.uuid4()),
                trend_id=trend_id,
                region=reg,
                category=item["category"],
                demand=round(item["signals"]["search"] + (r_idx * 4 - 6), 1),
                growth=round(5.5 + r_idx * 1.8, 1),
                consumer_signal=f"Accelerating sell-through in {reg} specialty concept stores and contemporary department stores.",
                timestamp=now - timedelta(days=7 * (r_idx + 1)),
                data_status="demo"
            )
            db.add(ret_sig)

        # 8. Sample Statistical Forecast
        f_rec = Forecast(
            id=str(uuid.uuid4()),
            trend_id=trend_id,
            model="holt_winters",
            horizon="3_months",
            forecast_value=round(item["signals"]["search"] + 8.5, 1),
            backtest_accuracy=item["confidence"],
            training_start=now - timedelta(days=180),
            training_end=now,
            data_status="demo"
        )
        db.add(f_rec)

        # 9. Prophecy records (5 stages)
        stages = [
            ("current", f"{item['name']} begins surfacing in niche runway shows and avant-garde editorials.", ["Runway spotlight", "Designer capsule prototypes"], "High-visibility brand elevation", "Low initial retail unit volume", 88.0),
            ("emerging", "Boutique contemporary retailers establish initial test assortments.", ["Specialty orders climbing +28%", "Social search velocity"], "Controlled initial production drop", "Pricing resistance if unsorted", 84.0),
            ("accelerating", "Consumer demand accelerates faster than observable market supply.", ["Search queries +44%", "High full-price sell-through"], "Expand category range into accessories and unisex", "Dilution by copycats", 80.0),
            ("mainstream", "Global contemporary department stores stock commercial versions.", ["Wide brand adoption", "Mass retail presence"], "Scale core commercial volume drivers", "Markdown pressure at end of cycle", 76.0),
            ("next", f"Evolution of {item['name']} into mutated micro-trends and counter-movements.", ["Emerging counter-signals", "Designers exploring contrasting silhouettes"], "Pre-seed subsequent season aesthetic", "Inventory overhang risk", 72.0)
        ]
        for st_name, st_fc, st_ev, st_opp, st_risk, st_conf in stages:
            pr = Prophecy(
                id=str(uuid.uuid4()),
                trend_id=trend_id,
                stage=st_name,
                forecast=st_fc,
                evidence_json=json.dumps(st_ev),
                opportunity=st_opp,
                risk=st_risk,
                confidence=st_conf,
                data_status="demo"
            )
            db.add(pr)

    db.commit()


if __name__ == "__main__":
    from app.database import SessionLocal
    db = SessionLocal()
    seed_database(db)
    print("Database successfully seeded with demo intelligence data.")
