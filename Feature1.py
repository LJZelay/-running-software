"""
CSE 4504 Team Project - Feature 1
Text Analysis and Processing Module

This module implements the first feature as per the project requirements.
Each team member will implement specific components assigned to them.
"""

from typing import List, Dict, Tuple, Union, Any
from dataclasses import dataclass
import re
from collections import Counter
from abc import ABC, abstractmethod
from Utils import logger, validate_input


@dataclass
class TextStats:
    """Data class for text statistics"""
    word_count: int
    character_count: int
    sentence_count: int
    avg_word_length: float
    unique_words: int
    most_common_words: List[Tuple[str, int]]


class TextProcessor(ABC):
    """Abstract base class for text processing components"""
    
    @abstractmethod
    def process(self, text: str) -> Any:
        """Process text and return result"""
        pass


class WordCounter(TextProcessor):
    """Component 1: Word counting and basic statistics"""
    
    def process(self, text: str) -> Dict[str, int]:
        """Count words and return basic statistics"""
        validate_input(text, str)
        
        words = re.findall(r'\b\w+\b', text.lower())
        word_count = len(words)
        char_count = len(text.replace('\n', '').replace('\r', ''))
        
        return {
            'total_words': word_count,
            'total_characters': char_count,
            'unique_words': len(set(words))
        }


class SentenceAnalyzer(TextProcessor):
    """Component 2: Sentence analysis"""
    
    def process(self, text: str) -> Dict[str, Any]:
        """Analyze sentences in text"""
        validate_input(text, str)
        
        # Simple sentence splitting (can be enhanced)
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        avg_words_per_sentence = 0
        if sentences:
            total_words = sum(len(re.findall(r'\b\w+\b', s)) for s in sentences)
            avg_words_per_sentence = total_words / len(sentences)
        
        return {
            'sentence_count': len(sentences),
            'avg_words_per_sentence': round(avg_words_per_sentence, 2),
            'sentences': sentences
        }


class KeywordExtractor(TextProcessor):
    """Component 3: Keyword extraction"""
    
    def __init__(self, stop_words: List[str] = None):
        self.stop_words = stop_words or ['the', 'a', 'an', 'and', 'or', 'but', 'in', 
                                         'on', 'at', 'to', 'for', 'of', 'with', 'by']
    
    def process(self, text: str, top_n: int = 5) -> List[Tuple[str, int]]:
        """Extract top N keywords from text"""
        validate_input(text, str)
        validate_input(top_n, int)
        
        words = re.findall(r'\b\w+\b', text.lower())
        # Filter out stop words
        filtered_words = [w for w in words if w not in self.stop_words and len(w) > 2]
        
        # Count word frequencies
        word_counts = Counter(filtered_words)
        
        # Get top N keywords
        return word_counts.most_common(top_n)


class TextFormatter(TextProcessor):
    """Component 4: Text formatting and transformation"""
    
    def process(self, text: str, 
                format_type: str = 'title') -> str:
        """Format text according to specified type"""
        validate_input(text, str)
        validate_input(format_type, str)
        
        format_type = format_type.lower()
        
        if format_type == 'title':
            return text.title()
        elif format_type == 'upper':
            return text.upper()
        elif format_type == 'lower':
            return text.lower()
        elif format_type == 'sentence':
            # Capitalize first letter of each sentence
            sentences = re.split(r'([.!?]\s+)', text)
            formatted = ''.join(
                s.capitalize() if i % 2 == 0 else s 
                for i, s in enumerate(sentences)
            )
            return formatted
        else:
            raise ValueError(f"Unknown format type: {format_type}")


