"""Load precisely the two declared implementations; no learning or calibration."""
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from src.replication.legacy_vader import sentiment


def analyzers():
    modern = SentimentIntensityAnalyzer()
    return {'VADER 2014': sentiment, 'VADER 3.3.2': modern.polarity_scores}
