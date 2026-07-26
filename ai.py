def score_deal(price):
    if price <= 400:
        return "🔥 Amazing Deal"
    elif price <= 500:
        return "✅ Great Deal"
    elif price <= 600:
        return "🟡 Fair Price"
    else:
        return "❌ Overpriced"


def matches_search(search, title):
    search = search.lower()
    title = title.lower()

    # PS5 console search
    if "ps5" in search or "playstation 5" in search:

        bad_words = [
            "portal",
            "controller",
            "headset",
            "skin",
            "cover",
            "case",
            "charger",
            "charging",
            "dock",
            "stand",
            "remote",
            "thumb grip",
            "thumbstick",
            "sticker",
            "faceplate",
            "plate",
            "accessory",
            "mount",
            "portable"
        ]

        for word in bad_words:
            if word in title:
                return 0

        good_words = [
            "playstation 5",
            "ps5",
            "console",
            "digital",
            "disc",
            "pro",
            "slim"
        ]

        score = 0

        for word in good_words:
            if word in title:
                score += 1

        return score

    # Generic search
    score = 0

    for word in search.split():
        if word in title:
            score += 1

    return score