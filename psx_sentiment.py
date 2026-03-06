"""
PSX Sentiment Analysis - Using NewsData.io API
Sirf PSX stocks ke liye - No Emoji, Clean Output
"""

import requests
import logging
from datetime import datetime, timedelta

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PSXSentiment:
    """PSX Stock Sentiment Analysis using NewsData.io"""
    
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://newsdata.io/api/1/latest"
        
    def get_company_news_sentiment(self, company_name, symbol):
        """
        Get news sentiment for a specific PSX company
        """
        try:
            # Company names for better search
            company_keywords = {
                'FFC': 'Fauji Fertilizer',
                'ENGROH': 'Engro',
                'OGDC': 'OGDC Oil Gas',
                'HUBC': 'Hub Power',
                'PPL': 'Pakistan Petroleum',
                'NBP': 'National Bank Pakistan',
                'UBL': 'United Bank',
                'MZNPETF': 'Meezan ETF',
                'NBPGETF': 'NBP ETF',
                'KEL': 'K Electric',
                'SYS': 'Systems Limited',
                'LUCK': 'Lucky Cement',
                'PSO': 'Pakistan State Oil',
                'GOLD': 'Gold Pakistan'
            }
            
            search_term = company_keywords.get(symbol, company_name)
            
            # API request with date filter (last 3 days)
            params = {
                'apikey': self.api_key,
                'q': search_term,
                'language': 'en',
                'size': 25,
                'timeframe': 3  # Last 3 days
            }
            
            logger.info(f"Fetching news for {search_term}")
            response = requests.get(self.base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                articles = data.get('results', [])
                
                if not articles:
                    logger.info(f"No news found for {search_term}")
                    return self._get_default_sentiment()
                
                # Analyze sentiment
                positive = 0
                negative = 0
                neutral = 0
                
                positive_words = ['surge', 'gain', 'bull', 'rise', 'up', 'positive', 'growth', 'profit', 
                                 'higher', 'increase', 'strong', 'record', 'beat', 'exceed', 'upgrade']
                
                negative_words = ['fall', 'drop', 'bear', 'down', 'negative', 'loss', 'decline', 'risk',
                                 'lower', 'decrease', 'weak', 'cut', 'miss', 'downgrade', 'investigation']
                
                for article in articles[:15]:  # Limit to 15 articles
                    title = article.get('title', '').lower()
                    description = article.get('description', '') or ''
                    description = description.lower()
                    
                    text = title + " " + description
                    
                    pos_count = sum(1 for word in positive_words if word in text)
                    neg_count = sum(1 for word in negative_words if word in text)
                    
                    if pos_count > neg_count:
                        positive += 1
                    elif neg_count > pos_count:
                        negative += 1
                    else:
                        neutral += 1
                
                total = positive + negative + neutral
                
                if total == 0:
                    return self._get_default_sentiment()
                
                sentiment = {
                    'positive': round((positive/total)*100, 1),
                    'negative': round((negative/total)*100, 1),
                    'neutral': round((neutral/total)*100, 1),
                    'overall': 'Positive' if positive > negative else 'Negative' if negative > positive else 'Neutral',
                    'article_count': total
                }
                
                logger.info(f"Sentiment for {symbol}: {sentiment['overall']} ({sentiment['positive']}% pos)")
                return sentiment
                
            else:
                logger.error(f"API error: {response.status_code}")
                return self._get_default_sentiment()
                
        except Exception as e:
            logger.error(f"Error in news sentiment: {e}")
            return self._get_default_sentiment()
    
    def _get_default_sentiment(self):
        """Return default neutral sentiment"""
        return {
            'positive': 33.3,
            'negative': 33.3,
            'neutral': 33.4,
            'overall': 'Neutral',
            'article_count': 0
        }
