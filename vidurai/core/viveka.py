"""
The Viveka Engine - Conscience & Discrimination
Teaching AI to distinguish important from trivial
"""

from typing import Dict, Any, List
from dataclasses import dataclass
from loguru import logger
import re

@dataclass
class ImportanceFactors:
    """Factors that determine memory importance"""
    emotional_weight: float = 0.0
    goal_relevance: float = 0.0
    surprise_factor: float = 0.0
    frequency: float = 0.0
    user_preference: float = 0.0
    dharma_alignment: float = 1.0

class VivekaEngine:
    """
    The Conscience Layer - Intelligent Importance Scoring
    Implements discrimination based on Vedantic principles
    """
    
    def __init__(self):
        self.user_goals: List[str] = []
        self.preferences: Dict[str, float] = {}
        logger.info("Initialized Viveka Engine - The Conscience Layer")
    
    def calculate_importance(self, 
                            content: str, 
                            metadata: Dict[str, Any] = None) -> float:
        """
        Calculate importance score using multiple factors
        Returns: score between 0.0 and 1.0
        """
        factors = self._analyze_content(content, metadata or {})
        
        # Weighted combination of factors
        weights = {
            'emotional': 0.25,
            'goal': 0.30,
            'surprise': 0.15,
            'frequency': 0.10,
            'preference': 0.10,
            'dharma': 0.10
        }
        
        score = (
            factors.emotional_weight * weights['emotional'] +
            factors.goal_relevance * weights['goal'] +
            factors.surprise_factor * weights['surprise'] +
            factors.frequency * weights['frequency'] +
            factors.user_preference * weights['preference'] +
            factors.dharma_alignment * weights['dharma']
        )
        
        return min(max(score, 0.0), 1.0)
    
    def _analyze_content(self, content: str, metadata: Dict) -> ImportanceFactors:
        """Analyze content to extract importance factors"""
        factors = ImportanceFactors()
        
        # Emotional weight detection
        factors.emotional_weight = self._detect_emotion(content)
        
        # Goal relevance
        factors.goal_relevance = self._check_goal_relevance(content)
        
        # Surprise factor (new information)
        factors.surprise_factor = self._calculate_novelty(content, metadata)
        
        # User preference alignment
        factors.user_preference = self._check_preferences(content)
        
        # Dharma (ethical) alignment
        factors.dharma_alignment = self._assess_dharma(content)
        
        return factors
    
    def _detect_emotion(self, content: str) -> float:
        """Detect emotional significance in content"""
        emotion_indicators = [
            'love', 'hate', 'fear', 'happy', 'sad', 'angry',
            'excited', 'worried', 'urgent', 'important', 'critical'
        ]
        
        content_lower = content.lower()
        emotion_count = sum(1 for word in emotion_indicators 
                          if word in content_lower)
        
        return min(emotion_count * 0.2, 1.0)
    
    def _check_goal_relevance(self, content: str) -> float:
        """Check if content relates to user goals"""
        if not self.user_goals:
            return 0.5  # Neutral if no goals set
        
        relevance = 0.0
        for goal in self.user_goals:
            if goal.lower() in content.lower():
                relevance += 0.3
        
        return min(relevance, 1.0)
    
    def _calculate_novelty(self, content: str, metadata: Dict) -> float:
        """Calculate how novel/surprising the information is"""
        # Check if marked as question
        if '?' in content:
            return 0.7
        
        # Check for learning indicators
        learning_words = ['learn', 'new', 'discover', 'realize', 'understand']
        if any(word in content.lower() for word in learning_words):
            return 0.6
        
        return 0.3
    
    def _check_preferences(self, content: str) -> float:
        """Check alignment with user preferences"""
        if not self.preferences:
            return 0.5
        
        score = 0.5  # Base score
        for pref, weight in self.preferences.items():
            if pref.lower() in content.lower():
                score += weight * 0.2
        
        return min(score, 1.0)
    
    def _assess_dharma(self, content: str) -> float:
        """
        Assess ethical alignment (dharma)
        Higher score = more aligned with ethical principles
        """
        # Check for harmful content indicators
        harmful_indicators = [
            'harm', 'hurt', 'kill', 'steal', 'lie', 'cheat',
            'hate', 'discriminate', 'abuse'
        ]
        
        content_lower = content.lower()
        
        # Penalize harmful content
        for word in harmful_indicators:
            if word in content_lower:
                return 0.2  # Low dharma score
        
        # Check for positive indicators
        positive_indicators = [
            'help', 'support', 'kind', 'truth', 'honest',
            'compassion', 'wisdom', 'peace', 'love'
        ]
        
        positive_count = sum(1 for word in positive_indicators 
                           if word in content_lower)
        
        if positive_count > 0:
            return min(0.8 + positive_count * 0.1, 1.0)
        
        return 0.7  # Neutral dharma score
    
    def set_user_goals(self, goals: List[str]):
        """Set user goals for relevance scoring"""
        self.user_goals = goals
        logger.info(f"Set {len(goals)} user goals")
    
    def set_preferences(self, preferences: Dict[str, float]):
        """Set user preferences for importance scoring"""
        self.preferences = preferences
        logger.info(f"Set {len(preferences)} user preferences")