class Feature1:
    """
    Main Feature 1 class that integrates all text analysis components.
    
    Team Members & Responsibilities:
    1. [Team Member 1] - WordCounter and TextStats implementation
    2. [Team Member 2] - SentenceAnalyzer and validation
    3. [Team Member 3] - KeywordExtractor and stop words handling
    4. [Team Member 4] - TextFormatter and integration testing
    """
    
    def __init__(self):
        """Initialize Feature 1 with all components"""
        self.components = {
            'word_counter': WordCounter(),
            'sentence_analyzer': SentenceAnalyzer(),
            'keyword_extractor': KeywordExtractor(),
            'text_formatter': TextFormatter()
        }
        logger.info("Feature1 initialized with all components")
    
    def execute(self, text: str, 
                operation: str = 'analyze',
                **kwargs) -> Union[Dict, str, TextStats]:
        """
        Execute Feature 1 operations
        
        Args:
            text: Input text to process
            operation: Type of operation to perform
                - 'analyze': Full text analysis
                - 'count': Word counting only
                - 'sentences': Sentence analysis
                - 'keywords': Extract keywords
                - 'format': Format text
            **kwargs: Additional parameters for specific operations
        
        Returns:
            Result based on the operation
        """
        validate_input(text, str)
        
        operation = operation.lower()
        
        try:
            if operation == 'analyze':
                return self._full_analysis(text)
            elif operation == 'count':
                return self.components['word_counter'].process(text)
            elif operation == 'sentences':
                return self.components['sentence_analyzer'].process(text)
            elif operation == 'keywords':
                top_n = kwargs.get('top_n', 5)
                return self.components['keyword_extractor'].process(text, top_n)
            elif operation == 'format':
                format_type = kwargs.get('format_type', 'title')
                return self.components['text_formatter'].process(text, format_type)
            else:
                raise ValueError(
                    f"Unknown operation: {operation}. "
                    f"Available: analyze, count, sentences, keywords, format"
                )
                
        except Exception as e:
            logger.error(f"Feature1 execution failed: {str(e)}")
            raise
    
    def _full_analysis(self, text: str) -> TextStats:
        """Perform complete text analysis"""
        # Get statistics from all components
        word_stats = self.components['word_counter'].process(text)
        sentence_stats = self.components['sentence_analyzer'].process(text)
        keywords = self.components['keyword_extractor'].process(text, top_n=10)
        
        # Calculate average word length
        words = re.findall(r'\b\w+\b', text.lower())
        avg_word_len = sum(len(w) for w in words) / len(words) if words else 0
        
        # Create TextStats object
        return TextStats(
            word_count=word_stats['total_words'],
            character_count=word_stats['total_characters'],
            sentence_count=sentence_stats['sentence_count'],
            avg_word_length=round(avg_word_len, 2),
            unique_words=word_stats['unique_words'],
            most_common_words=keywords
        )
    
    def get_component_info(self) -> Dict[str, str]:
        """Get information about all components"""
        return {
            'word_counter': 'Counts words, characters, and unique words',
            'sentence_analyzer': 'Analyzes sentence structure and counts',
            'keyword_extractor': 'Extracts important keywords from text',
            'text_formatter': 'Formats text in various styles'
        }


# Example usage and testing
if __name__ == "__main__":
    # Quick test of Feature1
    feature = Feature1()
    test_text = "Hello world! This is a test. Feature 1 is working."
    
    print("Testing Feature1 components:")
    print(f"Input text: {test_text}")
    print()
    
    # Test each component
    print("1. Word Counter:")
    print(feature.execute(test_text, 'count'))
    print()
    
    print("2. Sentence Analyzer:")
    print(feature.execute(test_text, 'sentences'))
    print()
    
    print("3. Keyword Extractor:")
    print(feature.execute(test_text, 'keywords', top_n=3))
    print()
    
    print("4. Text Formatter (title):")
    print(feature.execute(test_text, 'format', format_type='title'))
    print()
    
    print("5. Full Analysis:")
    stats = feature.execute(test_text, 'analyze')
    print(f"Word Count: {stats.word_count}")
    print(f"Characters: {stats.character_count}")
    print(f"Sentences: {stats.sentence_count}")
    print(f"Avg Word Length: {stats.avg_word_length}")
    print(f"Unique Words: {stats.unique_words}")
    print(f"Top Keywords: {stats.most_common_words}")