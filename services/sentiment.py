from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

analyzer = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    if not text:
        return "Neutral"

    score = analyzer.polarity_scores(text)["compound"]

    if score >= 0.05:
        return {
            "label": "Positive",
            "score": round(score, 2),
            "emoji": "😊"
        }
    elif score <= -0.05:
        return {
            "label": "Negative",
            "score": round(score, 2),
            "emoji": "😠"
        }
    else:
        return {
            "label": "Neutral",
            "score": round(score, 2),
            "emoji": "😐"
        }
